#!/usr/bin/env python3
"""
Debug CLI for Shadowrun RPG System
Provides tools for inspecting game state, debugging issues, and replaying WebSocket streams
"""
import argparse
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Session, Character, Entity, PendingResponse, GeneratedImage, ChatMemory
from sqlalchemy import text


class DebugCLI:
    """Debug CLI for Shadowrun system"""
    
    def __init__(self):
        self.app = app
        self.setup_context()
    
    def setup_context(self):
        """Setup Flask app context"""
        self.app.app_context().push()
    
    def inspect_game_state(self, session_id: str):
        """Inspect complete game state for a session"""
        print(f"\n{'='*60}")
        print(f"GAME STATE INSPECTION - Session: {session_id}")
        print(f"{'='*60}\n")
        
        # Get session info
        session = Session.query.filter_by(id=session_id).first()
        if not session:
            print(f"ERROR: Session '{session_id}' not found!")
            return
        
        print(f"Session Name: {session.name}")
        print(f"GM User ID: {session.gm_user_id}")
        print(f"Created At: {session.created_at}")
        
        # Get characters
        print(f"\n{'- Characters ':-<50}")
        characters = Character.query.filter_by(session_id=session_id).all()
        for char in characters:
            print(f"\n  Character: {char.name} (User: {char.user_id})")
            if char.attributes:
                attrs = json.loads(char.attributes)
                print(f"  Attributes: {attrs}")
            if char.skills:
                skills = json.loads(char.skills)
                print(f"  Top Skills: {dict(sorted(skills.items(), key=lambda x: x[1], reverse=True)[:5])}")
        
        # Get entities
        print(f"\n{'- Entities ':-<50}")
        entities = Entity.query.filter_by(session_id=session_id).all()
        for entity in entities:
            print(f"  {entity.type.upper()}: {entity.name} - Status: {entity.status}")
            if entity.extra_data:
                data = json.loads(entity.extra_data)
                print(f"    Extra: {data}")
        
        # Get pending responses
        print(f"\n{'- Pending DM Reviews ':-<50}")
        pending = PendingResponse.query.filter_by(
            session_id=session_id, 
            status='pending'
        ).all()
        for p in pending:
            print(f"  [{p.priority}] {p.response_type} from {p.user_id}")
            print(f"    Context: {p.context[:100]}...")
            print(f"    Created: {p.created_at}")
        
        # Get recent images
        print(f"\n{'- Recent Images ':-<50}")
        images = GeneratedImage.query.filter_by(
            session_id=session_id
        ).order_by(GeneratedImage.created_at.desc()).limit(5).all()
        for img in images:
            print(f"  {img.prompt[:50]}... by {img.user_id}")
            print(f"    Status: {img.status}, Provider: {img.provider}")
        
        print(f"\n{'='*60}\n")
    
    def replay_ws_stream(self, stream_id: str):
        """Replay a WebSocket stream for debugging"""
        print(f"\n{'='*60}")
        print(f"WEBSOCKET STREAM REPLAY - ID: {stream_id}")
        print(f"{'='*60}\n")
        
        # In a real implementation, this would query a WebSocket log table
        # For now, we'll show how it would work
        print("WebSocket stream replay not implemented yet")
        print("Would show:")
        print("  - Connection establishment")
        print("  - Authentication flow")
        print("  - All messages sent/received")
        print("  - Disconnection reason")
        
    def dump_crisis_state(self):
        """Dump complete system state for crisis debugging"""
        print(f"\n{'='*60}")
        print(f"CRISIS STATE DUMP - {datetime.now()}")
        print(f"{'='*60}\n")
        
        # Database stats
        print("Database Statistics:")
        stats = {
            'sessions': Session.query.count(),
            'characters': Character.query.count(),
            'entities': Entity.query.count(),
            'pending_responses': PendingResponse.query.filter_by(status='pending').count(),
            'images': GeneratedImage.query.count(),
        }
        for table, count in stats.items():
            print(f"  {table}: {count}")
        
        # Active sessions
        print("\nActive Sessions (last 24h):")
        recent_sessions = Session.query.filter(
            Session.created_at >= text("datetime('now', '-1 day')")
        ).all()
        for s in recent_sessions:
            print(f"  {s.id}: {s.name} (GM: {s.gm_user_id})")
        
        # System health checks
        print("\nSystem Health:")
        try:
            # Check database connection
            db.session.execute(text('SELECT 1'))
            print("  ✓ Database connection: OK")
        except Exception as e:
            print(f"  ✗ Database connection: FAILED - {e}")
        
        # Memory usage (if psutil available)
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            print(f"  Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
            print(f"  CPU percent: {process.cpu_percent()}%")
        except ImportError:
            print("  Memory/CPU stats: psutil not installed")
        
        print(f"\n{'='*60}\n")
    
    def analyze_performance(self, session_id: Optional[str] = None):
        """Analyze performance metrics"""
        print(f"\n{'='*60}")
        print(f"PERFORMANCE ANALYSIS")
        print(f"{'='*60}\n")
        
        # Query execution times (would need logging enabled)
        print("Query Performance:")
        
        # Slow queries
        slow_queries = [
            "Complex character queries with JSON parsing",
            "Entity updates during combat",
            "Pending response joins"
        ]
        
        for query in slow_queries:
            print(f"  - {query}")
        
        # WebSocket metrics
        print("\nWebSocket Metrics:")
        print("  Average message latency: N/A (implement logging)")
        print("  Reconnection frequency: N/A")
        print("  Message queue sizes: N/A")
        
        # API response times
        print("\nAPI Response Times:")
        print("  /api/llm: Average N/A ms")
        print("  /api/session/*/generate-image: Average N/A ms")
        
    def fix_orphaned_data(self):
        """Find and fix orphaned data"""
        print(f"\n{'='*60}")
        print(f"ORPHANED DATA CHECK")
        print(f"{'='*60}\n")
        
        # Find characters without sessions
        orphaned_chars = db.session.query(Character).filter(
            ~Character.session_id.in_(
                db.session.query(Session.id)
            )
        ).all()
        
        if orphaned_chars:
            print(f"Found {len(orphaned_chars)} orphaned characters:")
            for char in orphaned_chars:
                print(f"  - {char.name} (Session: {char.session_id})")
        else:
            print("No orphaned characters found")
        
        # Find entities without sessions
        orphaned_entities = db.session.query(Entity).filter(
            ~Entity.session_id.in_(
                db.session.query(Session.id)
            )
        ).all()
        
        if orphaned_entities:
            print(f"\nFound {len(orphaned_entities)} orphaned entities:")
            for entity in orphaned_entities:
                print(f"  - {entity.name} (Session: {entity.session_id})")
        else:
            print("\nNo orphaned entities found")
        
        print(f"\n{'='*60}\n")
    
    def export_session_data(self, session_id: str, output_file: str):
        """Export complete session data for backup/analysis"""
        print(f"Exporting session {session_id} to {output_file}...")
        
        session = Session.query.filter_by(id=session_id).first()
        if not session:
            print(f"ERROR: Session '{session_id}' not found!")
            return
        
        data = {
            'session': {
                'id': session.id,
                'name': session.name,
                'gm_user_id': session.gm_user_id,
                'created_at': session.created_at.isoformat() if session.created_at else None
            },
            'characters': [],
            'entities': [],
            'chat_memory': [],
            'images': []
        }
        
        # Export characters
        for char in Character.query.filter_by(session_id=session_id).all():
            data['characters'].append({
                'id': char.id,
                'name': char.name,
                'user_id': char.user_id,
                'attributes': char.attributes,
                'skills': char.skills,
                'qualities': char.qualities,
                'gear': char.gear
            })
        
        # Export entities
        for entity in Entity.query.filter_by(session_id=session_id).all():
            data['entities'].append({
                'id': entity.id,
                'name': entity.name,
                'type': entity.type,
                'status': entity.status,
                'extra_data': entity.extra_data
            })
        
        # Export chat memory
        for memory in ChatMemory.query.filter_by(session_id=session_id).all():
            data['chat_memory'].append({
                'user_id': memory.user_id,
                'role': memory.role,
                'messages': memory.messages
            })
        
        # Export images
        for img in GeneratedImage.query.filter_by(session_id=session_id).all():
            data['images'].append({
                'id': img.id,
                'prompt': img.prompt,
                'image_url': img.image_url,
                'provider': img.provider,
                'status': img.status
            })
        
        # Write to file
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Export complete! Data written to {output_file}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Shadowrun Debug CLI')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Inspect command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect game state')
    inspect_parser.add_argument('session_id', help='Session ID to inspect')
    
    # Replay command
    replay_parser = subparsers.add_parser('replay', help='Replay WebSocket stream')
    replay_parser.add_argument('stream_id', help='Stream ID to replay')
    
    # Crisis command
    crisis_parser = subparsers.add_parser('crisis', help='Dump crisis state')
    crisis_parser.add_argument('--dump-ws', action='store_true', help='Include WebSocket dumps')
    
    # Performance command
    perf_parser = subparsers.add_parser('perf', help='Analyze performance')
    perf_parser.add_argument('--session', help='Specific session to analyze')
    
    # Fix command
    fix_parser = subparsers.add_parser('fix', help='Fix orphaned data')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export session data')
    export_parser.add_argument('session_id', help='Session ID to export')
    export_parser.add_argument('-o', '--output', default='session_export.json', help='Output file')
    
    args = parser.parse_args()
    
    cli = DebugCLI()
    
    if args.command == 'inspect':
        cli.inspect_game_state(args.session_id)
    elif args.command == 'replay':
        cli.replay_ws_stream(args.stream_id)
    elif args.command == 'crisis':
        cli.dump_crisis_state()
    elif args.command == 'perf':
        cli.analyze_performance(args.session)
    elif args.command == 'fix':
        cli.fix_orphaned_data()
    elif args.command == 'export':
        cli.export_session_data(args.session_id, args.output)
    else:
        parser.print_help()


if __name__ == '__main__':
    main() 