"""
Unified Character Sheet Manager
Manages character sheets across Google Docs, Slack, and local database
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum

from .google_docs_integration import GoogleDocsCharacterSheet, CharacterSheetSync as GoogleDocsSync
from .slack_integration import SlackCharacterSheet, SlackCharacterSheetSync

logger = logging.getLogger(__name__)

class IntegrationType(Enum):
    GOOGLE_DOCS = "google_docs"
    SLACK = "slack"
    LOCAL = "local"

class CharacterSheetManager:
    """Unified manager for character sheets across all platforms"""
    
    def __init__(self, db_session):
        self.db = db_session
        
        # Initialize integration services
        try:
            self.google_docs = GoogleDocsCharacterSheet()
            self.google_sync = GoogleDocsSync(self.google_docs, db_session)
            self.google_available = True
        except Exception as e:
            logger.warning(f"Google Docs integration not available: {e}")
            self.google_docs = None
            self.google_sync = None
            self.google_available = False
        
        try:
            self.slack = SlackCharacterSheet()
            self.slack_sync = SlackCharacterSheetSync(self.slack, db_session)
            self.slack_available = True
        except Exception as e:
            logger.warning(f"Slack integration not available: {e}")
            self.slack = None
            self.slack_sync = None
            self.slack_available = False
    
    async def discover_character_sheets(self, session_id: str, user_id: str = None) -> Dict[str, List[Dict]]:
        """Discover character sheets across all platforms"""
        discovered_sheets = {
            'google_docs': [],
            'slack': [],
            'local': []
        }
        
        # Discover Google Docs sheets
        if self.google_available:
            try:
                from app import UserRole, Session
                session = Session.query.get(session_id)
                if session:
                    # Get user email if available for targeted search
                    user_email = None
                    if user_id:
                        # This would need to be implemented based on your user system
                        pass
                    
                    docs = await self.google_docs.list_accessible_documents(user_email)
                    discovered_sheets['google_docs'] = [
                        {
                            'id': doc['id'],
                            'name': doc['name'],
                            'type': 'google_docs',
                            'modified': doc['modified'],
                            'owner': doc['owner'],
                            'source': 'Google Docs'
                        }
                        for doc in docs
                    ]
                    
            except Exception as e:
                logger.error(f"Error discovering Google Docs sheets: {e}")
        
        # Discover Slack sheets
        if self.slack_available:
            try:
                from app import SlackSession
                slack_session = SlackSession.query.filter_by(session_id=session_id).first()
                if slack_session:
                    sheets = await self.slack.find_character_sheets(
                        slack_session.slack_channel_id, user_id
                    )
                    discovered_sheets['slack'] = [
                        {
                            **sheet,
                            'type': 'slack',
                            'source': 'Slack'
                        }
                        for sheet in sheets
                    ]
                    
            except Exception as e:
                logger.error(f"Error discovering Slack sheets: {e}")
        
        # Get local database sheets
        try:
            from app import Character
            query = Character.query.filter_by(session_id=session_id)
            if user_id:
                query = query.filter_by(user_id=user_id)
            
            local_characters = query.all()
            discovered_sheets['local'] = [
                {
                    'id': char.id,
                    'name': char.name,
                    'handle': char.handle,
                    'type': 'local',
                    'user_id': char.user_id,
                    'created_at': char.created_at.isoformat() if char.created_at else None,
                    'source': 'Local Database'
                }
                for char in local_characters
            ]
            
        except Exception as e:
            logger.error(f"Error getting local sheets: {e}")
        
        return discovered_sheets
    
    async def import_character_sheet(self, session_id: str, user_id: str, 
                                   source_type: str, source_reference: Dict[str, Any]) -> Dict[str, Any]:
        """Import a character sheet from external source to local database"""
        try:
            if source_type == 'google_docs':
                if not self.google_available:
                    return {'status': 'error', 'error': 'Google Docs integration not available'}
                
                result = await self.google_sync.sync_character_sheet(
                    source_reference['document_id'], session_id, user_id
                )
                
                # Create a WREN-managed copy
                if result['status'] == 'success':
                    copy_id = await self.google_docs.create_character_sheet_copy(
                        source_reference['document_id'], session_id
                    )
                    
                    # Update character with copy reference
                    from app import Character
                    character = Character.query.get(result['character_id'])
                    if character:
                        extra_data = json.loads(character.extra_data or '{}')
                        extra_data['google_docs']['wren_copy_id'] = copy_id
                        character.extra_data = json.dumps(extra_data)
                        self.db.session.commit()
                        
                        result['wren_copy_id'] = copy_id
                
                return result
                
            elif source_type == 'slack':
                if not self.slack_available:
                    return {'status': 'error', 'error': 'Slack integration not available'}
                
                return await self.slack_sync.sync_from_slack(
                    source_reference['channel_id'], user_id, session_id, source_reference
                )
                
            else:
                return {'status': 'error', 'error': f'Unknown source type: {source_type}'}
                
        except Exception as e:
            logger.error(f"Error importing character sheet: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def update_character_sheet(self, character_id: int, updates: Dict[str, Any], 
                                   sync_to_external: bool = True) -> Dict[str, Any]:
        """Update character sheet and optionally sync to external sources"""
        try:
            from app import Character
            
            character = Character.query.get(character_id)
            if not character:
                return {'status': 'error', 'error': 'Character not found'}
            
            # Apply updates to local character
            update_count = 0
            for field, value in updates.items():
                if hasattr(character, field):
                    if field in ['attributes', 'skills', 'qualities', 'gear', 'contacts']:
                        # JSON fields
                        if isinstance(value, dict) or isinstance(value, list):
                            setattr(character, field, json.dumps(value))
                        else:
                            setattr(character, field, value)
                    else:
                        setattr(character, field, value)
                    update_count += 1
            
            # Update timestamp
            character.updated_at = datetime.utcnow()
            self.db.session.commit()
            
            result = {
                'status': 'success',
                'character_id': character_id,
                'updates_applied': update_count,
                'sync_results': {}
            }
            
            # Sync to external sources if requested
            if sync_to_external:
                extra_data = json.loads(character.extra_data or '{}')
                
                # Sync to Google Docs
                if 'google_docs' in extra_data and self.google_available:
                    google_result = await self.google_sync.push_updates_to_docs(character_id, updates)
                    result['sync_results']['google_docs'] = google_result
                
                # Sync to Slack
                if 'slack' in extra_data and self.slack_available:
                    slack_result = await self.slack_sync.push_updates_to_slack(character_id, updates)
                    result['sync_results']['slack'] = slack_result
            
            return result
            
        except Exception as e:
            logger.error(f"Error updating character sheet: {e}")
            self.db.session.rollback()
            return {'status': 'error', 'error': str(e)}
    
    async def create_wren_managed_copy(self, character_id: int) -> Dict[str, Any]:
        """Create WREN-managed copies in external platforms"""
        try:
            from app import Character
            
            character = Character.query.get(character_id)
            if not character:
                return {'status': 'error', 'error': 'Character not found'}
            
            extra_data = json.loads(character.extra_data or '{}')
            result = {'status': 'success', 'copies_created': {}}
            
            # Create Google Docs copy
            if 'google_docs' in extra_data and self.google_available:
                google_info = extra_data['google_docs']
                if 'document_id' in google_info and 'wren_copy_id' not in google_info:
                    try:
                        copy_id = await self.google_docs.create_character_sheet_copy(
                            google_info['document_id'], character.session_id
                        )
                        google_info['wren_copy_id'] = copy_id
                        result['copies_created']['google_docs'] = copy_id
                    except Exception as e:
                        logger.error(f"Error creating Google Docs copy: {e}")
                        result['copies_created']['google_docs'] = f"Error: {str(e)}"
            
            # Create Slack managed thread
            if 'slack' in extra_data and self.slack_available:
                slack_info = extra_data['slack']
                if 'channel_id' in slack_info and 'wren_thread_ts' not in slack_info:
                    try:
                        # Get current character data
                        character_data = {
                            'name': character.name,
                            'handle': character.handle,
                            'archetype': character.archetype,
                            'attributes': json.loads(character.attributes or '{}'),
                            'skills': json.loads(character.skills or '{}'),
                            'qualities': json.loads(character.qualities or '{}')
                        }
                        
                        thread_ts = await self.slack.create_character_sheet_thread(
                            slack_info['channel_id'], character_data
                        )
                        slack_info['wren_thread_ts'] = thread_ts
                        result['copies_created']['slack'] = thread_ts
                    except Exception as e:
                        logger.error(f"Error creating Slack thread: {e}")
                        result['copies_created']['slack'] = f"Error: {str(e)}"
            
            # Update character with new copy references
            character.extra_data = json.dumps(extra_data)
            self.db.session.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating WREN managed copies: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def sync_all_character_sheets(self, session_id: str) -> Dict[str, Any]:
        """Sync all character sheets for a session"""
        try:
            from app import Character
            
            characters = Character.query.filter_by(session_id=session_id).all()
            results = {
                'status': 'success',
                'total_characters': len(characters),
                'sync_results': {}
            }
            
            for character in characters:
                char_result = {
                    'character_name': character.name,
                    'google_docs': None,
                    'slack': None
                }
                
                extra_data = json.loads(character.extra_data or '{}')
                
                # Sync from Google Docs
                if 'google_docs' in extra_data and self.google_available:
                    try:
                        google_info = extra_data['google_docs']
                        if 'document_id' in google_info:
                            char_data = await self.google_docs.parse_character_sheet(
                                google_info['document_id']
                            )
                            # Apply updates to character
                            await self.update_character_sheet(character.id, char_data, sync_to_external=False)
                            char_result['google_docs'] = 'success'
                    except Exception as e:
                        char_result['google_docs'] = f'error: {str(e)}'
                
                # Sync from Slack
                if 'slack' in extra_data and self.slack_available:
                    try:
                        slack_info = extra_data['slack']
                        if 'reference' in slack_info:
                            sync_result = await self.slack_sync.sync_from_slack(
                                slack_info['channel_id'],
                                character.user_id,
                                character.session_id,
                                slack_info['reference']
                            )
                            char_result['slack'] = sync_result['status']
                    except Exception as e:
                        char_result['slack'] = f'error: {str(e)}'
                
                results['sync_results'][str(character.id)] = char_result
            
            return results
            
        except Exception as e:
            logger.error(f"Error syncing all character sheets: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of all integrations"""
        return {
            'google_docs': {
                'available': self.google_available,
                'authenticated': self.google_docs is not None,
                'service_status': 'ready' if self.google_available else 'not_configured'
            },
            'slack': {
                'available': self.slack_available,
                'authenticated': self.slack is not None,
                'service_status': 'ready' if self.slack_available else 'not_configured'
            }
        }
    
    async def get_character_integration_info(self, character_id: int) -> Dict[str, Any]:
        """Get integration information for a specific character"""
        try:
            from app import Character
            
            character = Character.query.get(character_id)
            if not character:
                return {'status': 'error', 'error': 'Character not found'}
            
            extra_data = json.loads(character.extra_data or '{}')
            
            info = {
                'character_id': character_id,
                'character_name': character.name,
                'integrations': {}
            }
            
            # Google Docs integration info
            if 'google_docs' in extra_data:
                google_info = extra_data['google_docs']
                info['integrations']['google_docs'] = {
                    'connected': True,
                    'document_id': google_info.get('document_id'),
                    'wren_copy_id': google_info.get('wren_copy_id'),
                    'last_sync': google_info.get('last_sync'),
                    'last_update_push': google_info.get('last_update_push')
                }
            else:
                info['integrations']['google_docs'] = {'connected': False}
            
            # Slack integration info
            if 'slack' in extra_data:
                slack_info = extra_data['slack']
                info['integrations']['slack'] = {
                    'connected': True,
                    'channel_id': slack_info.get('channel_id'),
                    'reference_type': slack_info.get('reference', {}).get('type'),
                    'wren_thread_ts': slack_info.get('wren_thread_ts'),
                    'last_sync': slack_info.get('last_sync'),
                    'last_update_push': slack_info.get('last_update_push')
                }
            else:
                info['integrations']['slack'] = {'connected': False}
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting character integration info: {e}")
            return {'status': 'error', 'error': str(e)} 