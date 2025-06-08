"""
WebSocket authentication and message validation middleware
"""
import os
import jwt
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
from utils.validators import WebSocketMessageSchema
from pydantic import ValidationError

JWT_SECRET = os.getenv('JWT_SECRET', 'shadowrun-secret-key-change-in-production')
MAX_CONNECTIONS_PER_USER = 5
CONNECTION_TIMEOUT = 300  # 5 minutes

# Track active connections
active_connections: Dict[str, List[Dict[str, Any]]] = {}


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a JWT token and return the payload
    
    Args:
        token: JWT token string
        
    Returns:
        Token payload dict or None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def ws_auth_required(f: Callable) -> Callable:
    """
    WebSocket authentication decorator
    
    Usage:
        @ws_auth_required
        async def handle_websocket(ws, path, user_data):
            # user_data contains authenticated user info
    """
    @wraps(f)
    async def decorated_function(ws, path, *args, **kwargs):
        # Extract token from query params or first message
        token = None
        
        # Try to get token from path query params
        if '?token=' in path:
            token = path.split('?token=')[1].split('&')[0]
        
        # If no token in path, expect it in the first message
        if not token:
            try:
                # Wait for auth message with timeout
                auth_message = await asyncio.wait_for(ws.recv(), timeout=10.0)
                auth_data = json.loads(auth_message)
                
                if auth_data.get('type') != 'auth':
                    await ws.send(json.dumps({
                        'type': 'error',
                        'error': 'First message must be auth'
                    }))
                    await ws.close()
                    return
                
                token = auth_data.get('token')
            except asyncio.TimeoutError:
                await ws.send(json.dumps({
                    'type': 'error',
                    'error': 'Authentication timeout'
                }))
                await ws.close()
                return
            except json.JSONDecodeError:
                await ws.send(json.dumps({
                    'type': 'error',
                    'error': 'Invalid JSON'
                }))
                await ws.close()
                return
        
        # Verify token
        if not token:
            await ws.send(json.dumps({
                'type': 'error',
                'error': 'No authentication token provided'
            }))
            await ws.close()
            return
        
        user_data = verify_jwt_token(token)
        if not user_data:
            await ws.send(json.dumps({
                'type': 'error',
                'error': 'Invalid or expired token'
            }))
            await ws.close()
            return
        
        # Check connection limits
        user_id = user_data.get('user_id')
        if user_id in active_connections:
            if len(active_connections[user_id]) >= MAX_CONNECTIONS_PER_USER:
                await ws.send(json.dumps({
                    'type': 'error',
                    'error': 'Connection limit exceeded'
                }))
                await ws.close()
                return
        
        # Register connection
        connection_info = {
            'ws': ws,
            'connected_at': datetime.utcnow(),
            'last_activity': datetime.utcnow(),
            'path': path
        }
        
        if user_id not in active_connections:
            active_connections[user_id] = []
        active_connections[user_id].append(connection_info)
        
        try:
            # Send auth success
            await ws.send(json.dumps({
                'type': 'auth_success',
                'user_id': user_id,
                'session_id': user_data.get('session_id')
            }))
            
            # Call the actual handler with user data
            await f(ws, path, user_data, *args, **kwargs)
            
        finally:
            # Clean up connection
            if user_id in active_connections:
                active_connections[user_id] = [
                    conn for conn in active_connections[user_id]
                    if conn['ws'] != ws
                ]
                if not active_connections[user_id]:
                    del active_connections[user_id]
    
    return decorated_function


