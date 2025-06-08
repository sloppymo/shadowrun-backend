from flask import Blueprint, request, jsonify
from sqlalchemy import and_
from datetime import datetime
import json
import uuid
import random

# Import database models from app.py
from app import db, Session, UserRole, MatrixGrid, MatrixNode, MatrixPersona, MatrixAction, IceProgram

# Create matrix blueprint
matrix_bp = Blueprint('matrix', __name__)

# Routes
@matrix_bp.route('/api/session/<session_id>/matrix/grids', methods=['GET'])
def get_matrix_grids(session_id):
    """Get available matrix grids for a session"""
    grids = MatrixGrid.query.filter_by(session_id=session_id).all()
    
    return jsonify([{
        'id': g.id,
        'name': g.name,
        'grid_type': g.grid_type,
        'security_rating': g.security_rating,
        'noise_level': g.noise_level
    } for g in grids])

@matrix_bp.route('/api/session/<session_id>/matrix/grid/create', methods=['POST'])
def create_matrix_grid(session_id):
    """Create a new matrix grid"""
    data = request.json
    user_id = data.get('user_id')
    
    # Verify GM permissions
    session = Session.query.filter_by(id=session_id).first()
    if not session or session.gm_user_id != user_id:
        return jsonify({'error': 'Only GMs can create matrix grids'}), 403
    
    grid = MatrixGrid(
        session_id=session_id,
        name=data.get('name', 'Matrix Grid'),
        grid_type=data.get('grid_type', 'public'),
        security_rating=data.get('security_rating', 3),
        noise_level=data.get('noise_level', 0)
    )
    db.session.add(grid)
    
    # Generate initial nodes
    if data.get('generate_nodes', True):
        generate_grid_nodes(grid.id)
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'grid_id': grid.id
    })

def generate_grid_nodes(grid_id):
    """Generate procedural matrix nodes for a grid"""
    # Create main host
    main_host = MatrixNode(
        grid_id=grid_id,
        name='Corporate Host',
        node_type='host',
        security=8,
        encrypted=True,
        position_x=0,
        position_y=0,
        position_z=0,
        discovered=True,
        connected_nodes=json.dumps(['node-1', 'node-2', 'ice-1'])
    )
    db.session.add(main_host)
    
    # Create subsystems
    nodes = [
        {
            'name': 'Security Subsystem',
            'node_type': 'device',
            'security': 6,
            'position': (-2, 1, 0),
            'connected': ['data-1']
        },
        {
            'name': 'Personnel Database',
            'node_type': 'file',
            'security': 5,
            'encrypted': True,
            'position': (2, 1, 0),
            'connected': ['data-2']
        },
        {
            'name': 'Camera Controls',
            'node_type': 'data',
            'security': 4,
            'position': (-3, 2, 0),
            'data': {'type': 'device_control', 'device': 'security_cameras'}
        },
        {
            'name': 'Paydata Cache',
            'node_type': 'data',
            'security': 7,
            'encrypted': True,
            'position': (3, 2, 0),
            'data': {'type': 'paydata', 'value': 5000}
        }
    ]
    
    for node_data in nodes:
        node = MatrixNode(
            grid_id=grid_id,
            name=node_data['name'],
            node_type=node_data['node_type'],
            security=node_data['security'],
            encrypted=node_data.get('encrypted', False),
            position_x=node_data['position'][0],
            position_y=node_data['position'][1],
            position_z=node_data['position'][2],
            discovered=False,
            connected_nodes=json.dumps(node_data.get('connected', [])),
            data_payload=json.dumps(node_data.get('data')) if 'data' in node_data else None
        )
        db.session.add(node)
    
    # Create ICE
    ice_node = MatrixNode(
        grid_id=grid_id,
        name='Patrol IC',
        node_type='ice',
        security=6,
        position_x=0,
        position_y=-1,
        position_z=0,
        discovered=True
    )
    db.session.add(ice_node)
    
    ice_program = IceProgram(
        grid_id=grid_id,
        node_id=ice_node.id,
        name='Patrol IC',
        ice_type='patrol',
        rating=6,
        position_x=0,
        position_y=-1,
        position_z=0
    )
    db.session.add(ice_program)

@matrix_bp.route('/api/session/<session_id>/matrix/grid/<grid_id>/nodes', methods=['GET'])
def get_grid_nodes(session_id, grid_id):
    """Get nodes in a matrix grid"""
    persona_id = request.args.get('persona_id')
    
    # Get all nodes
    nodes = MatrixNode.query.filter_by(grid_id=grid_id).all()
    
    # Filter by discovered status if persona specified
    if persona_id:
        # In real implementation, would check persona's discovered nodes
        nodes = [n for n in nodes if n.discovered]
    
    return jsonify([{
        'id': n.id,
        'name': n.name,
        'type': n.node_type,
        'security': n.security,
        'encrypted': n.encrypted,
        'position': {'x': n.position_x, 'y': n.position_y, 'z': n.position_z},
        'discovered': n.discovered,
        'compromised': n.compromised,
        'connected': json.loads(n.connected_nodes) if n.connected_nodes else [],
        'data': json.loads(n.data_payload) if n.data_payload else None
    } for n in nodes])

