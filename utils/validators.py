"""
Security validators for Shadowrun RPG API inputs
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
import re
from datetime import datetime, timedelta
import html
import json

# Blocked patterns for AI prompts
BLOCKED_AI_PATTERNS = [
    r'erase\s+me',
    r'delete\s+all',
    r'drop\s+table',
    r'exec\s*\(',
    r'eval\s*\(',
    r'__import__',
    r'import\s+os',
    r'import\s+sys',
    r'subprocess',
    r'\\x[0-9a-fA-F]{2}',  # Hex escape sequences
    r'<script',
    r'javascript:',
    r'onclick\s*=',
    r'onerror\s*=',
]

# Maximum lengths
MAX_PROMPT_LENGTH = 2000
MAX_MESSAGE_LENGTH = 5000
MAX_DICE_NOTATION_LENGTH = 20


class AIInputSchema(BaseModel):
    """Validator for AI/LLM input prompts"""
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    context: Optional[Dict[str, Any]] = Field(default={})
    user_id: str = Field(..., min_length=1, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)
    
    @validator('prompt')
    def validate_prompt(cls, v):
        """Check for malicious patterns in prompts"""
        # Normalize the prompt for checking
        normalized = v.lower().strip()
        
        # Check for blocked patterns
        for pattern in BLOCKED_AI_PATTERNS:
            if re.search(pattern, normalized):
                raise ValueError(f"Prompt contains blocked pattern: {pattern}")
        
        # Check for excessive repetition (potential DoS)
        if len(set(normalized.split())) < len(normalized.split()) * 0.1:
            raise ValueError("Prompt contains excessive repetition")
        
        # Sanitize HTML entities
        return html.escape(v)
    
    @validator('user_id', 'session_id')
    def validate_ids(cls, v):
        """Validate ID format"""
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError("Invalid ID format")
        return v


class WebSocketMessageSchema(BaseModel):
    """Validator for WebSocket messages"""
    type: str = Field(..., min_length=1, max_length=50)
    payload: Dict[str, Any] = Field(...)
    user_id: str = Field(..., min_length=1, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    @validator('type')
    def validate_message_type(cls, v):
        """Validate message type"""
        allowed_types = [
            'chat', 'dice_roll', 'character_update', 'scene_update',
            'entity_update', 'image_request', 'ping', 'pong'
        ]
        if v not in allowed_types:
            raise ValueError(f"Invalid message type: {v}")
        return v
    
    @validator('payload')
    def validate_payload_size(cls, v):
        """Check payload size"""
        serialized = json.dumps(v)
        if len(serialized) > MAX_MESSAGE_LENGTH:
            raise ValueError("Payload too large")
        return v


class SlackRequestSchema(BaseModel):
    """Validator for Slack requests with timestamp verification"""
    timestamp: str = Field(...)
    signature: str = Field(...)
    body: Dict[str, Any] = Field(...)
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Ensure request is not older than 5 minutes"""
        try:
            request_time = datetime.fromtimestamp(int(v))
            current_time = datetime.utcnow()
            
            if current_time - request_time > timedelta(minutes=5):
                raise ValueError("Request timestamp too old")
            
            # Also check for future timestamps (clock skew)
            if request_time > current_time + timedelta(minutes=1):
                raise ValueError("Request timestamp in the future")
                
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid timestamp format: {e}")
        
        return v


class DiceNotationSchema(BaseModel):
    """Validator for dice notation"""
    notation: str = Field(..., min_length=1, max_length=MAX_DICE_NOTATION_LENGTH)
    
    @validator('notation')
    def validate_dice_notation(cls, v):
        """Validate dice notation format"""
        # Remove whitespace
        v = v.strip()
        
        # Check for basic format (e.g., 3d6, 2d10+5, 4d8-2)
        pattern = r'^(\d{1,2})d(\d{1,3})([+\-]\d{1,2})?$'
        if not re.match(pattern, v.lower()):
            raise ValueError("Invalid dice notation format")
        
        # Parse to check limits
        match = re.match(r'(\d+)d(\d+)', v.lower())
        if match:
            num_dice = int(match.group(1))
            dice_size = int(match.group(2))
            
            if num_dice > 20:
                raise ValueError("Maximum 20 dice allowed")
            if dice_size > 100:
                raise ValueError("Maximum d100 allowed")
        
        return v


class CharacterDataSchema(BaseModel):
    """Validator for character data updates"""
    name: Optional[str] = Field(None, max_length=100)
    handle: Optional[str] = Field(None, max_length=100)
    attributes: Optional[Dict[str, int]] = None
    skills: Optional[Dict[str, int]] = None
    
    @validator('name', 'handle')
    def sanitize_strings(cls, v):
        """Sanitize character strings"""
        if v:
            # Remove any HTML/script tags
            v = re.sub(r'<[^>]+>', '', v)
            # Escape HTML entities
            v = html.escape(v)
        return v
    
    @validator('attributes', 'skills')
    def validate_numeric_values(cls, v):
        """Ensure all values are valid integers"""
        if v:
            for key, value in v.items():
                if not isinstance(value, int) or value < 0 or value > 20:
                    raise ValueError(f"Invalid value for {key}: {value}")
        return v


def sanitize_html_content(content: str) -> str:
    """
    Sanitize HTML content for safe rendering
    This is a basic implementation - in production, use bleach or similar
    """
    # Remove script tags and event handlers
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', content, flags=re.IGNORECASE)
    content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
    
    # Escape remaining HTML
    return html.escape(content) 