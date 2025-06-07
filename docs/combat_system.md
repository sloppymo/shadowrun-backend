# Shadowrun 6E Combat System

## Core Mechanics

### Initiative System
- **Initiative Score** = Reaction + Intuition + 1D6 per Initiative Die
- **Action Economy**: Major Action, Minor Action, Free Action
- **Edge Actions**: Push the Limit, Second Chance, Seize the Initiative

### Attack Resolution
1. **Declare attack** and target
2. **Calculate attack pool** = Attribute + Skill + Modifiers - Environmental Penalties
3. **Roll attack test** (Threshold typically 0, counting hits)
4. **Defense test** = Reaction + Intuition + Defense Modifiers
5. **Compare hits** - if attacker has more hits, attack is successful
6. **Apply damage** = Base Damage Value + net hits - Armor (after AP)

## API Integration Points

### Combat Initiation
```python
@app.route('/api/session/<session_id>/combat/start', methods=['POST'])
def start_combat(session_id):
    # Create combat tracker in session
    # Roll initiative for all entities
    # Sort and create turn order
    # Return initial combat state
```

### Turn Management
```python
@app.route('/api/session/<session_id>/combat/next_turn', methods=['POST'])
def next_turn(session_id):
    # Advance combat round if all entities have acted
    # Process start-of-turn effects
    # Update current actor
    # Return updated combat state
```

### Attack Resolution
```python
@app.route('/api/session/<session_id>/combat/attack', methods=['POST'])
def resolve_attack(session_id):
    # Parse attack parameters from request
    # Calculate attack pool and roll
    # Calculate defense pool and roll
    # Determine outcome and damage
    # Update entity statuses
    # Return attack results
```

## Extending Combat With New Actions

New combat actions should follow this structure:
```python
def register_combat_action(action_name, action_type, requirements_func, execution_func, cost):
    """
    Register a new combat action
    
    Parameters:
    - action_name: Display name of the action
    - action_type: 'major', 'minor', or 'free'
    - requirements_func: Function that validates if action can be taken
    - execution_func: Function that executes the action
    - cost: Edge cost (0 for standard actions)
    """
    # Implementation details
```

## Environment and Cover Rules

Cover provides defensive advantages:
- **Light cover**: +2 defense dice
- **Medium cover**: +4 defense dice
- **Heavy cover**: +6 defense dice

Environmental conditions affect perception and accuracy:
- **Darkness**: -2 to -6 dice penalty based on severity
- **Smoke/Fog**: -2 to -4 dice penalty based on density
- **Rain/Weather**: -1 to -3 dice penalty based on intensity

## Implementing Special Attacks

Special attacks (called shots, multiple attacks, etc.) should implement the `SpecialAttack` interface:
```python
class SpecialAttack:
    @property
    def name(self):
        """Display name of the special attack"""
        pass
        
    @property
    def requirements(self):
        """List of requirements as {attribute: value} pairs"""
        pass
        
    def get_modifiers(self, attacker, target, weapon):
        """Return dict of modifiers to apply to the attack"""
        pass
        
    def apply_effects(self, attacker, target, damage, net_hits):
        """Apply special effects after damage calculation"""
        pass
```
