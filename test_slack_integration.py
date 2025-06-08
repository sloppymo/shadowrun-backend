import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app import app, db, SlackSession, Session, UserRole
from slack_integration import SlackBot, SlackCommandProcessor

class TestSlackIntegration:
    """Test suite for Slack integration"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.test_client() as client:
            with app.app_context():
                db.create_all()
                # Clear existing data
                db.session.query(SlackSession).delete()
                db.session.query(Session).delete()
                db.session.query(UserRole).delete()
                db.session.commit()
                yield client
    
    @pytest.fixture
    def mock_slack_bot(self):
        """Mock Slack bot for testing"""
        with patch('app.slack_bot') as mock_bot:
            mock_bot.verify_slack_request.return_value = True
            mock_bot.send_message = AsyncMock()
            mock_bot.upload_image = AsyncMock()
            mock_bot.format_shadowrun_response.return_value = [
                {"type": "section", "text": {"type": "mrkdwn", "text": "Test response"}}
            ]
            yield mock_bot
    
    def test_slack_bot_initialization(self):
        """Test Slack bot initialization"""
        with patch.dict('os.environ', {
            'SLACK_BOT_TOKEN': 'test_token',
            'SLACK_SIGNING_SECRET': 'test_secret'
        }):
            bot = SlackBot()
            assert bot.is_configured() == True
    
    def test_slack_bot_not_configured(self):
        """Test Slack bot when not configured"""
        with patch.dict('os.environ', {}, clear=True):
            bot = SlackBot()
            assert bot.is_configured() == False
    
    def test_slash_command_help(self, client, mock_slack_bot):
        """Test slash command help"""
        response = client.post('/api/slack/command', data={
            'command': '/sr-help',
            'text': '',
            'user_id': 'U123',
            'channel_id': 'C123',
            'team_id': 'T123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['response_type'] == 'ephemeral'
        assert 'Shadowrun Slack Commands' in str(data['blocks'])
    
    def test_slash_command_session_create(self, client, mock_slack_bot):
        """Test session creation via Slack command"""
        with app.app_context():
            response = client.post('/api/slack/command', data={
                'command': '/sr-session',
                'text': 'create Test Campaign',
                'user_id': 'U123',
                'channel_id': 'C123',
                'team_id': 'T123'
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['response_type'] == 'in_channel'
            
            # Check database
            slack_session = SlackSession.query.filter_by(
                slack_team_id='T123',
                slack_channel_id='C123'
            ).first()
            assert slack_session is not None
            
            session = Session.query.get(slack_session.session_id)
            assert session.name == 'Test Campaign'
            assert session.gm_user_id == 'U123'
    
    def test_slash_command_session_info(self, client, mock_slack_bot):
        """Test session info via Slack command"""
        with app.app_context():
            # Create test session
            session = Session(name='Test Session', gm_user_id='U123')
            db.session.add(session)
            db.session.flush()
            
            slack_session = SlackSession(
                slack_team_id='T123',
                slack_channel_id='C123',
                session_id=session.id
            )
            db.session.add(slack_session)
            db.session.commit()
            
            # Test info command
            response = client.post('/api/slack/command', data={
                'command': '/sr-session',
                'text': 'info',
                'user_id': 'U456',
                'channel_id': 'C123',
                'team_id': 'T123'
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'Test Session' in str(data['blocks'])
    
    def test_slash_command_ai_request(self, client, mock_slack_bot):
        """Test AI request via Slack command"""
        with app.app_context():
            # Create test session
            session = Session(name='Test Session', gm_user_id='U123')
            db.session.add(session)
            db.session.flush()
            
            slack_session = SlackSession(
                slack_team_id='T123',
                slack_channel_id='C123',
                session_id=session.id
            )
            db.session.add(slack_session)
            db.session.commit()
            
            response = client.post('/api/slack/command', data={
                'command': '/sr-ai',
                'text': 'What do I see in the warehouse?',
                'user_id': 'U456',
                'channel_id': 'C123',
                'team_id': 'T123'
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['response_type'] == 'in_channel'
            assert 'Processing request' in str(data['blocks'])
    
    def test_slash_command_image_generate(self, client, mock_slack_bot):
        """Test image generation via Slack command"""
        with app.app_context():
            # Create test session
            session = Session(name='Test Session', gm_user_id='U123')
            db.session.add(session)
            db.session.flush()
            
            slack_session = SlackSession(
                slack_team_id='T123',
                slack_channel_id='C123',
                session_id=session.id
            )
            db.session.add(slack_session)
            db.session.commit()
            
            response = client.post('/api/slack/command', data={
                'command': '/sr-image',
                'text': 'A cyberpunk street scene',
                'user_id': 'U456',
                'channel_id': 'C123',
                'team_id': 'T123'
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['response_type'] == 'in_channel'
            assert 'Generating image' in str(data['blocks'])
    
    def test_slash_command_dice_roll(self, client, mock_slack_bot):
        """Test dice rolling via Slack command"""
        response = client.post('/api/slack/command', data={
            'command': '/sr-roll',
            'text': '3d6',
            'user_id': 'U456',
            'channel_id': 'C123',
            'team_id': 'T123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['response_type'] == 'in_channel'
        assert 'rolled 3d6' in str(data['blocks'])
    
    def test_slash_command_dm_dashboard(self, client, mock_slack_bot):
        """Test DM dashboard access via Slack command"""
        response = client.post('/api/slack/command', data={
            'command': '/sr-dm',
            'text': 'dashboard',
            'user_id': 'U123',
            'channel_id': 'C123',
            'team_id': 'T123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['response_type'] == 'ephemeral'
        assert 'DM Dashboard' in str(data['blocks'])
    
    def test_slack_events_url_verification(self, client, mock_slack_bot):
        """Test Slack URL verification"""
        response = client.post('/api/slack/events', json={
            'type': 'url_verification',
            'challenge': 'test_challenge_123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['challenge'] == 'test_challenge_123'
    
    def test_slack_events_app_mention(self, client, mock_slack_bot):
        """Test app mention event"""
        response = client.post('/api/slack/events', json={
            'type': 'event_callback',
            'event': {
                'type': 'app_mention',
                'channel': 'C123',
                'user': 'U456',
                'text': '<@BOT_ID> help'
            }
        })
        
        assert response.status_code == 200
        mock_slack_bot.send_message.assert_called()
    
    def test_slack_interactive_dm_dashboard_button(self, client, mock_slack_bot):
        """Test interactive DM dashboard button"""
        payload = {
            'type': 'block_actions',
            'actions': [{
                'action_id': 'dm_dashboard_button',
                'value': 'open_dm_dashboard'
            }],
            'channel': {'id': 'C123'},
            'team': {'id': 'T123'}
        }
        
        response = client.post('/api/slack/interactive', data={
            'payload': json.dumps(payload)
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'Opening DM Dashboard' in data['text']
    
    def test_command_processor_invalid_command(self):
        """Test invalid command processing"""
        processor = SlackCommandProcessor(SlackBot())
        
        context = {
            'command': '/sr-invalid',
            'args': [],
            'user_id': 'U123',
            'channel_id': 'C123',
            'team_id': 'T123',
            'slack_session_id': 'T123_C123'
        }
        
        result = asyncio.run(processor.process_command(context))
        
        assert result['response_type'] == 'ephemeral'
        assert 'Unknown command' in result['text']
    
    def test_slack_session_mapping(self, client):
        """Test Slack session mapping functionality"""
        with app.app_context():
            # Test creating session mapping
            session = Session(name='Test Session', gm_user_id='U123')
            db.session.add(session)
            db.session.flush()
            
            slack_session = SlackSession(
                slack_team_id='T123',
                slack_channel_id='C123',
                session_id=session.id
            )
            db.session.add(slack_session)
            db.session.commit()
            
            # Test retrieving mapping
            found_session = SlackSession.query.filter_by(
                slack_team_id='T123',
                slack_channel_id='C123'
            ).first()
            
            assert found_session is not None
            assert found_session.session_id == session.id
    
    def test_dice_roll_parsing(self):
        """Test dice notation parsing"""
        processor = SlackCommandProcessor(SlackBot())
        
        # Test valid dice notation
        context = {
            'command': '/sr-roll',
            'args': ['2d10'],
            'user_id': 'U123',
            'channel_id': 'C123',
            'team_id': 'T123',
            'slack_session_id': 'T123_C123'
        }
        
        result = asyncio.run(processor.handle_dice_command(context))
        
        assert result['response_type'] == 'in_channel'
        assert 'rolled 2d10' in str(result['blocks'])
        
        # Test invalid dice notation
        context['args'] = ['invalid']
        result = asyncio.run(processor.handle_dice_command(context))
        
        assert result['response_type'] == 'ephemeral'
        assert 'Invalid dice notation' in result['text']
    
    def test_slack_response_formatting(self):
        """Test Slack response formatting"""
        bot = SlackBot()
        
        # Test error formatting
        error_blocks = bot.format_shadowrun_response("Test error", "error")
        assert any("System Error" in str(block) for block in error_blocks)
        
        # Test success formatting
        success_blocks = bot.format_shadowrun_response("Test success", "success")
        assert any("System Success" in str(block) for block in success_blocks)
        
        # Test DM notification formatting
        dm_blocks = bot.format_shadowrun_response("DM notification", "dm_notification")
        assert any("DM Notification" in str(block) for block in dm_blocks)
        assert any("Open DM Dashboard" in str(block) for block in dm_blocks)
    
    @patch('app.create_pending_response')
    def test_process_slack_ai_request(self, mock_create_pending, client):
        """Test processing AI request from Slack"""
        with app.app_context():
            # Setup session
            session = Session(name='Test Session', gm_user_id='U123')
            db.session.add(session)
            db.session.flush()
            
            slack_session = SlackSession(
                slack_team_id='T123',
                slack_channel_id='C123',
                session_id=session.id
            )
            db.session.add(slack_session)
            db.session.commit()
            
            mock_create_pending.return_value = 'response123'
            
            # Mock slack_bot
            with patch('app.slack_bot') as mock_bot:
                mock_bot.send_message = AsyncMock()
                
                from app import process_slack_ai_request
                import asyncio
                asyncio.run(process_slack_ai_request(
                    session_id='T123_C123',
                    user_id='U456',
                    message='Test AI request',
                    channel_id='C123'
                ))
                
                mock_create_pending.assert_called_once()
                mock_bot.send_message.assert_called_once()

if __name__ == '__main__':
    pytest.main([__file__, '-v']) 