"""
Flask decorators for security and functionality
"""
from functools import wraps
from flask import request, jsonify, g
from datetime import datetime, timedelta
import hashlib
import redis
import os
from typing import Optional, Callable, Dict, Any
import jwt
import time
from redis import Redis

# Initialize Redis for rate limiting (optional, will fall back to in-memory if not available)
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        decode_responses=True
    )
    redis_client.ping()
    REDIS_AVAILABLE = True
except:
    redis_client = None
    REDIS_AVAILABLE = False
    # In-memory fallback for rate limiting
    rate_limit_storage = {}

# JWT secret
JWT_SECRET = os.getenv('JWT_SECRET', 'shadowrun-secret-key-change-in-production')

# Rate limit configurations
RATE_LIMITS = {
    'dm_review': {
        'requests': 60,  # requests per window
        'window': 60,    # window in seconds
        'burst': 10      # burst allowance
    },
    'ai_operation': {
        'requests': 30,  # requests per window
        'window': 60,    # window in seconds
        'burst': 5       # burst allowance
    },
    'default': {
        'requests': 100, # requests per window
        'window': 60,    # window in seconds
        'burst': 20      # burst allowance
    }
}

def get_rate_limit_key(user_id: str, category: str) -> str:
    """Generate Redis key for rate limiting"""
    return f"rate_limit:{category}:{user_id}"

def check_rate_limit(user_id: str, category: str) -> tuple[bool, Optional[int]]:
    """Check if request is within rate limits"""
    if not user_id:
        return False, None
        
    config = RATE_LIMITS.get(category, RATE_LIMITS['default'])
    key = get_rate_limit_key(user_id, category)
    
    # Get current count and window start
    pipe = redis_client.pipeline()
    now = int(time.time())
    window_start = now - config['window']
    
    # Clean old entries and get current count
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, config['window'])
    _, count, _, _ = pipe.execute()
    
    # Check if within limits
    if count > config['requests'] + config['burst']:
        return False, None
        
    return True, config['window'] - (now - window_start)

def rate_limited(category: str = 'default'):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = request.json.get('user_id') if request.is_json else request.args.get('user_id')
            
            allowed, retry_after = check_rate_limit(user_id, category)
            if not allowed:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': retry_after
                }), 429
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def auth_required(role: Optional[str] = None):
    """
    Decorator to require authentication and optionally a specific role
    
    Usage:
        @auth_required()  # Any authenticated user
        @auth_required('gm')  # Only GMs
        @auth_required('player')  # Only players
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Authorization header required'}), 401
            
            # Extract token
            try:
                token_type, token = auth_header.split(' ', 1)
                if token_type.lower() != 'bearer':
                    return jsonify({'error': 'Invalid authorization type'}), 401
            except ValueError:
                return jsonify({'error': 'Invalid authorization header format'}), 401
            
            # Verify JWT token
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                g.user_id = payload.get('user_id')
                g.user_role = payload.get('role')
                g.session_id = payload.get('session_id')
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token has expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'Invalid token'}), 401
            
            # Check role if specified
            if role and g.user_role != role:
                return jsonify({'error': f'Role {role} required'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def validate_session_access():
    """
    Decorator to validate user has access to the session
    Requires auth_required to be applied first
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            session_id = kwargs.get('session_id')
            if not session_id:
                return jsonify({'error': 'Session ID required'}), 400
            
            # Import here to avoid circular imports
            from app import Session, UserRole
            
            # Check if session exists
            session = Session.query.filter_by(id=session_id).first()
            if not session:
                return jsonify({'error': 'Session not found'}), 404
            
            # Check if user has access to this session
            user_id = g.get('user_id')
            if not user_id:
                return jsonify({'error': 'User ID not found in token'}), 401
            
            # GMs always have access to their sessions
            if session.gm_user_id == user_id:
                g.is_gm = True
                return f(*args, **kwargs)
            
            # Check if user is a participant
            user_role = UserRole.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).first()
            
            if not user_role:
                return jsonify({'error': 'Access denied to this session'}), 403
            
            g.is_gm = False
            g.user_session_role = user_role.role
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def log_api_call():
    """
    Decorator to log API calls for debugging and auditing
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = datetime.utcnow()
            
            # Log request
            print(f"API Call: {request.method} {request.path} - User: {g.get('user_id', 'anonymous')}")
            
            # Call function
            result = f(*args, **kwargs)
            
            # Log response time
            duration = (datetime.utcnow() - start_time).total_seconds()
            print(f"API Response: {request.path} - Duration: {duration:.3f}s")
            
            return result
        
        return decorated_function
    return decorator

def require_json():
    """
    Decorator to ensure request has JSON content
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def sanitize_output():
    """
    Decorator to sanitize API output to prevent XSS
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from utils.validators import sanitize_html_content
            
            result = f(*args, **kwargs)
            
            # If result is a string, sanitize it
            if isinstance(result, str):
                return sanitize_html_content(result)
            
            # If result is a Flask response, don't modify
            if hasattr(result, 'get_json'):
                return result
            
            # If result is a dict/list, recursively sanitize strings
            def sanitize_recursive(obj):
                if isinstance(obj, str):
                    return sanitize_html_content(obj)
                elif isinstance(obj, dict):
                    return {k: sanitize_recursive(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [sanitize_recursive(item) for item in obj]
                return obj
            
            return sanitize_recursive(result)
        
        return decorated_function
    return decorator 