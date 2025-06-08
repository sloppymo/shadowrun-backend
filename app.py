import os
import uuid
import asyncio
import json
import traceback
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import httpx
from datetime import datetime
from typing import Dict, Optional

# Import local modules
from llm_utils import call_llm, call_llm_with_review, get_reviewed_response, call_openai_stream
from image_gen_utils import create_image_generation_request, process_image_generation, get_session_images
from slack_integration import slack_bot, slack_processor

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

app = Flask(__name__)
CORS(app)

# Configure SQLite
db_path = os.path.join(os.path.dirname(__file__), 'shadowrun.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Models ---
class ChatMemory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, db.ForeignKey('session.id'), nullable=False)
    user_id = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False)  # 'player', 'gm', 'observer'
    messages = db.Column(db.Text, nullable=False, default="[]")  # JSON-encoded list of {role, content}

class Session(db.Model):
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String, nullable=False)
    gm_user_id = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class UserRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, db.ForeignKey('session.id'), nullable=False)
    user_id = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False)  # 'player', 'gm', 'observer'

class Scene(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, db.ForeignKey('session.id'), nullable=False, unique=True)
    summary = db.Column(db.Text, nullable=False, default="")

class Entity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, db.ForeignKey('session.id'), nullable=False)
    name = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)  # e.g., 'player', 'npc', 'spirit', etc.
    status = db.Column(db.String, nullable=True)  # e.g., 'active', 'marked', etc.
    extra_data = db.Column(db.Text, nullable=True)  # JSON-encoded string for extensibility

# --- Character Model for SR6E ---
class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, db.ForeignKey('session.id'), nullable=False)
    user_id = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    handle = db.Column(db.String, nullable=True)
    archetype = db.Column(db.String, nullable=True)
    background_seed = db.Column(db.String, nullable=True)
    gender = db.Column(db.String, nullable=True)
    pronouns = db.Column(db.String, nullable=True)
    essence_anchor = db.Column(db.String, nullable=True)
    build_method = db.Column(db.String, nullable=True)  # 'priority', 'karma', 'narrative'
    attributes = db.Column(db.Text, nullable=True)  # JSON: {body, agility, reaction, logic, intuition, willpower, charisma, edge}
    skills = db.Column(db.Text, nullable=True)  # JSON: {skill_name: value, ...}
    qualities = db.Column(db.Text, nullable=True)  # JSON: {positive: [...], negative: [...], symbolic: [...]}
    gear = db.Column(db.Text, nullable=True)  # JSON: list of gear/cyberware
    lifestyle = db.Column(db.Text, nullable=True)  # JSON: lifestyle info
    contacts = db.Column(db.Text, nullable=True)  # JSON: list of contacts
    narrative_hooks = db.Column(db.Text, nullable=True)  # JSON: list of hooks/flags
    core_traumas = db.Column(db.Text, nullable=True)  # JSON: [{label, description, mechanical_effect}]
    core_strengths = db.Column(db.Text, nullable=True)  # JSON: [{label, description, mechanical_effect}]
    created_at = db.Column(db.DateTime, server_default=db.func.now())

# --- DM Review System Models ---
class PendingResponse(db.Model):
    """Stores AI-generated responses awaiting DM review"""
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String, db.ForeignKey('session.id'), nullable=False)
    user_id = db.Column(db.String, nullable=False)  # Player who triggered the AI response
    context = db.Column(db.Text, nullable=False)  # Original player input/context
    ai_response = db.Column(db.Text, nullable=False)  # Generated AI response
    response_type = db.Column(db.String, nullable=False)  # 'narrative', 'dice_roll', 'npc_action', etc.
    status = db.Column(db.String, nullable=False, default='pending')  # 'pending', 'approved', 'rejected', 'edited'
    dm_notes = db.Column(db.Text, nullable=True)  # DM's notes/comments
    final_response = db.Column(db.Text, nullable=True)  # Final approved/edited response
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    reviewed_at = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.Integer, nullable=False, default=1)  # 1=low, 2=medium, 3=high

