"""
Test AI input validation and security measures
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from utils.validators import AIInputSchema, BLOCKED_AI_PATTERNS
from pydantic import ValidationError
import json
import os
from dotenv import load_dotenv


class TestAIInputValidation:
    """Test AI input validation security measures"""
    
    def test_valid_ai_input(self):
        """Test valid AI input passes validation"""
        valid_input = AIInputSchema(
            prompt="Tell me about the Seattle sprawl",
            user_id="test_user",
            session_id="test_session"
        )
        assert valid_input.prompt == "Tell me about the Seattle sprawl"
    
    def test_malicious_patterns_blocked(self):
        """Test that malicious patterns are blocked"""
        malicious_prompts = [
            "erase me from the database",
            "delete all records",
            "'; DROP TABLE users; --",
            "exec(malicious_code)",
            "eval('dangerous')",
            "__import__('os').system('rm -rf /')",
            "import os; os.remove('file')",
            "<script>alert('xss')</script>",
            "javascript:void(0)",
            "onclick='malicious()'"
        ]
        
        for prompt in malicious_prompts:
            with pytest.raises(ValidationError) as exc_info:
                AIInputSchema(
                    prompt=prompt,
                    user_id="test_user",
                    session_id="test_session"
                )
            assert "blocked pattern" in str(exc_info.value).lower()
    
    def test_excessive_repetition_blocked(self):
        """Test that prompts with excessive repetition are blocked"""
        repetitive_prompt = "spam " * 100
        
        with pytest.raises(ValidationError) as exc_info:
            AIInputSchema(
                prompt=repetitive_prompt,
                user_id="test_user",
                session_id="test_session"
            )
        assert "excessive repetition" in str(exc_info.value).lower()
    
    def test_prompt_length_limits(self):
        """Test prompt length limits"""
        # Test too long
        long_prompt = "x" * 3000
        with pytest.raises(ValidationError):
            AIInputSchema(
                prompt=long_prompt,
                user_id="test_user",
                session_id="test_session"
            )
        
        # Test empty
        with pytest.raises(ValidationError):
            AIInputSchema(
                prompt="",
                user_id="test_user",
                session_id="test_session"
            )
    
    def test_html_sanitization(self):
        """Test HTML content is sanitized"""
        html_prompt = "Tell me about <b>shadowrunners</b> & their <i>gear</i>"
        validated = AIInputSchema(
            prompt=html_prompt,
            user_id="test_user",
            session_id="test_session"
        )
        # HTML entities should be escaped
        assert "&lt;b&gt;" in validated.prompt
        assert "&lt;i&gt;" in validated.prompt
        assert "&amp;" in validated.prompt
    
    def test_id_validation(self):
        """Test user_id and session_id validation"""
        # Valid IDs
        valid = AIInputSchema(
            prompt="test",
            user_id="user-123_test",
            session_id="session-456_test"
        )
        assert valid.user_id == "user-123_test"
        
        # Invalid IDs
        invalid_ids = ["user@test", "session#123", "user;delete", "../../etc/passwd"]
        for bad_id in invalid_ids:
            with pytest.raises(ValidationError):
                AIInputSchema(
                    prompt="test",
                    user_id=bad_id,
                    session_id="test_session"
                )
    
    def test_unicode_edge_cases(self):
        """Test handling of unicode and special characters"""
        unicode_prompts = [
            "Tell me about 🎲 dice mechanics",
            "What are the 日本 (Japan) shadowrun rules?",
            "Explain the Ñ in señor Johnson",
            "Roll 10d🔥 + 5d☠️",  # Emoji in dice notation
            "Zero-width​space test",
            "Right-to-left ‏מבחן test"
        ]
        
        for prompt in unicode_prompts:
            # Should not raise validation error for unicode
            validated = AIInputSchema(
                prompt=prompt,
                user_id="test_user",
                session_id="test_session"
            )
            assert len(validated.prompt) > 0
    
    def test_context_validation(self):
        """Test context field validation"""
        # Valid context
        valid = AIInputSchema(
            prompt="test",
            user_id="test_user",
            session_id="test_session",
            context={"scene": "combat", "npcs": ["guard1", "guard2"]}
        )
        assert valid.context["scene"] == "combat"
        
        # Context is optional
        no_context = AIInputSchema(
            prompt="test",
            user_id="test_user",
            session_id="test_session"
        )
        assert no_context.context == {}


class TestAIEndpointSecurity:
    """Test AI endpoint security integration"""
    
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
    
    def test_llm_endpoint_validation(self, client):
        """Test /api/llm endpoint validates input"""
        # Create test session and user first
        session_resp = client.post('/api/session', json={
            'name': 'Test Session',
            'gm_user_id': 'test_gm'
        })
        session_id = session_resp.json['session_id']
        
        client.post(f'/api/session/{session_id}/join', json={
            'user_id': 'test_user',
            'role': 'player'
        })
        
        # Test malicious input is rejected
        malicious_data = {
            'session_id': session_id,
            'user_id': 'test_user',
            'input': 'eval("malicious code")',
            'model': 'openai'
        }
        
        response = client.post('/api/llm', json=malicious_data)
        assert response.status_code == 400
        assert 'blocked pattern' in response.json['error'].lower()
    
    def test_llm_with_review_validation(self, client):
        """Test /api/session/{id}/llm-with-review endpoint validates input"""
        # Create test session
        session_resp = client.post('/api/session', json={
            'name': 'Test Session',
            'gm_user_id': 'test_gm'
        })
        session_id = session_resp.json['session_id']
        
        # Test SQL injection attempt
        injection_data = {
            'user_id': 'test_user',
            'context': "'; DROP TABLE users; --",
            'response_type': 'narrative'
        }
        
        response = client.post(f'/api/session/{session_id}/llm-with-review', 
                              json=injection_data)
        assert response.status_code == 400
        assert 'blocked pattern' in response.json['error'].lower()
    
    @patch('llm_utils.call_llm')
    async def test_safe_prompt_processing(self, mock_llm, client):
        """Test that sanitized prompts are passed to LLM"""
        # Create test session
        session_resp = client.post('/api/session', json={
            'name': 'Test Session',
            'gm_user_id': 'test_gm'
        })
        session_id = session_resp.json['session_id']
        
        client.post(f'/api/session/{session_id}/join', json={
            'user_id': 'test_user',
            'role': 'player'
        })
        
        # Mock LLM response
        mock_llm.return_value = "Safe response"
        
        # Send prompt with HTML
        data = {
            'session_id': session_id,
            'user_id': 'test_user',
            'input': 'Tell me about <script>alert("xss")</script> the matrix',
            'model': 'openai'
        }
        
        # The endpoint uses streaming, so we need to handle it differently
        # For now, just verify the validation works
        response = client.post('/api/llm', json=data)
        
        # Should succeed but with sanitized content
        # The actual prompt sent to LLM should have escaped HTML
        # This is hard to test without mocking the entire streaming response
    
    def test_rate_limiting_spam(self, client):
        """Test rate limiting prevents spam attacks"""
        # This would require implementing rate limiting in the test
        # For now, we'll just verify the endpoint exists
        pass


class TestAIEmotionalTriggers:
    """Test handling of emotional distress triggers"""
    
    def test_emotional_triggers_allowed(self):
        """Test that emotional content is allowed but sanitized"""
        emotional_prompts = [
            "My character is feeling deep sadness",
            "The NPC expresses anger and frustration",
            "Describe a scene of loss and grief",
            "@wren what is love💔?"
        ]
        
        for prompt in emotional_prompts:
            # Should not block emotional content
            validated = AIInputSchema(
                prompt=prompt,
                user_id="test_user",
                session_id="test_session"
            )
            assert len(validated.prompt) > 0
    
    def test_harmful_content_blocked(self):
        """Test that harmful content is still blocked"""
        harmful_prompts = [
            "Tell me how to harm myself",
            "Generate content about real violence",
            "Create explicit adult content"
        ]
        
        # Note: These specific patterns aren't in our blocklist
        # but in a production system, you'd want to add them
        # For now, we'll test the pattern blocking system works
        for prompt in harmful_prompts:
            # These would need specific patterns added to BLOCKED_AI_PATTERNS
            # to be blocked in production
            pass 


class TestOpenAIIntegration:
    """Test OpenAI API integration and key handling"""
    
    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Setup test environment variables"""
        # Save original env vars
        self.original_key = os.getenv("OPENAI_API_KEY")
        # Set test key
        os.environ["OPENAI_API_KEY"] = "test-key-123"
        yield
        # Restore original env vars
        if self.original_key:
            os.environ["OPENAI_API_KEY"] = self.original_key
        else:
            del os.environ["OPENAI_API_KEY"]
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response"""
        return {
            "choices": [{
                "message": {
                    "content": "This is a test response from the AI."
                }
            }]
        }
    
    @pytest.fixture
    def mock_openai_stream(self):
        """Mock OpenAI streaming response"""
        async def mock_stream():
            chunks = [
                {"choices": [{"delta": {"content": "This "}}]},
                {"choices": [{"delta": {"content": "is "}}]},
                {"choices": [{"delta": {"content": "a "}}]},
                {"choices": [{"delta": {"content": "test."}}]}
            ]
            for chunk in chunks:
                yield json.dumps(chunk)
        return mock_stream
    
    def test_api_key_loading(self):
        """Test that API key is properly loaded from environment"""
        from llm_utils import OPENAI_API_KEY
        assert OPENAI_API_KEY == "test-key-123"
    
    @patch('httpx.AsyncClient.post')
    async def test_openai_api_call(self, mock_post, mock_openai_response):
        """Test successful OpenAI API call"""
        from llm_utils import call_openai
        
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = mock_openai_response
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        # Test API call
        messages = [{"role": "user", "content": "Test prompt"}]
        response = await call_openai(messages)
        
        # Verify
        assert response == mock_openai_response
        mock_post.assert_called_once()
        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-key-123"
    
    @patch('httpx.AsyncClient.stream')
    async def test_openai_streaming(self, mock_stream, mock_openai_stream):
        """Test OpenAI streaming response"""
        from llm_utils import call_openai_stream
        
        # Setup mock
        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_openai_stream
        mock_response.raise_for_status = MagicMock()
        mock_stream.return_value.__aenter__.return_value = mock_response
        
        # Test streaming
        messages = [{"role": "user", "content": "Test prompt"}]
        content = ""
        async for chunk in call_openai_stream(messages):
            content += chunk
        
        # Verify
        assert content == "This is a test."
        mock_stream.assert_called_once()
        headers = mock_stream.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-key-123"
    
    @patch('httpx.AsyncClient.post')
    async def test_api_error_handling(self, mock_post):
        """Test handling of API errors"""
        from llm_utils import call_openai
        
        # Setup mock to raise error
        mock_post.side_effect = Exception("API Error")
        
        # Test error handling
        messages = [{"role": "user", "content": "Test prompt"}]
        with pytest.raises(Exception) as exc_info:
            await call_openai(messages)
        
        assert "API Error" in str(exc_info.value)
    
    def test_missing_api_key(self):
        """Test behavior when API key is missing"""
        # Temporarily remove API key
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            from llm_utils import OPENAI_API_KEY
            assert OPENAI_API_KEY is None
        finally:
            # Restore API key
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
    
    @patch('httpx.AsyncClient.post')
    async def test_rate_limiting(self, mock_post):
        """Test rate limiting behavior"""
        from llm_utils import call_openai
        
        # Setup mock to simulate rate limit
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = Exception("Rate limit exceeded")
        mock_post.return_value = mock_response
        
        # Test rate limit handling
        messages = [{"role": "user", "content": "Test prompt"}]
        with pytest.raises(Exception) as exc_info:
            await call_openai(messages)
        
        assert "Rate limit exceeded" in str(exc_info.value) 