def ws_message_shape_validator(expected_schema: type = WebSocketMessageSchema):
    """
    Decorator to validate WebSocket message shapes
    
    Args:
        expected_schema: Pydantic schema class to validate against
        
    Usage:
        @ws_message_shape_validator(MyMessageSchema)
        async def handle_message(message_data: dict):
            # message_data is validated
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        async def decorated_function(message: str, *args, **kwargs):
            try:
                # Parse JSON
                data = json.loads(message)
                
                # Validate with schema
                validated = expected_schema(**data)
                
                # Call function with validated data
                return await f(validated.dict(), *args, **kwargs)
                
            except json.JSONDecodeError:
                return {
                    'type': 'error',
                    'error': 'Invalid JSON format'
                }
            except ValidationError as e:
                return {
                    'type': 'error',
                    'error': f'Validation error: {str(e)}'
                }
            except Exception as e:
                return {
                    'type': 'error',
                    'error': f'Unexpected error: {str(e)}'
                }
        
        return decorated_function
    return decorator


class WebSocketRateLimiter:
    """Rate limiter for WebSocket messages"""
    
    def __init__(self, max_messages: int = 30, window_seconds: int = 60):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.user_messages: Dict[str, List[datetime]] = {}
    
    def check_rate_limit(self, user_id: str) -> bool:
        """
        Check if user is within rate limit
        
        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # Clean old messages
        if user_id in self.user_messages:
            self.user_messages[user_id] = [
                msg_time for msg_time in self.user_messages[user_id]
                if msg_time > cutoff
            ]
        else:
            self.user_messages[user_id] = []
        
        # Check limit
        if len(self.user_messages[user_id]) >= self.max_messages:
            return False
        
        # Add current message
        self.user_messages[user_id].append(now)
        return True


class WebSocketConnectionManager:
    """Manages WebSocket connections with security features"""
    
    def __init__(self):
        self.rate_limiter = WebSocketRateLimiter()
        self.connections: Dict[str, Dict[str, Any]] = {}  # session_id -> connection info
    
    async def connect(self, ws, session_id: str, user_id: str, role: str):
        """Register a new connection"""
        if session_id not in self.connections:
            self.connections[session_id] = {}
        
        self.connections[session_id][user_id] = {
            'ws': ws,
            'role': role,
            'connected_at': datetime.utcnow(),
            'last_ping': datetime.utcnow()
        }
    
    async def disconnect(self, session_id: str, user_id: str):
        """Remove a connection"""
        if session_id in self.connections:
            if user_id in self.connections[session_id]:
                del self.connections[session_id][user_id]
            
            # Clean up empty sessions
            if not self.connections[session_id]:
                del self.connections[session_id]
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any], 
                                  exclude_user: Optional[str] = None):
        """Broadcast message to all users in a session"""
        if session_id not in self.connections:
            return
        
        message_str = json.dumps(message)
        
        # Send to all connections in session
        disconnected = []
        for user_id, conn_info in self.connections[session_id].items():
            if user_id == exclude_user:
                continue
            
            try:
                await conn_info['ws'].send(message_str)
            except:
                # Mark for disconnection
                disconnected.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected:
            await self.disconnect(session_id, user_id)
    
    async def send_to_user(self, session_id: str, user_id: str, message: Dict[str, Any]):
        """Send message to specific user"""
        if session_id in self.connections and user_id in self.connections[session_id]:
            try:
                await self.connections[session_id][user_id]['ws'].send(json.dumps(message))
            except:
                await self.disconnect(session_id, user_id)
    
    async def check_message_rate_limit(self, user_id: str) -> bool:
        """Check if user is within message rate limit"""
        return self.rate_limiter.check_rate_limit(user_id)
    
    async def cleanup_stale_connections(self):
        """Remove connections that haven't pinged recently"""
        cutoff = datetime.utcnow() - timedelta(seconds=CONNECTION_TIMEOUT)
        
        for session_id in list(self.connections.keys()):
            for user_id in list(self.connections[session_id].keys()):
                conn_info = self.connections[session_id][user_id]
                if conn_info['last_ping'] < cutoff:
                    await self.disconnect(session_id, user_id)
    
    def update_ping(self, session_id: str, user_id: str):
        """Update last ping time for a connection"""
        if session_id in self.connections and user_id in self.connections[session_id]:
            self.connections[session_id][user_id]['last_ping'] = datetime.utcnow()


# Global connection manager
ws_connection_manager = WebSocketConnectionManager()


# Periodic cleanup task
async def periodic_cleanup():
    """Run periodic cleanup of stale connections"""
    while True:
        await asyncio.sleep(60)  # Run every minute
        await ws_connection_manager.cleanup_stale_connections() 