class DmNotification(db.Model):
    """Notifications for DMs about pending reviews"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, db.ForeignKey('session.id'), nullable=False)
    dm_user_id = db.Column(db.String, nullable=False)
    pending_response_id = db.Column(db.String, db.ForeignKey('pending_response.id'), nullable=False)
    notification_type = db.Column(db.String, nullable=False)  # 'new_review', 'urgent_review'
    message = db.Column(db.String, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class ReviewHistory(db.Model):
    """Audit trail of DM review actions"""
    id = db.Column(db.Integer, primary_key=True)
    pending_response_id = db.Column(db.String, db.ForeignKey('pending_response.id'), nullable=False)
    dm_user_id = db.Column(db.String, nullable=False)
    action = db.Column(db.String, nullable=False)  # 'approved', 'rejected', 'edited'
    original_response = db.Column(db.Text, nullable=True)  # For tracking edits
    final_response = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class GeneratedImage(db.Model):
    """Stores generated scene images"""
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String, db.ForeignKey('session.id'), nullable=False)
    user_id = db.Column(db.String, nullable=False)  # User who requested the image
    prompt = db.Column(db.Text, nullable=False)  # Original description/prompt
    enhanced_prompt = db.Column(db.Text, nullable=True)  # AI-enhanced prompt for image generation
    image_url = db.Column(db.String, nullable=True)  # URL to generated image
    thumbnail_url = db.Column(db.String, nullable=True)  # URL to thumbnail
    provider = db.Column(db.String, nullable=False)  # 'dalle', 'stable_diffusion', 'midjourney'
    status = db.Column(db.String, nullable=False, default='pending')  # 'pending', 'generating', 'completed', 'failed'
    error_message = db.Column(db.Text, nullable=True)  # Error details if generation failed
    generation_time = db.Column(db.Float, nullable=True)  # Time taken to generate (seconds)
    tags = db.Column(db.Text, nullable=True)  # JSON: scene tags for categorization
    is_favorite = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    completed_at = db.Column(db.DateTime, nullable=True)

class ImageGeneration(db.Model):
    """Tracks image generation requests and queue"""
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String, db.ForeignKey('session.id'), nullable=False)
    user_id = db.Column(db.String, nullable=False)
    request_type = db.Column(db.String, nullable=False)  # 'scene', 'character', 'location', 'item'
    context = db.Column(db.Text, nullable=False)  # Scene description or context
    style_preferences = db.Column(db.Text, nullable=True)  # JSON: style settings
    priority = db.Column(db.Integer, nullable=False, default=1)  # 1=low, 2=medium, 3=high
    status = db.Column(db.String, nullable=False, default='queued')  # 'queued', 'processing', 'completed', 'failed'
    result_image_id = db.Column(db.String, db.ForeignKey('generated_image.id'), nullable=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

class SlackSession(db.Model):
    """Maps Slack channels to game sessions"""
    id = db.Column(db.Integer, primary_key=True)
    slack_team_id = db.Column(db.String, nullable=False)
    slack_channel_id = db.Column(db.String, nullable=False)
    session_id = db.Column(db.String, db.ForeignKey('session.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    # Ensure unique mapping per channel
    __table_args__ = (db.UniqueConstraint('slack_team_id', 'slack_channel_id'),)

# --- API Endpoints ---

# --- Character Endpoints ---
@app.route('/api/session/<session_id>/characters', methods=['GET'])
def get_characters(session_id):
    chars = Character.query.filter_by(session_id=session_id).all()
    return jsonify([
        {
            'id': c.id,
            'user_id': c.user_id,
            'name': c.name,
            'handle': c.handle,
            'archetype': c.archetype,
            'background_seed': c.background_seed,
            'gender': c.gender,
            'pronouns': c.pronouns,
            'essence_anchor': c.essence_anchor,
            'build_method': c.build_method,
            'attributes': c.attributes,
            'skills': c.skills,
            'qualities': c.qualities,
            'gear': c.gear,
            'lifestyle': c.lifestyle,
            'contacts': c.contacts,
            'narrative_hooks': c.narrative_hooks,
            'core_traumas': c.core_traumas,
            'core_strengths': c.core_strengths,
            'created_at': c.created_at.isoformat() if c.created_at else None
        }
        for c in chars
    ])

@app.route('/api/session/<session_id>/character', methods=['POST'])
def create_character(session_id):
    data = request.json
    try:
        char = Character(
            session_id=session_id,
            user_id=data.get('user_id'),
            name=data.get('name'),
            handle=data.get('handle'),
            archetype=data.get('archetype'),
            background_seed=data.get('background_seed'),
            gender=data.get('gender'),
            pronouns=data.get('pronouns'),
            essence_anchor=data.get('essence_anchor'),
            build_method=data.get('build_method'),
            attributes=data.get('attributes'),
            skills=data.get('skills'),
            qualities=data.get('qualities'),
            gear=data.get('gear'),
            lifestyle=data.get('lifestyle'),
            contacts=data.get('contacts'),
            narrative_hooks=data.get('narrative_hooks'),
            core_traumas=data.get('core_traumas'),
            core_strengths=data.get('core_strengths'),
        )
        db.session.add(char)
        db.session.commit()
        return jsonify({'status': 'success', 'character_id': char.id}), 201
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/session/<session_id>/character/<int:char_id>', methods=['GET'])
def get_character(session_id, char_id):
    char = Character.query.filter_by(session_id=session_id, id=char_id).first()
    if not char:
        return jsonify({'status': 'error', 'error': 'Character not found'}), 404
    return jsonify({
        'id': char.id,
        'user_id': char.user_id,
        'name': char.name,
        'handle': char.handle,
        'archetype': char.archetype,
        'background_seed': char.background_seed,
        'gender': char.gender,
        'pronouns': char.pronouns,
        'essence_anchor': char.essence_anchor,
        'build_method': char.build_method,
        'attributes': char.attributes,
        'skills': char.skills,
        'qualities': char.qualities,
        'gear': char.gear,
        'lifestyle': char.lifestyle,
        'contacts': char.contacts,
        'narrative_hooks': char.narrative_hooks,
        'core_traumas': char.core_traumas,
        'core_strengths': char.core_strengths,
        'created_at': char.created_at.isoformat() if char.created_at else None
    })

@app.route('/api/session/<session_id>/character/<int:char_id>', methods=['PUT'])
def update_character(session_id, char_id):
    char = Character.query.filter_by(session_id=session_id, id=char_id).first()
    if not char:
        return jsonify({'status': 'error', 'error': 'Character not found'}), 404
    data = request.json
    for field in [
        'name','handle','archetype','background_seed','gender','pronouns','essence_anchor','build_method',
        'attributes','skills','qualities','gear','lifestyle','contacts','narrative_hooks','core_traumas','core_strengths']:
        if field in data:
            setattr(char, field, data[field])
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/session/<session_id>/character/<int:char_id>', methods=['DELETE'])
def delete_character(session_id, char_id):
    char = Character.query.filter_by(session_id=session_id, id=char_id).first()
    if not char:
        return jsonify({'status': 'error', 'error': 'Character not found'}), 404
    db.session.delete(char)
    db.session.commit()
    return jsonify({'status': 'deleted'})

# --- Scene Endpoints ---
@app.route('/api/session/<session_id>/scene', methods=['GET'])
def get_scene(session_id):
    scene = Scene.query.filter_by(session_id=session_id).first()
    if scene:
        return jsonify({'session_id': session_id, 'summary': scene.summary})
    else:
        return jsonify({'session_id': session_id, 'summary': ''})

@app.route('/api/session/<session_id>/scene', methods=['POST'])
def update_scene(session_id):
    data = request.json
    summary = data.get('summary', '')
    user_id = data.get('user_id')
    # Permission check: only GM can update
    session = Session.query.filter_by(id=session_id).first()
    if not session or session.gm_user_id != user_id:
        return jsonify({'error': 'Only GM can update scene.'}), 403
    scene = Scene.query.filter_by(session_id=session_id).first()
    if not scene:
        scene = Scene(session_id=session_id, summary=summary)
        db.session.add(scene)
    else:
        scene.summary = summary
    db.session.commit()
    return jsonify({'session_id': session_id, 'summary': scene.summary})

# --- Entity Endpoints ---
@app.route('/api/session/<session_id>/entities', methods=['GET'])
def get_entities(session_id):
    entities = Entity.query.filter_by(session_id=session_id).all()
    return jsonify([
        {'id': e.id, 'name': e.name, 'type': e.type, 'status': e.status, 'extra_data': e.extra_data}
        for e in entities
    ])

@app.route('/api/session/<session_id>/entities', methods=['POST'])
def add_or_update_entity(session_id):
    data = request.json
    user_id = data.get('user_id')
    # Permission check: only GM can add/update
    session = Session.query.filter_by(id=session_id).first()
    if not session or session.gm_user_id != user_id:
        return jsonify({'error': 'Only GM can modify entities.'}), 403
    entity_id = data.get('id')
    if entity_id:
        # Update existing
        entity = Entity.query.filter_by(id=entity_id, session_id=session_id).first()
        if not entity:
            return jsonify({'error': 'Entity not found.'}), 404
        entity.name = data.get('name', entity.name)
        entity.type = data.get('type', entity.type)
        entity.status = data.get('status', entity.status)
        entity.extra_data = data.get('extra_data', entity.extra_data)
    else:
        # Add new
        entity = Entity(
            session_id=session_id,
            name=data['name'],
            type=data['type'],
            status=data.get('status'),
            extra_data=data.get('extra_data')
        )
        db.session.add(entity)
    db.session.commit()
    return jsonify({'id': entity.id, 'name': entity.name, 'type': entity.type, 'status': entity.status, 'extra_data': entity.extra_data})

@app.route('/api/session/<session_id>/entities/<int:entity_id>', methods=['DELETE'])
def delete_entity(session_id, entity_id):
    data = request.json
    user_id = data.get('user_id')
    # Permission check: only GM can delete
    session = Session.query.filter_by(id=session_id).first()
    if not session or session.gm_user_id != user_id:
        return jsonify({'error': 'Only GM can delete entities.'}), 403
    entity = Entity.query.filter_by(id=entity_id, session_id=session_id).first()
    if not entity:
        return jsonify({'error': 'Entity not found.'}), 404
    db.session.delete(entity)
    db.session.commit()
    return jsonify({'status': 'deleted'})

# --- DM Review System API Endpoints ---

@app.route('/api/session/<session_id>/pending-responses', methods=['GET'])
def get_pending_responses(session_id):
    """Get all pending responses for a session (DMs only)"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    # Verify the user is the GM for this session
    session = Session.query.filter_by(id=session_id).first()
    if not session or session.gm_user_id != user_id:
        return jsonify({'error': 'Only GMs can view pending responses'}), 403
    
    pending = PendingResponse.query.filter_by(session_id=session_id, status='pending').order_by(
        PendingResponse.priority.desc(), PendingResponse.created_at.asc()
    ).all()
    
    return jsonify([{
        'id': p.id,
        'user_id': p.user_id,
        'context': p.context,
        'ai_response': p.ai_response,
        'response_type': p.response_type,
        'priority': p.priority,
        'created_at': p.created_at.isoformat() if p.created_at else None
    } for p in pending])

