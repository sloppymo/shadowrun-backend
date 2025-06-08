"""
Comprehensive logging system for Shadowrun RPG
Provides context-aware logging with security redaction and performance tracking
"""
import logging
import time
import inspect
import os
import hashlib
import json
import traceback
import secrets
from functools import wraps
from pythonjsonlogger import jsonlogger
from typing import Any, Dict, Optional, Callable
from datetime import datetime

# Sensitive keys that should be redacted in logs
SENSITIVE_KEYS = {
    'password', 'token', 'api_key', 'secret', 'authorization',
    'cookie', 'session_id', 'jwt', 'bearer', 'api_secret',
    'client_secret', 'private_key', 'encryption_key'
}

# High-risk patterns for crisis detection
CRISIS_PATTERNS = [
    'end it all', 'kill myself', 'suicide', 'worthless',
    'nobody cares', 'better off dead', 'self harm'
]

class ContextLogger:
    """Context-aware logger with request tracking and security features"""
    
    def __init__(self, name: str = "shadowrun"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # JSON formatter for structured logs
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={'asctime': 'timestamp'}
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Context variables
        self.request_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.game_session_id: Optional[str] = None
        
    def bind(self, request_id: Optional[str] = None, 
             user_id: Optional[str] = None,
             session_id: Optional[str] = None,
             game_session_id: Optional[str] = None) -> 'ContextLogger':
        """Bind context variables to logger"""
        if request_id:
            self.request_id = request_id
        if user_id:
            self.user_id = user_id
        if session_id:
            self.session_id = session_id
        if game_session_id:
            self.game_session_id = game_session_id
        return self
    
    def _get_caller_info(self) -> Dict[str, Any]:
        """Get information about the calling function"""
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            caller_frame = frame.f_back.f_back
            return {
                "file": os.path.basename(caller_frame.f_code.co_filename),
                "line": caller_frame.f_lineno,
                "function": caller_frame.f_code.co_name,
            }
        return {}
    
    def _redact_sensitive(self, data: Any) -> Any:
        """Recursively redact sensitive information"""
        if isinstance(data, dict):
            return {
                k: '***REDACTED***' if any(sens in k.lower() for sens in SENSITIVE_KEYS) 
                else self._redact_sensitive(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._redact_sensitive(item) for item in data]
        elif isinstance(data, str):
            # Check for patterns like "Bearer token123"
            if any(pattern in data.lower() for pattern in ['bearer ', 'basic ', 'token=']):
                return '***REDACTED***'
        return data
    
    def _detect_crisis(self, message: str, **kwargs) -> bool:
        """Detect potential crisis situations in messages"""
        text_to_check = str(message).lower()
        for key, value in kwargs.items():
            if isinstance(value, str):
                text_to_check += " " + value.lower()
        
        return any(pattern in text_to_check for pattern in CRISIS_PATTERNS)
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal logging method with context and redaction"""
        # Check for crisis situations
        if self._detect_crisis(message, **kwargs):
            self._log_crisis_detected(message, kwargs)
        
        # Build context
        context = {
            "timestamp_ms": int(time.time() * 1000),
            "request_id": self.request_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "game_session_id": self.game_session_id,
            **self._get_caller_info()
        }
        
        # Redact sensitive data
        safe_kwargs = self._redact_sensitive(kwargs)
        
        # Add all kwargs to context
        context.update(safe_kwargs)
        
        # Log with context
        getattr(self.logger, level)(message, extra=context)
    
    def _log_crisis_detected(self, message: str, data: Dict):
        """Special handling for crisis situations"""
        self.logger.critical("CRISIS_INPUT_DETECTED", extra={
            "crisis_type": "emotional_distress",
            "original_message": message[:100] + "...",  # Truncate for privacy
            "user_id": self.user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "action_required": "immediate_support"
        })
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context"""
        self._log("debug", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with context"""
        self._log("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context"""
        self._log("warning", message, **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message with context and optional exception"""
        if exception:
            kwargs['exception_type'] = type(exception).__name__
            kwargs['exception_message'] = str(exception)
            kwargs['stack_trace'] = traceback.format_exc()
        self._log("error", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context"""
        self._log("critical", message, **kwargs)
    
    def security_event(self, event_type: str, severity: str = "MEDIUM", **details):
        """Log security-related events"""
        self.warning(f"SECURITY_EVENT_{event_type}", 
                    event_type=event_type,
                    severity=severity,
                    stack_trace="".join(traceback.format_stack()[-5:]),  # Last 5 frames
                    **details)
    
    def performance_metric(self, operation: str, duration_ms: float, **kwargs):
        """Log performance metrics"""
        level = "warning" if duration_ms > 1000 else "info" if duration_ms > 500 else "debug"
        self._log(level, f"PERFORMANCE_{operation}", 
                 operation=operation,
                 duration_ms=round(duration_ms, 2),
                 **kwargs)
    
    def game_event(self, event_type: str, **kwargs):
        """Log game-specific events"""
        self.info(f"GAME_EVENT_{event_type}", 
                 event_type=event_type,
                 game_session_id=self.game_session_id,
                 **kwargs)
    
    def dice_roll(self, expression: str, result: Any, user_id: str, **kwargs):
        """Log dice roll with integrity check"""
        roll_hash = hashlib.sha256(
            f"{expression}-{user_id}-{time.time()}".encode()
        ).hexdigest()[:8]
        
        self.info("DICE_ROLL",
                 expression=expression,
                 result=result,
                 user_id=user_id,
                 roll_hash=roll_hash,
                 **kwargs)
    
    def ai_request(self, prompt: str, model: str, **kwargs):
        """Log AI request with prompt hash"""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:8]
        self.info("AI_REQUEST",
                 prompt_length=len(prompt),
                 prompt_hash=prompt_hash,
                 model=model,
                 **kwargs)
    
    def cost_event(self, service: str, cost_usd: float, **kwargs):
        """Log cost-incurring events"""
        self.info("COST_EVENT",
                 service=service,
                 cost_usd=round(cost_usd, 4),
                 **kwargs)

# Global logger instance
logger = ContextLogger()

# Timing decorator
def timed(operation_name: Optional[str] = None):
    """Decorator to time function execution"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            operation = operation_name or func.__name__
            
            logger.debug(f"{operation}_started",
                        args_count=len(args),
                        kwargs_keys=list(kwargs.keys()))
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                logger.performance_metric(operation, duration_ms,
                                        status="success",
                                        args_hash=hash(str(args)),
                                        kwargs_hash=hash(str(kwargs)))
                
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                logger.error(f"{operation}_failed",
                           exception=e,
                           duration_ms=round(duration_ms, 2))
                raise
        
        return wrapper
    return decorator

# Log sampling for high-volume endpoints
class LogSampler:
    """Sample logs for high-volume operations"""
    
    def __init__(self, sample_rate: float = 0.1):
        self.sample_rate = sample_rate
        self._counter = 0
    
    def should_log(self) -> bool:
        """Determine if this call should be logged"""
        self._counter += 1
        return self._counter % int(1 / self.sample_rate) == 0

# Create sampler instances for different operations
dice_roll_sampler = LogSampler(0.1)  # Log 10% of dice rolls
websocket_sampler = LogSampler(0.01)  # Log 1% of WebSocket messages

def log_game_state_change(session_id: str, action: Dict[str, Any], 
                         prev_state_hash: str, new_state_hash: str):
    """Log game state transitions"""
    logger.game_event("STATE_TRANSITION",
                     session_id=session_id,
                     action_type=action.get('type'),
                     player_id=action.get('player_id'),
                     prev_state=prev_state_hash[:8],
                     new_state=new_state_hash[:8],
                     state_changed=prev_state_hash != new_state_hash)

def log_slack_event(event_type: str, team_id: str, channel_id: str, 
                   user_id: str, **kwargs):
    """Log Slack integration events"""
    logger.info(f"SLACK_{event_type}",
               event_type=event_type,
               team_id=team_id,
               channel_id=channel_id,
               slack_user_id=user_id,
               **kwargs)

# Crisis detection helper
def detect_crisis_content(text: str) -> bool:
    """Check if text contains crisis indicators"""
    return any(pattern in text.lower() for pattern in CRISIS_PATTERNS) 