@matrix_bp.route('/api/session/<session_id>/matrix/persona/create', methods=['POST'])
def create_matrix_persona(session_id):
    """Create or update a matrix persona"""
    data = request.json
    
    persona = MatrixPersona.query.filter_by(
        character_id=data.get('character_id'),
        user_id=data.get('user_id')
    ).first()
    
    if not persona:
        persona = MatrixPersona(
            character_id=data.get('character_id'),
            user_id=data.get('user_id')
        )
        db.session.add(persona)
    
    # Update stats
    persona.attack = data.get('attack', 4)
    persona.sleaze = data.get('sleaze', 5)
    persona.data_processing = data.get('data_processing', 6)
    persona.firewall = data.get('firewall', 4)
    persona.grid_id = data.get('grid_id')
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'persona_id': persona.id
    })

@matrix_bp.route('/api/session/<session_id>/matrix/action', methods=['POST'])
def perform_matrix_action(session_id):
    """Perform a matrix action"""
    data = request.json
    persona_id = data.get('persona_id')
    action_type = data.get('action_type')
    target_node_id = data.get('target_node_id')
    
    # Get persona
    persona = MatrixPersona.query.get(persona_id)
    if not persona:
        return jsonify({'error': 'Persona not found'}), 404
    
    # Get target node
    target_node = MatrixNode.query.get(target_node_id) if target_node_id else None
    
    # Simulate action resolution
    difficulty = target_node.security if target_node else 3
    roll = random.randint(1, 6) + random.randint(1, 6)
    
    # Determine attribute to use
    if action_type == 'hack':
        attribute = persona.sleaze if not target_node.compromised else persona.attack
    elif action_type == 'search':
        attribute = persona.data_processing
    elif action_type == 'crash':
        attribute = persona.attack
    else:
        attribute = persona.sleaze
    
    success = (roll + attribute) >= difficulty
    overwatch = 0
    
    if success:
        if action_type == 'hack' and target_node:
            target_node.compromised = True
            # Discover connected nodes
            connected_ids = json.loads(target_node.connected_nodes) if target_node.connected_nodes else []
            for node_id in connected_ids:
                connected_node = MatrixNode.query.filter_by(id=node_id, grid_id=target_node.grid_id).first()
                if connected_node:
                    connected_node.discovered = True
        
        elif action_type == 'search' and target_node:
            # Reveal hidden nodes connected to target
            connected_ids = json.loads(target_node.connected_nodes) if target_node.connected_nodes else []
            for node_id in connected_ids:
                connected_node = MatrixNode.query.filter_by(id=node_id, grid_id=target_node.grid_id).first()
                if connected_node:
                    connected_node.discovered = True
        
        elif action_type == 'crash' and target_node and target_node.node_type == 'ice':
            # Crash ICE
            ice = IceProgram.query.filter_by(node_id=target_node_id).first()
            if ice:
                ice.status = 'crashed'
    else:
        # Failed action generates overwatch
        overwatch = difficulty
        persona.overwatch_score = min(40, persona.overwatch_score + overwatch)
    
    # Record action
    action = MatrixAction(
        session_id=session_id,
        persona_id=persona_id,
        action_type=action_type,
        target_node_id=target_node_id,
        success=success,
        rolls=json.dumps({'roll': roll, 'attribute': attribute, 'difficulty': difficulty}),
        overwatch_generated=overwatch
    )
    db.session.add(action)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'success': success,
        'roll': roll,
        'attribute': attribute,
        'difficulty': difficulty,
        'overwatch_generated': overwatch,
        'current_overwatch': persona.overwatch_score
    })

@matrix_bp.route('/api/session/<session_id>/matrix/perception', methods=['POST'])
def matrix_perception(session_id):
    """Perform matrix perception check"""
    data = request.json
    persona_id = data.get('persona_id')
    grid_id = data.get('grid_id')
    
    # Get persona
    persona = MatrixPersona.query.get(persona_id)
    if not persona:
        return jsonify({'error': 'Persona not found'}), 404
    
    # Roll perception
    perception_roll = random.randint(1, 6) + random.randint(1, 6) + persona.data_processing
    
    # Find undiscovered nodes
    undiscovered_nodes = MatrixNode.query.filter_by(
        grid_id=grid_id,
        discovered=False
    ).all()
    
    discovered_count = 0
    for node in undiscovered_nodes:
        if perception_roll > node.security:
            node.discovered = True
            discovered_count += 1
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'perception_roll': perception_roll,
        'discovered_count': discovered_count
    })

@matrix_bp.route('/api/session/<session_id>/matrix/ice/<ice_id>/behavior', methods=['GET'])
def get_ice_behavior(session_id, ice_id):
    """Get ICE behavior/movement update"""
    ice = IceProgram.query.get(ice_id)
    if not ice or ice.status != 'active':
        return jsonify({'status': 'inactive'})
    
    # Simple patrol movement
    ice.position_x += (random.random() - 0.5) * 0.5
    ice.position_y += (random.random() - 0.5) * 0.5
    ice.last_action = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'status': 'active',
        'position': {
            'x': ice.position_x,
            'y': ice.position_y,
            'z': ice.position_z
        }
    }) 