@app.route('/api/session/<session_id>/pending-response/<response_id>/review', methods=['POST'])
def review_response(session_id, response_id):
    """DM reviews and approves/rejects/edits a pending response"""
    data = request.json
    dm_user_id = data.get('user_id')
    action = data.get('action')  # 'approve', 'reject', 'edit'
    final_response = data.get('final_response', '')
    dm_notes = data.get('dm_notes', '')
    
    if not dm_user_id or not action:
        return jsonify({'error': 'user_id and action are required'}), 400
    
    # Verify the user is the GM for this session
    session = Session.query.filter_by(id=session_id).first()
    if not session or session.gm_user_id != dm_user_id:
        return jsonify({'error': 'Only GMs can review responses'}), 403
    
    pending = PendingResponse.query.filter_by(id=response_id, session_id=session_id).first()
    if not pending:
        return jsonify({'error': 'Pending response not found'}), 404
    
    # Create review history entry
    original_response = pending.ai_response
    
    # Update pending response based on action
    if action == 'approve':
        pending.status = 'approved'
        pending.final_response = pending.ai_response
    elif action == 'reject':
        pending.status = 'rejected'
        pending.final_response = None
    elif action == 'edit':
        pending.status = 'edited'
        pending.final_response = final_response
    else:
        return jsonify({'error': 'Invalid action'}), 400
    
    pending.dm_notes = dm_notes
    pending.reviewed_at = db.func.now()
    
    # Create review history
    history = ReviewHistory(
        pending_response_id=response_id,
        dm_user_id=dm_user_id,
        action=action,
        original_response=original_response,
        final_response=pending.final_response,
        notes=dm_notes
    )
    
    db.session.add(history)
    db.session.commit()
    
    return jsonify({'status': 'success', 'action': action})

