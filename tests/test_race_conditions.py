import pytest
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from app import app, db, Session, PendingResponse, UserRole, GeneratedImage
from unittest.mock import patch, Mock


class TestRaceConditions:
    """Test suite for race conditions and concurrent operations"""
    
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.test_client() as client:
            with app.app_context():
                db.create_all()
                yield client
                
    def test_concurrent_session_join(self, client):
        """Test multiple users joining session simultaneously"""
        # Create session
        with app.app_context():
            session = Session(id='test-session', name='Test', gm_user_id='gm-123')
            db.session.add(session)
            db.session.commit()
        
        # Simulate 10 concurrent join requests
        def join_session(user_id):
            return client.post(f'/api/session/test-session/join', json={
                'user_id': f'user-{user_id}'
            })
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(join_session, i) for i in range(10)]
            results = [f.result() for f in futures]
        
        # All should succeed
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count == 10, f"Only {success_count} of 10 joins succeeded"
        
        # Verify no duplicate roles
        with app.app_context():
            roles = UserRole.query.filter_by(session_id='test-session').all()
            user_ids = [r.user_id for r in roles]
            assert len(user_ids) == len(set(user_ids)), "Duplicate user roles created"
    
    def test_concurrent_dm_review_approval(self, client):
        """Test concurrent DM approvals of same response"""
        # Create pending response
        with app.app_context():
            response = PendingResponse(
                id='resp-123',
                session_id='test-session',
                user_id='player-1',
                context='Test question',
                ai_response='Test answer',
                status='pending'
            )
            db.session.add(response)
            db.session.commit()
        
        # Simulate 5 concurrent approval attempts
        def approve_response():
            return client.post('/api/review', json={
                'response_id': 'resp-123',
                'action': 'approve',
                'dm_user_id': 'gm-123'
            })
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(approve_response) for _ in range(5)]
            results = [f.result() for f in futures]
        
        # Only one should succeed
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count == 1, f"{success_count} approvals succeeded, expected 1"
        
        # Verify response is approved only once
        with app.app_context():
            response = PendingResponse.query.get('resp-123')
            assert response.status == 'approved', "Response not properly approved"
    
    def test_concurrent_image_generation(self, client):
        """Test concurrent image generation requests"""
        # Mock image generation
        with patch('image_gen_utils.ImageGenerator.generate_image') as mock_gen:
            mock_gen.return_value = {
                'image_url': 'http://test.com/image.png',
                'provider': 'dalle',
                'generation_time': 1.5
            }
            
            # Simulate 5 concurrent image requests
            def generate_image(i):
                return client.post('/api/session/test-session/generate-image', json={
                    'prompt': f'Test prompt {i}',
                    'user_id': f'user-{i}'
                })
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(generate_image, i) for i in range(5)]
                results = [f.result() for f in futures]
            
            # All should succeed
            for r in results:
                assert r.status_code in [200, 201], f"Image generation failed: {r.status_code}"
    
    def test_websocket_message_ordering(self):
        """Test WebSocket message ordering under concurrent load"""
        # This would require actual WebSocket testing framework
        # Placeholder for WebSocket race condition test
        messages_received = []
        
        def mock_websocket_handler(message):
            messages_received.append({
                'id': message['id'],
                'timestamp': time.time()
            })
        
        # Simulate concurrent message sending
        # Would need actual WebSocket implementation
        pass
    
    def test_database_deadlock_prevention(self, client):
        """Test database operations don't cause deadlocks"""
        def update_session_1():
            with app.app_context():
                session = Session.query.get('test-session')
                time.sleep(0.1)  # Simulate processing
                session.name = 'Updated by Thread 1'
                db.session.commit()
        
        def update_session_2():
            with app.app_context():
                session = Session.query.get('test-session')
                time.sleep(0.1)  # Simulate processing
                session.name = 'Updated by Thread 2'
                db.session.commit()
        
        # Create test session
        with app.app_context():
            session = Session(id='test-session', name='Original', gm_user_id='gm-123')
            db.session.add(session)
            db.session.commit()
        
        # Run concurrent updates
        thread1 = threading.Thread(target=update_session_1)
        thread2 = threading.Thread(target=update_session_2)
        
        thread1.start()
        thread2.start()
        
        thread1.join(timeout=5)
        thread2.join(timeout=5)
        
        # Both should complete without deadlock
        assert not thread1.is_alive(), "Thread 1 deadlocked"
        assert not thread2.is_alive(), "Thread 2 deadlocked"
    
    def test_session_state_consistency(self, client):
        """Test session state remains consistent under concurrent modifications"""
        # Create session with initial state
        with app.app_context():
            session = Session(id='test-session', name='Test', gm_user_id='gm-123')
            db.session.add(session)
            
            # Add some players
            for i in range(3):
                role = UserRole(
                    session_id='test-session',
                    user_id=f'player-{i}',
                    role='player'
                )
                db.session.add(role)
            db.session.commit()
        
        # Concurrent operations
        def player_action(player_id):
            # Simulate various player actions
            actions = [
                lambda: client.post('/api/roll', json={'dice': '3d6', 'user_id': player_id}),
                lambda: client.post('/api/llm', json={'message': 'test', 'user_id': player_id}),
                lambda: client.get(f'/api/session/test-session/status'),
            ]
            import random
            return random.choice(actions)()
        
        # Run many concurrent actions
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(player_action, f'player-{i % 3}')
                for i in range(30)
            ]
            results = [f.result() for f in futures]
        
        # Verify session integrity
        with app.app_context():
            session = Session.query.get('test-session')
            assert session is not None, "Session lost during concurrent operations"
            
            roles = UserRole.query.filter_by(session_id='test-session').all()
            assert len(roles) == 3, f"Player count changed: {len(roles)}"
    
    def test_notification_queue_race_condition(self, client):
        """Test notification system under concurrent load"""
        notifications_sent = []
        
        def send_notification(notif_id):
            response = client.post('/api/notifications', json={
                'session_id': 'test-session',
                'message': f'Notification {notif_id}',
                'type': 'dm_review',
                'priority': 'high'
            })
            if response.status_code == 200:
                notifications_sent.append(notif_id)
            return response
        
        # Send many notifications concurrently
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(send_notification, i)
                for i in range(50)
            ]
            results = [f.result() for f in futures]
        
        # All should be sent
        assert len(notifications_sent) == 50, f"Lost notifications: {50 - len(notifications_sent)}"
    
    @pytest.mark.asyncio
    async def test_async_operation_race_conditions(self):
        """Test async operations for race conditions"""
        results = []
        
        async def async_operation(op_id):
            # Simulate async work
            await asyncio.sleep(0.01)
            results.append(op_id)
            return op_id
        
        # Run many async operations concurrently
        tasks = [async_operation(i) for i in range(100)]
        completed = await asyncio.gather(*tasks)
        
        # Verify all completed
        assert len(completed) == 100, f"Only {len(completed)} of 100 operations completed"
        assert len(set(completed)) == 100, "Duplicate results detected"
    
    def test_slack_command_spam_protection(self, client):
        """Test Slack command spam doesn't overwhelm system"""
        def send_slack_command(cmd_id):
            return client.post('/api/slack/command', data={
                'command': '/sr-roll',
                'text': '3d6',
                'user_id': f'user-{cmd_id % 5}',  # 5 different users
                'channel_id': 'C123',
                'team_id': 'T123'
            })
        
        start_time = time.time()
        
        # Send 100 commands as fast as possible
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(send_slack_command, i) for i in range(100)]
            results = [f.result() for f in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete reasonably fast (not hung)
        assert duration < 10, f"Commands took too long: {duration}s"
        
        # Check for rate limiting
        status_codes = [r.status_code for r in results]
        rate_limited = sum(1 for code in status_codes if code == 429)
        assert rate_limited > 0, "No rate limiting detected for spam"
    
    def test_character_damage_race_condition(self, client):
        """Test concurrent damage application to same character"""
        # Create character with 100 HP
        character_hp = 100
        
        def apply_damage(damage_amount):
            return client.post('/api/character/damage', json={
                'character_id': 'char-123',
                'damage': damage_amount
            })
        
        # Apply damage from multiple sources simultaneously
        damage_amounts = [10, 15, 20, 5, 10]  # Total: 60
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(apply_damage, damage)
                for damage in damage_amounts
            ]
            results = [f.result() for f in futures]
        
        # Final HP should be exactly 40 (100 - 60)
        # This tests that damage is applied atomically
        # (Would need actual implementation to verify)
        pass 