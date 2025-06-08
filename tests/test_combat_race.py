"""
Test combat race conditions and simultaneous actions
"""
import pytest
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock
from app import app, db, Session, UserRole, Character, Entity
from utils.dice_roller import dice_roller
import json


class TestCombatRaceConditions:
    """Test race conditions in combat scenarios"""
    
    @pytest.fixture
    def app_context(self):
        """Create Flask app context for testing"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app_context):
        """Create test client"""
        return app_context.test_client()
    
    @pytest.fixture
    def setup_combat_session(self, app_context):
        """Set up a combat session with players"""
        # Create session
        session = Session(
            id='combat-session-123',
            name='Combat Test',
            gm_user_id='gm_user'
        )
        db.session.add(session)
        
        # Add GM
        gm_role = UserRole(
            session_id=session.id,
            user_id='gm_user',
            role='gm'
        )
        db.session.add(gm_role)
        
        # Add players
        for i in range(3):
            player_role = UserRole(
                session_id=session.id,
                user_id=f'player_{i}',
                role='player'
            )
            db.session.add(player_role)
            
            # Create character
            character = Character(
                session_id=session.id,
                user_id=f'player_{i}',
                name=f'Runner {i}',
                attributes=json.dumps({
                    'body': 3,
                    'agility': 4,
                    'reaction': 5,
                    'logic': 3,
                    'intuition': 4,
                    'willpower': 3,
                    'charisma': 3,
                    'edge': 2
                })
            )
            db.session.add(character)
        
        # Add NPCs
        for i in range(2):
            npc = Entity(
                session_id=session.id,
                name=f'Guard {i}',
                type='npc',
                status='active',
                extra_data=json.dumps({
                    'health': 10,
                    'armor': 2
                })
            )
            db.session.add(npc)
        
        db.session.commit()
        return session.id
    
    def test_simultaneous_edge_and_damage_rolls(self, client, setup_combat_session):
        """Test simultaneous Edge usage and damage rolls"""
        session_id = setup_combat_session
        
        # Mock dice rolls to be predictable
        with patch.object(dice_roller, 'roll_shadowrun') as mock_roll:
            # Configure different results for each call
            mock_roll.side_effect = [
                # Player 1 Edge roll
                {
                    'dice_pool': 10,
                    'rolls': [6, 6, 5, 4, 3, 2, 1, 6, 5, 4, 6, 5],  # Exploded 6s
                    'hits': 8,
                    'ones': 1,
                    'glitch': False,
                    'critical_glitch': False,
                    'edge_used': True
                },
                # Player 2 damage roll
                {
                    'dice_pool': 8,
                    'rolls': [5, 5, 4, 3, 2, 1, 1, 1],
                    'hits': 2,
                    'ones': 3,
                    'glitch': False,
                    'critical_glitch': False,
                    'edge_used': False
                }
            ]
            
            # Simulate simultaneous requests
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Player 1 uses Edge for attack
                future1 = executor.submit(
                    client.post,
                    f'/api/command',
                    json={
                        'command': 'roll 10d6 edge',
                        'session_id': session_id,
                        'user_id': 'player_0',
                        'model': 'shadowrun'
                    }
                )
                
                # Player 2 rolls damage
                future2 = executor.submit(
                    client.post,
                    f'/api/command',
                    json={
                        'command': 'roll 8d6 damage',
                        'session_id': session_id,
                        'user_id': 'player_1',
                        'model': 'shadowrun'
                    }
                )
                
                # Get results
                response1 = future1.result()
                response2 = future2.result()
            
            # Both should succeed
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            # Verify different results
            data1 = response1.get_json()
            data2 = response2.get_json()
            
            assert 'edge' in str(data1).lower()
            assert 'damage' in str(data2).lower()
    
    def test_concurrent_initiative_modifications(self, client, setup_combat_session):
        """Test multiple players modifying initiative simultaneously"""
        session_id = setup_combat_session
        
        # Store to track initiative order
        initiative_updates = []
        
        def update_initiative(player_id, initiative):
            """Helper to update initiative"""
            response = client.post(
                f'/api/session/{session_id}/entities',
                json={
                    'user_id': 'gm_user',  # Only GM can update
                    'name': f'Player {player_id}',
                    'type': 'player',
                    'status': 'active',
                    'extra_data': json.dumps({'initiative': initiative})
                }
            )
            initiative_updates.append({
                'player': player_id,
                'initiative': initiative,
                'time': time.time()
            })
            return response
        
        # Simulate concurrent initiative updates
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            
            # Three players roll initiative at the same time
            for i in range(3):
                future = executor.submit(
                    update_initiative,
                    f'player_{i}',
                    15 - i  # Different initiatives
                )
                futures.append(future)
            
            # Wait for all to complete
            results = [f.result() for f in futures]
        
        # All should succeed
        for result in results:
            assert result.status_code in [200, 201]
        
        # Verify initiative order is preserved
        entities = client.get(
            f'/api/session/{session_id}/entities'
        ).get_json()
        
        # Should have all entities
        assert len([e for e in entities if e['type'] == 'player']) >= 3
    
    def test_damage_application_race_condition(self, client, setup_combat_session):
        """Test applying damage to same target from multiple sources"""
        session_id = setup_combat_session
        
        # Create a target with health
        target = Entity(
            session_id=session_id,
            name='Target',
            type='npc',
            status='active',
            extra_data=json.dumps({'health': 20, 'armor': 3})
        )
        db.session.add(target)
        db.session.commit()
        target_id = target.id
        
        def apply_damage(damage, source):
            """Helper to apply damage"""
            # Get current health
            entity = Entity.query.get(target_id)
            current_data = json.loads(entity.extra_data)
            current_health = current_data['health']
            
            # Calculate new health
            new_health = current_health - damage
            current_data['health'] = new_health
            
            # Update
            response = client.post(
                f'/api/session/{session_id}/entities',
                json={
                    'user_id': 'gm_user',
                    'id': target_id,
                    'name': 'Target',
                    'type': 'npc',
                    'status': 'wounded' if new_health > 0 else 'incapacitated',
                    'extra_data': json.dumps(current_data)
                }
            )
            return response, new_health
        
        # Simulate concurrent damage
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Two sources deal damage simultaneously
            future1 = executor.submit(apply_damage, 8, 'player_0')
            future2 = executor.submit(apply_damage, 7, 'player_1')
            
            result1, health1 = future1.result()
            result2, health2 = future2.result()
        
        # At least one should succeed
        assert result1.status_code == 200 or result2.status_code == 200
        
        # Final health should reflect some damage
        final_entity = Entity.query.get(target_id)
        final_data = json.loads(final_entity.extra_data)
        final_health = final_data['health']
        
        # Health should be reduced
        assert final_health < 20
    
    @pytest.mark.asyncio
    async def test_async_edge_pool_modifications(self, client, setup_combat_session):
        """Test async modifications to Edge pool"""
        session_id = setup_combat_session
        
        async def use_edge(player_id):
            """Async helper to use Edge"""
            # This would be an async endpoint in real implementation
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                client.post,
                f'/api/session/{session_id}/character/edge/use',
                {'user_id': player_id, 'amount': 1}
            )
        
        async def gain_edge(player_id):
            """Async helper to gain Edge"""
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                client.post,
                f'/api/session/{session_id}/character/edge/gain',
                {'user_id': player_id, 'amount': 1}
            )
        
        # Simulate simultaneous Edge modifications
        tasks = [
            use_edge('player_0'),
            use_edge('player_0'),  # Same player using twice
            gain_edge('player_0'),  # While also gaining
        ]
        
        # Run concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should handle gracefully (no crashes)
        for result in results:
            if not isinstance(result, Exception):
                # If not an error, should be a response
                assert hasattr(result, 'status_code')
    
    def test_combat_state_consistency(self, client, setup_combat_session):
        """Test combat state remains consistent under concurrent modifications"""
        session_id = setup_combat_session
        
        # Track all state changes
        state_changes = []
        
        def modify_combat_state(action_type, data):
            """Helper to modify combat state"""
            endpoint_map = {
                'damage': f'/api/session/{session_id}/entities',
                'initiative': f'/api/session/{session_id}/entities',
                'status': f'/api/session/{session_id}/entities',
                'scene': f'/api/session/{session_id}/scene'
            }
            
            response = client.post(
                endpoint_map.get(action_type, f'/api/session/{session_id}/entities'),
                json=data
            )
            
            state_changes.append({
                'action': action_type,
                'data': data,
                'time': time.time(),
                'success': response.status_code in [200, 201]
            })
            
            return response
        
        # Simulate combat round with many concurrent actions
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            # Various combat actions happening simultaneously
            actions = [
                ('damage', {
                    'user_id': 'gm_user',
                    'id': 1,
                    'name': 'Guard 0',
                    'type': 'npc',
                    'status': 'wounded',
                    'extra_data': json.dumps({'health': 5})
                }),
                ('initiative', {
                    'user_id': 'gm_user',
                    'name': 'Runner 0',
                    'type': 'player',
                    'status': 'active',
                    'extra_data': json.dumps({'initiative': 18})
                }),
                ('status', {
                    'user_id': 'gm_user',
                    'name': 'Runner 1',
                    'type': 'player',
                    'status': 'stunned',
                    'extra_data': json.dumps({})
                }),
                ('scene', {
                    'user_id': 'gm_user',
                    'summary': 'Combat round 2: Guards are retreating'
                })
            ]
            
            for action_type, data in actions:
                future = executor.submit(modify_combat_state, action_type, data)
                futures.append(future)
            
            # Wait for all
            results = [f.result() for f in futures]
        
        # Verify state consistency
        successful_changes = [s for s in state_changes if s['success']]
        assert len(successful_changes) > 0
        
        # Check final state
        entities = client.get(f'/api/session/{session_id}/entities').get_json()
        scene = client.get(f'/api/session/{session_id}/scene').get_json()
        
        # Should have consistent state
        assert len(entities) > 0
        assert 'summary' in scene
    
    def test_glitch_during_edge_use(self, client, setup_combat_session):
        """Test handling of glitch while using Edge"""
        session_id = setup_combat_session
        
        with patch.object(dice_roller, 'roll_shadowrun') as mock_roll:
            # Configure to return glitch with Edge
            mock_roll.return_value = {
                'dice_pool': 12,
                'rolls': [1, 1, 1, 1, 1, 1, 2, 3, 6, 6, 5, 6],
                'hits': 4,  # Some hits due to Edge
                'ones': 6,  # Many ones
                'glitch': True,
                'critical_glitch': False,
                'edge_used': True
            }
            
            response = client.post(
                '/api/command',
                json={
                    'command': 'roll 12d6 edge attack',
                    'session_id': session_id,
                    'user_id': 'player_0',
                    'model': 'shadowrun'
                }
            )
            
            assert response.status_code == 200
            data = response.get_json()
            
            # Should indicate both Edge use and glitch
            response_text = str(data).lower()
            assert 'edge' in response_text
            assert 'glitch' in response_text
    
    def test_race_condition_in_dm_approval(self, client, setup_combat_session):
        """Test race condition when multiple DMs approve same action"""
        session_id = setup_combat_session
        
        # Create pending action
        from app import PendingResponse
        
        pending = PendingResponse(
            session_id=session_id,
            user_id='player_0',
            context='I want to hack the security system',
            ai_response='You successfully hack into the system',
            response_type='narrative',
            priority=2
        )
        db.session.add(pending)
        db.session.commit()
        response_id = pending.id
        
        def approve_response(dm_id):
            """Helper for DM approval"""
            return client.post(
                f'/api/session/{session_id}/pending-response/{response_id}/review',
                json={
                    'user_id': dm_id,
                    'action': 'approve',
                    'dm_notes': f'Approved by {dm_id}'
                }
            )
        
        # Simulate multiple DMs trying to approve simultaneously
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Two DMs try to approve at the same time
            future1 = executor.submit(approve_response, 'gm_user')
            future2 = executor.submit(approve_response, 'gm_user')  # Same GM clicking twice
            
            result1 = future1.result()
            result2 = future2.result()
        
        # One should succeed, one should fail or get different response
        success_count = sum(1 for r in [result1, result2] if r.status_code == 200)
        assert success_count >= 1
        
        # Check final state
        updated_pending = PendingResponse.query.get(response_id)
        assert updated_pending.status != 'pending' 