@app.route('/api/session/<session_id>/dm/notifications', methods=['GET'])
def get_dm_notifications(session_id):
    """Get unread notifications for the DM"""
    dm_user_id = request.args.get('user_id')
    if not dm_user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    # Verify the user is the GM for this session
    session = Session.query.filter_by(id=session_id).first()
    if not session or session.gm_user_id != dm_user_id:
        return jsonify({'error': 'Only GMs can view notifications'}), 403
    
    notifications = DmNotification.query.filter_by(
        session_id=session_id, 
        dm_user_id=dm_user_id,
        is_read=False
    ).order_by(DmNotification.created_at.desc()).all()
    
    return jsonify([{
        'id': n.id,
        'pending_response_id': n.pending_response_id,
        'notification_type': n.notification_type,
        'message': n.message,
        'created_at': n.created_at.isoformat() if n.created_at else None
    } for n in notifications])

@app.route('/api/session/<session_id>/dm/notifications/<int:notification_id>/mark-read', methods=['POST'])
def mark_notification_read(session_id, notification_id):
    """Mark a notification as read"""
    data = request.json
    dm_user_id = data.get('user_id')
    
    if not dm_user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    notification = DmNotification.query.filter_by(
        id=notification_id,
        session_id=session_id,
        dm_user_id=dm_user_id
    ).first()
    
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'status': 'success'})

@app.route('/api/session/<session_id>/player/<user_id>/approved-responses', methods=['GET'])
def get_approved_responses(session_id, user_id):
    """Get approved responses for a specific player"""
    responses = PendingResponse.query.filter_by(
        session_id=session_id,
        user_id=user_id,
        status='approved'
    ).order_by(PendingResponse.reviewed_at.desc()).all()
    
    return jsonify([{
        'id': r.id,
        'context': r.context,
        'final_response': r.final_response,
        'response_type': r.response_type,
        'dm_notes': r.dm_notes,
        'reviewed_at': r.reviewed_at.isoformat() if r.reviewed_at else None
    } for r in responses])

@app.route('/api/session/<session_id>/llm-with-review', methods=['POST'])
def llm_with_review(session_id):
    """
    Enhanced LLM endpoint that supports DM review workflow
    """
    data = request.json
    user_id = data.get('user_id')
    context = data.get('context', data.get('input', ''))
    response_type = data.get('response_type', 'narrative')
    priority = data.get('priority', 1)
    require_review = data.get('require_review', True)
    model = data.get('model', 'openai')
    
    if not user_id or not context:
        return jsonify({'error': 'user_id and context are required'}), 400
    
    # Validate session and user
    session = Session.query.filter_by(id=session_id).first()
    if not session:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    user_role = UserRole.query.filter_by(session_id=session_id, user_id=user_id).first()
    if not user_role:
        return jsonify({'error': 'User not in session'}), 403
    
    try:
        result = asyncio.run(call_llm_with_review(
            session_id=session_id,
            user_id=user_id,
            context=context,
            model=model,
            response_type=response_type,
            priority=priority,
            require_review=require_review
        ))
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pending-response/<response_id>/status', methods=['GET'])
def check_pending_response_status(response_id):
    """
    Check the status of a pending response
    """
    try:
        result = asyncio.run(get_reviewed_response(response_id))
        if result is None:
            return jsonify({'error': 'Pending response not found'}), 404
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ping')
def ping():
    return jsonify({'status': 'ok', 'message': 'Shadowrun backend is alive.'})

@app.route('/api/session', methods=['POST'])
def create_session():
    data = request.json
    name = data.get('name')
    gm_user_id = data.get('gm_user_id')
    if not name or not gm_user_id:
        return jsonify({'error': 'Missing required fields'}), 400
    session = Session(name=name, gm_user_id=gm_user_id)
    db.session.add(session)
    db.session.commit()
    return jsonify({'session_id': session.id, 'name': session.name, 'gm_user_id': session.gm_user_id})

