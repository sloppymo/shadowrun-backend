from flask import Blueprint, request, jsonify
from sqlalchemy import and_
from datetime import datetime
import json
import uuid

# Import database models from app.py
from app import db, Session, UserRole, Combat, Combatant, CombatAction

# Create combat blueprint
combat_bp = Blueprint('combat', __name__)

# Routes
@combat_bp.route('/api/session/<session_id>/combat/create', methods=['POST'])
def create_combat(session_id):
    """Create a new combat encounter"""
    data = request.json
    user_id = data.get('user_id')
    name = data.get('name', 'Combat Encounter')
    
    # Verify GM permissions
    session = Session.query.filter_by(id=session_id).first()
    if not session or session.gm_user_id != user_id:
        return jsonify({'error': 'Only GMs can create combat encounters'}), 403
    
    # Create combat
    combat = Combat(
        session_id=session_id,
        name=name,
        status='setup'
    )
    db.session.add(combat)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'combat_id': combat.id,
        'name': combat.name
    })

@combat_bp.route('/api/session/<session_id>/combat/<combat_id>/combatants', methods=['GET'])
def get_combatants(session_id, combat_id):
    """Get all combatants in a combat"""
    combatants = Combatant.query.filter_by(combat_id=combat_id).all()
    
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'type': c.type,
        'initiative': c.initiative,
        'initiative_score': c.initiative_score,
        'actions': c.actions,
        'reaction': c.reaction,
        'intuition': c.intuition,
        'edge': c.edge,
        'current_edge': c.current_edge,
        'physical_damage': c.physical_damage,
        'stun_damage': c.stun_damage,
        'condition_monitor': {
            'physical': c.physical_monitor,
            'stun': c.stun_monitor
        },
        'status': c.status,
        'tags': json.loads(c.tags) if c.tags else [],
        'position': json.loads(c.position) if c.position else None
    } for c in combatants])

@combat_bp.route('/api/session/<session_id>/combat/<combat_id>/combatant', methods=['POST'])
def add_combatant(session_id, combat_id):
    """Add a combatant to combat"""
    data = request.json
    user_id = data.get('user_id')
    
    # Verify GM permissions
    session = Session.query.filter_by(id=session_id).first()
    if not session or session.gm_user_id != user_id:
        return jsonify({'error': 'Only GMs can add combatants'}), 403
    
    # Create combatant
    combatant = Combatant(
        combat_id=combat_id,
        name=data.get('name'),
        type=data.get('type', 'npc'),
        initiative=data.get('initiative', 10),
        reaction=data.get('reaction', 5),
        intuition=data.get('intuition', 3),
        edge=data.get('edge', 2),
        current_edge=data.get('current_edge', 2),
        physical_monitor=data.get('physical_monitor', 10),
        stun_monitor=data.get('stun_monitor', 10),
        tags=json.dumps(data.get('tags', [])),
        position=json.dumps(data.get('position')) if data.get('position') else None
    )
    db.session.add(combatant)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'combatant_id': combatant.id
    })

@combat_bp.route('/api/session/<session_id>/combat/<combat_id>/roll-initiative', methods=['POST'])
def roll_initiative(session_id, combat_id):
    """Roll initiative for all combatants"""
    import random
    
    data = request.json
    user_id = data.get('user_id')
    
    # Verify GM permissions
    session = Session.query.filter_by(id=session_id).first()
    if not session or session.gm_user_id != user_id:
        return jsonify({'error': 'Only GMs can roll initiative'}), 403
    
    # Get all combatants
    combatants = Combatant.query.filter_by(combat_id=combat_id).all()
    
    # Roll initiative for each
    for combatant in combatants:
        roll = random.randint(1, 6)
        combatant.initiative_score = combatant.initiative + combatant.intuition + roll
    
    # Update combat status
    combat = Combat.query.get(combat_id)
    if combat:
        combat.status = 'active'
        combat.current_round = 1
        combat.active_combatant_index = 0
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Initiative rolled for all combatants'
    })

@combat_bp.route('/api/session/<session_id>/combat/<combat_id>/damage', methods=['POST'])
def apply_damage(session_id, combat_id):
    """Apply damage to a combatant"""
    data = request.json
    user_id = data.get('user_id')
    combatant_id = data.get('combatant_id')
    physical_damage = data.get('physical_damage', 0)
    stun_damage = data.get('stun_damage', 0)
    
    # Verify GM permissions
    session = Session.query.filter_by(id=session_id).first()
    if not session or session.gm_user_id != user_id:
        return jsonify({'error': 'Only GMs can apply damage'}), 403
    
    # Get combatant
    combatant = Combatant.query.get(combatant_id)
    if not combatant:
        return jsonify({'error': 'Combatant not found'}), 404
    
    # Apply damage
    combatant.physical_damage = max(0, min(combatant.physical_damage + physical_damage, combatant.physical_monitor))
    combatant.stun_damage = max(0, min(combatant.stun_damage + stun_damage, combatant.stun_monitor))
    
    # Update status
    if combatant.physical_damage >= combatant.physical_monitor:
        combatant.status = 'dead'
    elif combatant.stun_damage >= combatant.stun_monitor:
        combatant.status = 'unconscious'
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'combatant_status': combatant.status,
        'physical_damage': combatant.physical_damage,
        'stun_damage': combatant.stun_damage
    })

@combat_bp.route('/api/session/<session_id>/combat/<combat_id>/next-turn', methods=['POST'])
def next_turn(session_id, combat_id):
    """Advance to next turn"""
    data = request.json
    user_id = data.get('user_id')
    
    # Verify GM permissions
    session = Session.query.filter_by(id=session_id).first()
    if not session or session.gm_user_id != user_id:
        return jsonify({'error': 'Only GMs can advance turns'}), 403
    
    # Get combat
    combat = Combat.query.get(combat_id)
    if not combat:
        return jsonify({'error': 'Combat not found'}), 404
    
    # Get combatants sorted by initiative
    combatants = Combatant.query.filter_by(combat_id=combat_id).order_by(
        Combatant.initiative_score.desc()
    ).all()
    
    if not combatants:
        return jsonify({'error': 'No combatants in combat'}), 400
    
    # Advance turn
    combat.active_combatant_index += 1
    
    # Check if round is complete
    if combat.active_combatant_index >= len(combatants):
        combat.active_combatant_index = 0
        combat.current_round += 1
        
        # Reduce sustained actions
        for combatant in combatants:
            combatant.actions = max(0, combatant.actions - 1)
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'current_round': combat.current_round,
        'active_combatant_index': combat.active_combatant_index
    })

@combat_bp.route('/api/session/<session_id>/combat/<combat_id>/action', methods=['POST'])
def record_action(session_id, combat_id):
    """Record a combat action"""
    data = request.json
    
    action = CombatAction(
        combat_id=combat_id,
        combatant_id=data.get('combatant_id'),
        round_number=data.get('round_number'),
        action_type=data.get('action_type'),
        description=data.get('description'),
        rolls=json.dumps(data.get('rolls', []))
    )
    
    db.session.add(action)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'action_id': action.id
    }) 