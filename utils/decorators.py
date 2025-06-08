"""
Flask decorators for security and functionality
"""
from functools import wraps
from flask import request, jsonify, g
from datetime import datetime, timedelta
import hashlib
import redis
import os
from typing import Optional, Callable
import jwt

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


def rate_limited(requests: int = 10, window: int = 60):
    """
    Rate limiting decorator
    
    Args:
        requests: Number of requests allowed
        window: Time window in seconds
        
    Usage:
        @rate_limited(requests=5, window=60)  # 5 requests per minute
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier
            client_id = request.headers.get('X-Forwarded-For', request.remote_addr)
            endpoint = request.endpoint
            key = f"rate_limit:{endpoint}:{client_id}"
            
            current_time = datetime.utcnow()
            
            if REDIS_AVAILABLE:
                # Use Redis for distributed rate limiting
                try:
                    current_count = redis_client.incr(key)
                    if current_count == 1:
                        redis_client.expire(key, window)
                    
                    if current_count > requests:
                        return jsonify({
                            'error': 'Rate limit exceeded',
                            'retry_after': window
                        }), 429
                except:
                    # Redis error, allow request but log it
                    print(f"Redis error in rate limiting for {key}")
            else:
                # In-memory fallback
                if key not in rate_limit_storage:
                    rate_limit_storage[key] = []
                
                # Clean old entries
                cutoff_time = current_time - timedelta(seconds=window)
                rate_limit_storage[key] = [
                    t for t in rate_limit_storage[key] 
                    if t > cutoff_time
                ]
                
                # Check rate limit
                if len(rate_limit_storage[key]) >= requests:
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'retry_after': window
                    }), 429
                
                # Add current request
                rate_limit_storage[key].append(current_time)
            
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