@app.route('/api/session/<session_id>/join', methods=['POST'])
def join_session(session_id):
    data = request.json
    user_id = data.get('user_id')
    role = data.get('role', 'player')
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400
    user_role = UserRole(session_id=session_id, user_id=user_id, role=role)
    db.session.add(user_role)
    db.session.commit()
    return jsonify({'session_id': session_id, 'user_id': user_id, 'role': role})

@app.route('/api/session/<session_id>/users', methods=['GET'])
def get_session_users(session_id):
    users = UserRole.query.filter_by(session_id=session_id).all()
    return jsonify([
        {'user_id': u.user_id, 'role': u.role}
        for u in users
    ])

# --- Image Generation Endpoints ---
@app.route('/api/session/<session_id>/generate-image', methods=['POST'])
def generate_image_endpoint(session_id):
    """Request image generation for a scene or description"""
    try:
        data = request.json
        user_id = data.get('user_id')
        prompt = data.get('prompt')
        request_type = data.get('type', 'scene')  # 'scene', 'character', 'location', 'item'
        priority = data.get('priority', 1)
        style_preferences = data.get('style_preferences', {})
        
        if not user_id or not prompt:
            return jsonify({'error': 'Missing required fields: user_id, prompt'}), 400
        
        # Validate session and user
        session = Session.query.filter_by(id=session_id).first()
        if not session:
            return jsonify({'error': 'Invalid session_id'}), 400
        
        user_role = UserRole.query.filter_by(session_id=session_id, user_id=user_id).first()
        if not user_role:
            return jsonify({'error': 'User not in session'}), 403
        
        # Create image generation request
        img_request = ImageGeneration(
            session_id=session_id,
            user_id=user_id,
            request_type=request_type,
            context=prompt,
            style_preferences=json.dumps(style_preferences),
            priority=priority
        )
        
        db.session.add(img_request)
        db.session.commit()
        request_id = img_request.id
        
        return jsonify({
            'status': 'success',
            'request_id': request_id,
            'message': 'Image generation request queued'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>/generate-image-instant', methods=['POST'])
def generate_image_instant(session_id):
    """Generate image immediately (synchronous)"""
    try:
        data = request.json
        user_id = data.get('user_id')
        prompt = data.get('prompt')
        provider = data.get('provider', 'dalle')
        style_preferences = data.get('style_preferences', {})
        
        if not user_id or not prompt:
            return jsonify({'error': 'Missing required fields: user_id, prompt'}), 400
        
        # Validate session and user
        session = Session.query.filter_by(id=session_id).first()
        if not session:
            return jsonify({'error': 'Invalid session_id'}), 400
        
        user_role = UserRole.query.filter_by(session_id=session_id, user_id=user_id).first()
        if not user_role:
            return jsonify({'error': 'User not in session'}), 403
        
        # Generate image directly
        from image_gen_utils import ImageGenerator
        generator = ImageGenerator()
        
        result = asyncio.run(generator.generate_image(
            prompt=prompt,
            provider=provider,
            context=f"Session: {session_id}",
            **style_preferences
        ))
        
        # Save result to database
        generated_image = GeneratedImage(
            session_id=session_id,
            user_id=user_id,
            prompt=prompt,
            enhanced_prompt=result.get("revised_prompt", prompt),
            image_url=result["image_url"],
            provider=result["provider"],
            status="completed",
            generation_time=result["generation_time"],
            completed_at=datetime.utcnow()
        )
        
        db.session.add(generated_image)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'image_id': generated_image.id,
            'image_url': result["image_url"],
            'generation_time': result["generation_time"],
            'provider': result["provider"]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>/images', methods=['GET'])
def get_session_images_endpoint(session_id):
    """Get generated images for a session"""
    try:
        user_id = request.args.get('user_id')
        limit = int(request.args.get('limit', 20))
        
        # Validate session
        session = Session.query.filter_by(id=session_id).first()
        if not session:
            return jsonify({'error': 'Invalid session_id'}), 400
        
        # Get images directly from database
        query = GeneratedImage.query.filter_by(session_id=session_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        images_db = query.order_by(GeneratedImage.created_at.desc()).limit(limit).all()
        
        images = [
            {
                "id": img.id,
                "prompt": img.prompt,
                "image_url": img.image_url,
                "provider": img.provider,
                "status": img.status,
                "created_at": img.created_at.isoformat(),
                "is_favorite": img.is_favorite,
                "tags": json.loads(img.tags) if img.tags else []
            }
            for img in images_db
        ]
        
        return jsonify({
            'status': 'success',
            'images': images,
            'count': len(images)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>/image/<image_id>', methods=['GET'])
def get_image_details(session_id, image_id):
    """Get details of a specific generated image"""
    try:
        image = GeneratedImage.query.filter_by(id=image_id, session_id=session_id).first()
        if not image:
            return jsonify({'error': 'Image not found'}), 404
        
        return jsonify({
            'status': 'success',
            'image': {
                'id': image.id,
                'prompt': image.prompt,
                'enhanced_prompt': image.enhanced_prompt,
                'image_url': image.image_url,
                'provider': image.provider,
                'status': image.status,
                'generation_time': image.generation_time,
                'created_at': image.created_at.isoformat(),
                'is_favorite': image.is_favorite,
                'tags': json.loads(image.tags) if image.tags else []
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>/image/<image_id>/favorite', methods=['POST'])
def toggle_image_favorite(session_id, image_id):
    """Toggle favorite status of an image"""
    try:
        data = request.json
        user_id = data.get('user_id')
        is_favorite = data.get('is_favorite', True)
        
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        image = GeneratedImage.query.filter_by(id=image_id, session_id=session_id).first()
        if not image:
            return jsonify({'error': 'Image not found'}), 404
        
        # Check if user has permission to modify this image
        if image.user_id != user_id:
            user_role = UserRole.query.filter_by(session_id=session_id, user_id=user_id).first()
            if not user_role or user_role.role != 'gm':
                return jsonify({'error': 'Permission denied'}), 403
        
        image.is_favorite = is_favorite
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'image_id': image_id,
            'is_favorite': is_favorite
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>/image-providers', methods=['GET'])
def get_available_providers(session_id):
    """Get list of available image generation providers"""
    try:
        from image_gen_utils import ImageGenerator
        generator = ImageGenerator()
        providers = generator.get_available_providers()
        
        return jsonify({
            'status': 'success',
            'providers': providers,
            'default': 'dalle' if 'dalle' in providers else providers[0] if providers else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Imports moved to top of file

# --- Command Routing with Model Selection ---
@app.route('/api/command', methods=['POST'])
def route_command():
    data = request.json
    command = data.get('command')
    session_id = data.get('session_id')
    user_id = data.get('user_id')
    model = data.get('model', 'openai')
    model_name = data.get('model_name')  # For OpenRouter, e.g., 'openai/gpt-4o', 'mistralai/mistral-large', etc.
    messages = [
        {"role": "user", "content": command}
    ]
    try:
        llm_response = asyncio.run(call_llm(model, messages, model_name=model_name))
        return jsonify({
            'status': 'success',
            'command': command,
            'session_id': session_id,
            'user_id': user_id,
            'model': model,
            'model_name': model_name,
            'llm_response': llm_response
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# --- LLM Streaming Endpoint ---
@app.route('/api/llm', methods=['POST'])
def llm_stream():
    data = request.json
    session_id = data.get('session_id')
    user_id = data.get('user_id')
    user_input = data.get('input')
    model = data.get('model', 'openai')
    model_name = data.get('model_name')
    stream = True

    # Validate session and user
    session = Session.query.filter_by(id=session_id).first()
    if not session:
        return jsonify({'status': 'error', 'error': 'Invalid session_id'}), 400
    user_role = UserRole.query.filter_by(session_id=session_id, user_id=user_id).first()
    if not user_role:
        return jsonify({'status': 'error', 'error': 'User not in session'}), 403

    # Prepare messages for LLM
    messages = [
        {"role": "user", "content": user_input}
    ]

    async def llm_async_gen():
        try:
            agen = await call_llm(model, messages, stream=True, model_name=model_name)
            async for chunk in agen:
                # Tag output with speaker
                yield f'data: {{"speaker": "AI", "content": {repr(chunk)} }}\n\n'
        except httpx.HTTPStatusError as e:
            error_msg = f"Upstream API error: {e.response.status_code} {e.response.text}"
            print(error_msg)
            yield f'data: {{"error": "Upstream API error", "type": "http", "details": {repr(error_msg)} }}\n\n'
        except httpx.RequestError as e:
            error_msg = f"Network error: {str(e)}"
            print(error_msg)
            yield f'data: {{"error": "Network error", "type": "network", "details": {repr(error_msg)} }}\n\n'
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Internal error: {str(e)}\n{tb}")
            yield f'data: {{"error": "Internal server error", "type": "internal", "details": {repr(str(e))}, "trace": {repr(tb)} }}\n\n'

    def generate():
        agen = llm_async_gen()
        while True:
            try:
                chunk = asyncio.run(agen.__anext__())
                yield chunk
            except StopAsyncIteration:
                break

    headers = {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache'}
    return Response(generate(), headers=headers)

# Imports moved to top of file

@app.route("/api/chat", methods=["POST"])
def chat():
    # Accepts: {input, session_id, user_id, role}
    data = request.json
    user_input = data.get("input", "").strip()
    session_id = data.get("session_id")
    user_id = data.get("user_id")
    role = data.get("role", "player")
    if not user_input:
        return jsonify({"response": "No input provided."}), 400

    # Fetch or initialize chat memory for this session/user/role
    memory = ChatMemory.query.filter_by(session_id=session_id, user_id=user_id, role=role).first()
    if memory is None:
        # Start with a system prompt
        messages = [{"role": "system", "content": "You are an expert Shadowrun GM AI. Answer as a helpful, creative, and rules-savvy Shadowrun game master. Respond in character where appropriate."}]
        memory = ChatMemory(session_id=session_id, user_id=user_id, role=role, messages=json.dumps(messages))
        db.session.add(memory)
        db.session.commit()
    else:
        messages = json.loads(memory.messages)

    # Append the new user message
    messages.append({"role": "user", "content": user_input})

    # Imports available at top of file

    def event_stream():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def stream():
            async for chunk in call_openai_stream(messages):
                yield chunk
        content = ""
        try:
            for chunk in loop.run_until_complete(stream()):
                content += chunk
                yield f"data: {chunk}\n\n"
        finally:
            loop.close()
        # Save the AI message to memory after streaming
        messages.append({"role": "assistant", "content": content})
        memory.messages = json.dumps(messages)
        db.session.commit()

    headers = {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache'}
    return Response(stream_with_context(event_stream()), headers=headers)

@app.route("/")
def index():
    return "<h2>Shadowrun Multiplayer Engine API is running!<br>Welcome, runner. For docs and endpoints, see /api.</h2>", 200

from stream_proxy import stream_proxy
app.register_blueprint(stream_proxy)

# --- Slack Integration Endpoints ---
@app.route('/api/slack/command', methods=['POST'])
def handle_slack_command():
    """Handle Slack slash commands"""
    try:
        # Verify the request came from Slack
        if not slack_bot.verify_slack_request(request.headers, request.get_data(as_text=True)):
            return jsonify({'error': 'Invalid request signature'}), 401
        
        # Parse form data from Slack
        command_data = {
            'command': request.form.get('command'),
            'text': request.form.get('text', ''),
            'user_id': request.form.get('user_id'),
            'channel_id': request.form.get('channel_id'),
            'team_id': request.form.get('team_id'),
            'user_name': request.form.get('user_name'),
            'channel_name': request.form.get('channel_name'),
            'team_domain': request.form.get('team_domain'),
            'response_url': request.form.get('response_url')
        }
        
        # Process the command
        response = asyncio.run(slack_processor.process_command(command_data))
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Slack command error: {e}")
        return jsonify({
            'response_type': 'ephemeral',
            'text': f'Error processing command: {str(e)}'
        }), 500

@app.route('/api/slack/events', methods=['POST'])
def handle_slack_events():
    """Handle Slack events (URL verification, app mentions, etc.)"""
    try:
        # Verify the request came from Slack
        if not slack_bot.verify_slack_request(request.headers, request.get_data(as_text=True)):
            return jsonify({'error': 'Invalid request signature'}), 401
        
        event_data = request.json
        
        # Handle URL verification challenge
        if event_data.get('type') == 'url_verification':
            return jsonify({'challenge': event_data.get('challenge')})
        
        # Handle other events
        if event_data.get('type') == 'event_callback':
            event = event_data.get('event', {})
            
            # Handle app mentions
            if event.get('type') == 'app_mention':
                asyncio.run(handle_app_mention(event))
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        print(f"Slack events error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/slack/interactive', methods=['POST'])
def handle_slack_interactive():
    """Handle Slack interactive components (buttons, modals, etc.)"""
    try:
        # Verify the request came from Slack
        if not slack_bot.verify_slack_request(request.headers, request.get_data(as_text=True)):
            return jsonify({'error': 'Invalid request signature'}), 401
        
        payload = json.loads(request.form.get('payload', '{}'))
        
        # Handle button clicks
        if payload.get('type') == 'block_actions':
            actions = payload.get('actions', [])
            for action in actions:
                if action.get('action_id') == 'dm_dashboard_button':
                    # Open DM dashboard
                    channel_id = payload['channel']['id']
                    team_id = payload['team']['id']
                    
                    dashboard_url = f"http://localhost:3000/console?dm=true&session={team_id}_{channel_id}"
                    
                    return jsonify({
                        'response_type': 'ephemeral',
                        'text': f'Opening DM Dashboard: {dashboard_url}'
                    })
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        print(f"Slack interactive error: {e}")
        return jsonify({'error': str(e)}), 500

# --- Slack Helper Functions ---
async def create_session_for_slack(name: str, gm_user_id: str, slack_channel_id: str, slack_team_id: str) -> Dict:
    """Create a game session for Slack channel"""
    # Create regular session
    session = Session(name=name, gm_user_id=gm_user_id)
    db.session.add(session)
    db.session.flush()  # Get the ID
    
    # Create Slack mapping
    slack_session = SlackSession(
        slack_team_id=slack_team_id,
        slack_channel_id=slack_channel_id,
        session_id=session.id
    )
    db.session.add(slack_session)
    
    # Add GM to session
    gm_role = UserRole(session_id=session.id, user_id=gm_user_id, role='gm')
    db.session.add(gm_role)
    
    db.session.commit()
    
    return {
        'session_id': session.id,
        'name': session.name,
        'gm_user_id': session.gm_user_id
    }

async def get_slack_session_info(slack_session_id: str) -> Optional[Dict]:
    """Get session info for a Slack channel"""
    team_id, channel_id = slack_session_id.split('_', 1)
    
    slack_session = SlackSession.query.filter_by(
        slack_team_id=team_id,
        slack_channel_id=channel_id
    ).first()
    
    if not slack_session:
        return None
    
    session = Session.query.get(slack_session.session_id)
    if not session:
        return None
    
    # Get players
    players = UserRole.query.filter_by(session_id=session.id).all()
    
    return {
        'session_id': session.id,
        'name': session.name,
        'gm_user_id': session.gm_user_id,
        'players': [{'user_id': p.user_id, 'role': p.role} for p in players],
        'created_at': session.created_at.isoformat()
    }

async def process_slack_ai_request(session_id: str, user_id: str, message: str, channel_id: str):
    """Process AI request from Slack and notify when reviewed"""
    try:
        # Get actual session ID from Slack session
        team_id, slack_channel_id = session_id.split('_', 1)
        slack_session = SlackSession.query.filter_by(
            slack_team_id=team_id,
            slack_channel_id=slack_channel_id
        ).first()
        
        if not slack_session:
            await slack_bot.send_message(
                channel=channel_id,
                text="Error: No active session in this channel. Use `/sr-session create` first.",
                ephemeral_user=user_id
            )
            return
        
        actual_session_id = slack_session.session_id
        
        # Create pending response using DM review system
        from llm_utils import create_pending_response
        response_id = create_pending_response(
            session_id=actual_session_id,
            user_id=user_id,
            context=message,
            response_type='slack_ai',
            priority=2
        )
        
        # Notify in Slack
        await slack_bot.send_message(
            channel=channel_id,
            blocks=slack_bot.format_shadowrun_response(
                f"AI request submitted for DM review.\nRequest ID: {response_id[:8]}...\n" \
                f"You'll be notified when the DM approves the response.",
                "success"
            )
        )
        
    except Exception as e:
        print(f"Error processing Slack AI request: {e}")
        await slack_bot.send_message(
            channel=channel_id,
            text=f"Error processing AI request: {str(e)}",
            ephemeral_user=user_id
        )

async def process_slack_image_request(session_id: str, user_id: str, description: str, channel_id: str):
    """Process image generation request from Slack"""
    try:
        # Get actual session ID from Slack session
        team_id, slack_channel_id = session_id.split('_', 1)
        slack_session = SlackSession.query.filter_by(
            slack_team_id=team_id,
            slack_channel_id=slack_channel_id
        ).first()
        
        if not slack_session:
            await slack_bot.send_message(
                channel=channel_id,
                text="Error: No active session in this channel. Use `/sr-session create` first.",
                ephemeral_user=user_id
            )
            return
        
        actual_session_id = slack_session.session_id
        
        # Generate image directly
        from image_gen_utils import ImageGenerator
        generator = ImageGenerator()
        
        result = await generator.generate_image(
            prompt=description,
            provider="dalle",  # Default to DALL-E
            context=f"Slack Session: {actual_session_id}"
        )
        
        # Save to database
        generated_image = GeneratedImage(
            session_id=actual_session_id,
            user_id=user_id,
            prompt=description,
            enhanced_prompt=result.get("revised_prompt", description),
            image_url=result["image_url"],
            provider=result["provider"],
            status="completed",
            generation_time=result["generation_time"],
            completed_at=datetime.utcnow()
        )
        
        db.session.add(generated_image)
        db.session.commit()
        
        # Share image in Slack
        await slack_bot.upload_image(
            channel=channel_id,
            image_url=result["image_url"],
            title=f"Generated Scene: {description[:50]}...",
            comment=f"Generated by <@{user_id}> using {result['provider'].upper()}\n" \
                   f"Generation time: {result['generation_time']:.1f}s"
        )
        
    except Exception as e:
        print(f"Error processing Slack image request: {e}")
        await slack_bot.send_message(
            channel=channel_id,
            blocks=slack_bot.format_shadowrun_response(
                f"Image generation failed: {str(e)}",
                "error"
            )
        )

async def handle_app_mention(event: Dict):
    """Handle when the bot is mentioned in Slack"""
    try:
        channel = event.get('channel')
        user = event.get('user')
        text = event.get('text', '')
        
        # Extract command from mention
        # Remove bot mention and process as help
        await slack_bot.send_message(
            channel=channel,
            blocks=slack_bot.format_shadowrun_response(
                "Hello! I'm your Shadowrun assistant.\n" \
                "Use `/sr-help` to see available commands.",
                "general"
            )
        )
        
    except Exception as e:
        print(f"Error handling app mention: {e}")

async def notify_slack_on_dm_review(session_id: str, response_id: str, action: str, final_response: str):
    """Notify Slack channel when DM reviews a response"""
    try:
        # Find Slack channel for this session
        slack_session = SlackSession.query.filter_by(session_id=session_id).first()
        if not slack_session:
            return
        
        # Get the pending response to find the original user
        pending_response = PendingResponse.query.get(response_id)
        if not pending_response:
            return
        
        if action == 'approved':
            message = f"✅ *AI Response Approved*\n" \
                     f"For: <@{pending_response.user_id}>\n" \
                     f"Response: {final_response}"
            
            await slack_bot.send_message(
                channel=slack_session.slack_channel_id,
                blocks=slack_bot.format_shadowrun_response(message, "success")
            )
        
        elif action == 'rejected':
            await slack_bot.send_message(
                channel=slack_session.slack_channel_id,
                text=f"❌ AI response for <@{pending_response.user_id}> was rejected by the DM.",
                ephemeral_user=pending_response.user_id
            )
        
        elif action == 'edited':
            message = f"✏️ *AI Response (Edited by DM)*\n" \
                     f"For: <@{pending_response.user_id}>\n" \
                     f"Response: {final_response}"
            
            await slack_bot.send_message(
                channel=slack_session.slack_channel_id,
                blocks=slack_bot.format_shadowrun_response(message, "success")
            )
        
    except Exception as e:
        print(f"Error notifying Slack on DM review: {e}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
