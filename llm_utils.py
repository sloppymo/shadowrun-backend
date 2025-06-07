import os
import httpx

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Model endpoints (can be adjusted)
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
DEEPSEEK_CHAT_URL = "https://api.deepseek.com/v1/chat/completions"
ANTHROPIC_CHAT_URL = "https://api.anthropic.com/v1/messages"
MISTRAL_CHAT_URL = "https://api.mistral.ai/v1/chat/completions"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

import json

async def call_openai_stream(messages):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "stream": True
    }
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", OPENAI_CHAT_URL, headers=headers, json=payload, timeout=60) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data = line[len("data: "):]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            yield content
                    except Exception:
                        continue

async def call_openai(messages, stream=False):
    if stream:
        raise RuntimeError("Use call_openai_stream for streaming")
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "stream": False
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(OPENAI_CHAT_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()

async def call_deepseek(messages, stream=False):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",  # Adjust if you want to use coder or other DeepSeek models
        "messages": messages,
        "stream": stream
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(DEEPSEEK_CHAT_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()

# Anthropic Claude
async def call_anthropic(messages, stream=False):
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    prompt = messages[0]["content"] if messages else ""
    payload = {
        "model": "claude-3-opus-20240229",
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": stream
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(ANTHROPIC_CHAT_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()

# Mistral
async def call_mistral(messages, stream=False):
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistral-large-latest",  # You can change to 'mistral-small-latest', etc.
        "messages": messages,
        "stream": stream
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(MISTRAL_CHAT_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()

# OpenRouter
async def call_openrouter(messages, model_name="openai/gpt-4o", stream=False):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,  # e.g., "openai/gpt-4o", "mistralai/mistral-large", "google/gemini-pro"
        "messages": messages,
        "stream": stream
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(OPENROUTER_CHAT_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()

# Utility to select model
async def call_llm(model, messages, stream=False, model_name=None):
    if model == "openai":
        if stream:
            return call_openai_stream(messages)
        return await call_openai(messages, stream=False)
    elif model == "deepseek":
        return await call_deepseek(messages, stream)
    elif model == "anthropic":
        return await call_anthropic(messages, stream)
    elif model == "mistral":
        return await call_mistral(messages, stream)
    elif model == "openrouter":
        # Pass model_name for OpenRouter, default to GPT-4o if not provided
        return await call_openrouter(messages, model_name or "openai/gpt-4o", stream)
    else:
        raise ValueError(f"Unknown model: {model}")

# --- DM Review System Functions ---

async def create_pending_response(session_id, user_id, context, response_type='narrative', priority=1):
    """
    Create a pending AI response that requires DM review.
    Returns the pending response ID for tracking.
    """
    from app import db, PendingResponse, DmNotification, Session
    import uuid
    
    # Generate AI response
    messages = [
        {"role": "system", "content": "You are an expert Shadowrun GM AI. Provide a creative, rules-accurate response to the player's action. Keep responses concise but engaging."},
        {"role": "user", "content": context}
    ]
    
    try:
        # Generate the AI response (non-streaming for review workflow)
        llm_response = await call_openai(messages, stream=False)
        ai_response = llm_response['choices'][0]['message']['content']
        
        # Create pending response
        pending_id = str(uuid.uuid4())
        pending = PendingResponse(
            id=pending_id,
            session_id=session_id,
            user_id=user_id,
            context=context,
            ai_response=ai_response,
            response_type=response_type,
            priority=priority
        )
        
        # Get the GM for this session
        session = Session.query.filter_by(id=session_id).first()
        if session:
            # Create notification for the DM
            notification = DmNotification(
                session_id=session_id,
                dm_user_id=session.gm_user_id,
                pending_response_id=pending_id,
                notification_type='new_review' if priority <= 2 else 'urgent_review',
                message=f"New {response_type} response needs review from player {user_id}"
            )
            
            db.session.add(notification)
        
        db.session.add(pending)
        db.session.commit()
        
        return {
            'status': 'pending_review',
            'pending_response_id': pending_id,
            'message': 'Response generated and queued for DM review'
        }
        
    except Exception as e:
        print(f"Error creating pending response: {str(e)}")
        raise e

async def get_reviewed_response(pending_response_id):
    """
    Get a reviewed response by ID. Returns None if still pending.
    """
    from app import PendingResponse
    
    pending = PendingResponse.query.filter_by(id=pending_response_id).first()
    if not pending:
        return None
    
    if pending.status in ['approved', 'edited']:
        return {
            'status': pending.status,
            'response': pending.final_response,
            'dm_notes': pending.dm_notes,
            'reviewed_at': pending.reviewed_at.isoformat() if pending.reviewed_at else None
        }
    elif pending.status == 'rejected':
        return {
            'status': 'rejected',
            'dm_notes': pending.dm_notes,
            'reviewed_at': pending.reviewed_at.isoformat() if pending.reviewed_at else None
        }
    else:
        return {
            'status': 'pending',
            'message': 'Still awaiting DM review'
        }

async def call_llm_with_review(session_id, user_id, context, model='openai', response_type='narrative', priority=1, require_review=True):
    """
    Enhanced LLM call that can either require DM review or provide immediate response.
    """
    if require_review:
        return await create_pending_response(session_id, user_id, context, response_type, priority)
    else:
        # Direct LLM call without review
        messages = [
            {"role": "system", "content": "You are an expert Shadowrun GM AI. Provide a creative, rules-accurate response to the player's action."},
            {"role": "user", "content": context}
        ]
        return await call_llm(model, messages, stream=False)
