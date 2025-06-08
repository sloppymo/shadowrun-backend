"""
Flask middleware for comprehensive request/response logging
Tracks all HTTP requests with timing, context, and security information
"""
import time
import secrets
import json
from flask import g, request, Response
from typing import Optional
from utils.logger import logger

def get_user_id() -> Optional[str]:
    """Extract user ID from request (JWT, session, etc.)"""
    # Try to get from various sources
    user_id = None
    
    # From request JSON
    if request.is_json and request.json:
        user_id = request.json.get('user_id')
    
    # From query params
    if not user_id:
        user_id = request.args.get('user_id')
    
    # From headers (if using JWT)
    if not user_id and 'Authorization' in request.headers:
        # This would normally decode JWT
        # For now, just mark that auth header exists
        user_id = "authenticated_user"
    
    return user_id

def init_request_logging(app):
    """Initialize request logging middleware"""
    
    @app.before_request
    def log_request_start():
        """Log request start and bind context"""
        # Generate request ID
        request_id = secrets.token_urlsafe(8)
        g.request_id = request_id
        g.start_time = time.perf_counter()
        
        # Get user ID
        user_id = get_user_id()
        
        # Get session ID from path if present
        session_id = None
        if '/session/' in request.path:
            parts = request.path.split('/session/')
            if len(parts) > 1:
                session_id = parts[1].split('/')[0]
        
        # Bind context to logger
        logger.bind(
            request_id=request_id,
            user_id=user_id,
            session_id=session_id
        )
        
        # Prepare safe headers (remove sensitive ones)
        safe_headers = {}
        sensitive_headers = {'authorization', 'cookie', 'x-api-key', 'x-slack-signature'}
        for key, value in request.headers:
            if key.lower() not in sensitive_headers:
                safe_headers[key] = value
            else:
                safe_headers[key] = '***REDACTED***'
        
        # Log request details
        logger.info("REQUEST_STARTED",
                   method=request.method,
                   path=request.path,
                   remote_addr=request.remote_addr,
                   user_agent=request.user_agent.string,
                   content_length=request.content_length,
                   params=dict(request.args),
                   headers=safe_headers)
        
        # Log request body for non-GET requests (with size limit)
        if request.method != 'GET' and request.is_json:
            try:
                body = request.get_json()
                if body:
                    # Limit body size in logs
                    body_str = json.dumps(body)
                    if len(body_str) > 1000:
                        logger.debug("REQUEST_BODY_TRUNCATED",
                                   body_preview=body_str[:500] + "...",
                                   body_size=len(body_str))
                    else:
                        logger.debug("REQUEST_BODY", body=body)
            except Exception as e:
                logger.warning("REQUEST_BODY_PARSE_ERROR", error=str(e))
    
    @app.after_request
    def log_response(response: Response) -> Response:
        """Log response details and timing"""
        if hasattr(g, 'start_time'):
            duration_ms = (time.perf_counter() - g.start_time) * 1000
            
            # Determine log level based on status code
            if response.status_code >= 500:
                log_func = logger.error
            elif response.status_code >= 400:
                log_func = logger.warning
            else:
                log_func = logger.info
            
            # Log response
            log_func("REQUEST_COMPLETED",
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                    response_size=response.content_length or len(response.data or b''),
                    content_type=response.content_type)
            
            # Add performance warning for slow requests
            if duration_ms > 1000:
                logger.warning("SLOW_REQUEST_DETECTED",
                             path=request.path,
                             duration_ms=round(duration_ms, 2),
                             method=request.method)
            
            # Add request ID to response headers for tracing
            response.headers['X-Request-ID'] = g.get('request_id', 'unknown')
        
        return response
    
    @app.errorhandler(Exception)
    def log_unhandled_exception(error: Exception):
        """Log unhandled exceptions"""
        if hasattr(g, 'start_time'):
            duration_ms = (time.perf_counter() - g.start_time) * 1000
        else:
            duration_ms = 0
        
        logger.error("UNHANDLED_EXCEPTION",
                    exception=error,
                    path=request.path,
                    method=request.method,
                    duration_ms=round(duration_ms, 2))
        
        # Return generic error response
        return {
            'error': 'Internal server error',
            'request_id': g.get('request_id', 'unknown')
        }, 500
    
    # Log app startup
    logger.info("APPLICATION_STARTED",
               environment=app.config.get('ENV', 'production'),
               debug_mode=app.debug,
               host=app.config.get('HOST', '0.0.0.0'),
               port=app.config.get('PORT', 5000))

def log_database_query(query: str, params: dict, duration_ms: float):
    """Log database query performance"""
    # Only log slow queries in production, all queries in debug
    if logger.logger.isEnabledFor(logger.logger.debug) or duration_ms > 100:
        logger.debug("DATABASE_QUERY",
                    query_type=query.split()[0].upper(),
                    duration_ms=round(duration_ms, 2),
                    query_preview=query[:200] + "..." if len(query) > 200 else query,
                    param_count=len(params) if params else 0)

def log_api_call(service: str, endpoint: str, duration_ms: float, 
                status_code: Optional[int] = None, error: Optional[str] = None):
    """Log external API calls"""
    log_data = {
        "service": service,
        "endpoint": endpoint,
        "duration_ms": round(duration_ms, 2),
        "status_code": status_code
    }
    
    if error:
        logger.error("EXTERNAL_API_ERROR", error=error, **log_data)
    else:
        logger.info("EXTERNAL_API_CALL", **log_data)

def log_websocket_event(event_type: str, session_id: str, user_id: str, **kwargs):
    """Log WebSocket events"""
    logger.info(f"WEBSOCKET_{event_type}",
               event_type=event_type,
               ws_session_id=session_id,
               ws_user_id=user_id,
               **kwargs) 