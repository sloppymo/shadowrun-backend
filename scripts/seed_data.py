#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Database seeding script for Shadowrun RPG backend
Populates the database with sample data for development and testing
"""

import os
import sys
import json
import random
from datetime import datetime, timedelta

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from app import db, app
    from models import Character, Session, Entity, Scene, ChatMemory
except ImportError as e:
    print(f"Error importing application modules: {e}")
    print("Make sure to run this script from the project root directory.")
    sys.exit(1)

# Sample data definitions
SAMPLE_CHARACTERS = [
    {
        "name": "Nova",
        "metatype": "Elf",
        "role": "Decker",
        "attributes": {
            "body": 3,
            "agility": 5,
            "reaction": 4,
            "strength": 2,
            "willpower": 5,
            "logic": 6,
            "intuition": 5,
            "charisma": 4
        },
        "skills": {
            "hacking": 6,
            "cybercombat": 5,
            "electronic_warfare": 5,
            "computer": 6,
            "software": 4,
            "hardware": 4,
            "perception": 4
        },
        "equipment": [
            {
                "name": "Hermes Chariot",
                "type": "Cyberdeck",
                "rating": 4,
                "data_processing": 5,
                "firewall": 4,
                "attack": 3,
                "sleaze": 6
            },
            {
                "name": "Ares Predator VI",
                "type": "Heavy Pistol",
                "damage": "3P",
                "accuracy": 5
            }
        ],
        "nuyen": 5000,
        "karma": 30
    },
    {
        "name": "Brick",
        "metatype": "Troll",
        "role": "Street Samurai", 
        "attributes": {
            "body": 8,
            "agility": 4,
            "reaction": 5,
            "strength": 7,
            "willpower": 4,
            "logic": 3,
            "intuition": 3,
            "charisma": 2
        },
        "skills": {
            "automatics": 6,
            "blades": 5,
            "heavy_weapons": 4,
            "unarmed_combat": 5,
            "running": 3,
            "intimidation": 4,
            "pilot_ground_craft": 3
        },
        "equipment": [
            {
                "name": "FN HAR",
                "type": "Assault Rifle",
                "damage": "5P",
                "accuracy": 6,
                "mode": "SA/BF/FA",
                "rc": 2
            },
            {
                "name": "Wired Reflexes",
                "type": "Cyberware",
                "rating": 2,
                "essence_cost": 2.0
            }
        ],
        "nuyen": 3000,
        "karma": 25
    },
    {
        "name": "Whisper",
        "metatype": "Human",
        "role": "Face",
        "attributes": {
            "body": 3,
            "agility": 4,
            "reaction": 3,
            "strength": 2,
            "willpower": 4,
            "logic": 4,
            "intuition": 4,
            "charisma": 6
        },
        "skills": {
            "con": 6,
            "negotiation": 6,
            "etiquette": 5,
            "intimidation": 4,
            "performance": 4,
            "leadership": 4,
            "pistols": 3
        },
        "equipment": [
            {
                "name": "Tailored Pheromones",
                "type": "Bioware",
                "rating": 3
            },
            {
                "name": "Ceska Black Scorpion",
                "type": "Machine Pistol",
                "damage": "2P",
                "accuracy": 5
            }
        ],
        "nuyen": 8000,
        "karma": 35
    }
]

SAMPLE_ENTITIES = [
    {
        "name": "Knight Errant Security Guard",
        "entity_type": "NPC",
        "data": {
            "metatype": "Human",
            "profession": "Security",
            "threat_level": "Low",
            "attributes": {
                "body": 4,
                "agility": 4,
                "reaction": 3,
                "strength": 3,
                "willpower": 3,
                "logic": 2,
                "intuition": 3,
                "charisma": 2
            },
            "equipment": [
                "Ares Predator III",
                "Armor Vest",
                "Commlink (Rating 3)"
            ]
        }
    },
    {
        "name": "Renraku Spider",
        "entity_type": "NPC",
        "data": {
            "metatype": "Elf",
            "profession": "Security Decker",
            "threat_level": "Medium",
            "attributes": {
                "body": 3,
                "agility": 4,
                "reaction": 4,
                "strength": 2,
                "willpower": 4,
                "logic": 5,
                "intuition": 4,
                "charisma": 3
            },
            "equipment": [
                "Renraku Tsurugi Cyberdeck",
                "Light Pistol",
                "Commlink (Rating 5)",
                "Datajack"
            ]
        }
    },
    {
        "name": "Lone Star Patrol Drone",
        "entity_type": "Drone",
        "data": {
            "drone_model": "MCT-Nissan Roto-Drone",
            "rating": 3,
            "pilot": 3,
            "armor": 6,
            "weapons": [
                "Mounted SMG"
            ]
        }
    }
]

SAMPLE_SCENES = [
    {
        "name": "Downtown Seattle Nightclub",
        "description": "The bass pounds through the walls of Club Penumbra, the hottest nightclub in Downtown Seattle. Neon lights cut through the artificial fog, revealing silhouettes dancing on elevated platforms. The VIP section overlooks the main floor, guarded by imposing troll bouncers.",
        "data": {
            "tags": ["urban", "nightlife", "social"],
            "security_rating": 3,
            "lighting": "dim",
            "crowd": "dense",
            "ambient": "techno music, crowd noise"
        }
    },
    {
        "name": "Aztechnology Corporate Server Room",
        "description": "Rows of sleek black server racks pulse with tiny blue lights, humming with the power of corporate data. The room is kept at a chilly temperature, with reinforced doors and multiple security checkpoints leading to this inner sanctum of digital secrets.",
        "data": {
            "tags": ["corporate", "high-security", "matrix"],
            "security_rating": 5,
            "ic_present": ["Patrol IC", "Killer IC", "Probe IC"],
            "alarm_rating": 4,
            "host_rating": 5
        }
    },
    {
        "name": "Redmond Barrens Hideout",
        "description": "A dilapidated concrete building stands among the urban decay of the Redmond Barrens. Inside, the gang has reinforced weak points and set up defensive positions. Makeshift barricades and lookout posts protect what has become their territory in this lawless zone.",
        "data": {
            "tags": ["barrens", "gang territory", "combat"],
            "security_rating": 2,
            "gangs_present": ["Rusted Stilettos"],
            "hazards": ["toxic waste", "unstable structure"],
            "loot_potential": 3
        }
    }
]

def create_sample_session():
    """Create a sample game session with associated data"""
    print("Creating sample game session...")
    
    # Create a new session
    session = Session(
        name="Night City Run",
        gm_notes="Corporate extraction mission with complications",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status="active"
    )
    db.session.add(session)
    db.session.flush()  # To get the session ID
    
    session_id = session.id
    print(f"Created session: {session.name} (ID: {session_id})")
    
    # Add characters to session
    for char_data in SAMPLE_CHARACTERS:
        character = Character(
            name=char_data["name"],
            data=char_data,
            session_id=session_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.session.add(character)
        print(f"Added character: {character.name}")
    
    # Add entities to session
    for entity_data in SAMPLE_ENTITIES:
        entity = Entity(
            name=entity_data["name"],
            entity_type=entity_data["entity_type"],
            data=entity_data["data"],
            session_id=session_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.session.add(entity)
        print(f"Added entity: {entity.name}")
    
    # Add scenes to session
    for scene_data in SAMPLE_SCENES:
        scene = Scene(
            name=scene_data["name"],
            description=scene_data["description"],
            data=scene_data["data"],
            session_id=session_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.session.add(scene)
        print(f"Added scene: {scene.name}")
    
    # Add some chat memory
    chat_memories = [
        {
            "role": "system",
            "content": "Session started. Welcome runners to the Night City extraction mission."
        },
        {
            "role": "user",
            "content": "Nova takes point and begins scanning for security systems."
        },
        {
            "role": "assistant",
            "content": "Nova's cyberdeck lights up as she connects to the local grid. She detects three security cameras and a keycard access panel at the main entrance."
        },
        {
            "role": "user",
            "content": "Brick moves to the side entrance to check for guards."
        }
    ]
    
    for i, memory in enumerate(chat_memories):
        chat_memory = ChatMemory(
            session_id=session_id,
            role=memory["role"],
            content=memory["content"],
            created_at=datetime.now() - timedelta(minutes=len(chat_memories) - i),
            sequence=i
        )
        db.session.add(chat_memory)
    
    print(f"Added {len(chat_memories)} chat messages")
    
    db.session.commit()
    print("Sample game session created successfully!")

def confirm_action():
    """Confirm with the user before proceeding"""
    response = input("This will add sample data to your database. Continue? (y/n): ")
    return response.lower() == 'y'

if __name__ == "__main__":
    with app.app_context():
        print("Shadowrun RPG Database Seed Script")
        print("==================================")
        
        if len(sys.argv) > 1 and sys.argv[1] == "--force":
            proceed = True
        else:
            proceed = confirm_action()
        
        if proceed:
            create_sample_session()
        else:
            print("Operation cancelled.")
