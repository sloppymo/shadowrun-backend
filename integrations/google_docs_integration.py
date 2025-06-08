"""
Google Docs Integration for Shadowrun Character Sheets
Allows WREN to read, parse, and update character sheets stored in Google Docs
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re

logger = logging.getLogger(__name__)

# Scopes required for Google Docs and Drive access
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

class GoogleDocsCharacterSheet:
    """Manages character sheet integration with Google Docs"""
    
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.drive_service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google APIs"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # If no valid credentials, authorize user
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    logger.error(f"Credentials file not found: {self.credentials_file}")
                    return
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('docs', 'v1', credentials=creds)
        self.drive_service = build('drive', 'v3', credentials=creds)
        logger.info("Google Docs API authenticated successfully")
    
    async def parse_character_sheet(self, document_id: str) -> Dict[str, Any]:
        """Parse a character sheet from a Google Doc"""
        try:
            # Get document content
            document = self.service.documents().get(documentId=document_id).execute()
            content = self._extract_text_content(document)
            
            # Parse character data using regex patterns
            character_data = self._parse_shadowrun_data(content)
            
            # Add metadata
            character_data['source'] = 'google_docs'
            character_data['document_id'] = document_id
            character_data['last_updated'] = datetime.utcnow().isoformat()
            
            logger.info(f"Successfully parsed character sheet from document {document_id}")
            return character_data
            
        except HttpError as e:
            logger.error(f"Google Docs API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error parsing character sheet: {e}")
            raise
    
    def _extract_text_content(self, document: Dict) -> str:
        """Extract plain text from Google Docs document structure"""
        content = ""
        body = document.get('body', {})
        
        for element in body.get('content', []):
            if 'paragraph' in element:
                paragraph = element['paragraph']
                for element_content in paragraph.get('elements', []):
                    if 'textRun' in element_content:
                        content += element_content['textRun'].get('content', '')
        
        return content
    
    def _parse_shadowrun_data(self, content: str) -> Dict[str, Any]:
        """Parse Shadowrun 6E character data from document text"""
        character_data = {
            'name': '',
            'handle': '',
            'archetype': '',
            'attributes': {},
            'skills': {},
            'qualities': {'positive': [], 'negative': [], 'symbolic': []},
            'gear': [],
            'lifestyle': {},
            'contacts': [],
            'edge': 0,
            'karma': 0,
            'nuyen': 0
        }
        
        # Extract character name
        name_match = re.search(r'(?:Name|Character):\s*([^\n\r]+)', content, re.IGNORECASE)
        if name_match:
            character_data['name'] = name_match.group(1).strip()
        
        # Extract handle/street name
        handle_match = re.search(r'(?:Handle|Street Name):\s*([^\n\r]+)', content, re.IGNORECASE)
        if handle_match:
            character_data['handle'] = handle_match.group(1).strip()
        
        # Extract archetype
        archetype_match = re.search(r'Archetype:\s*([^\n\r]+)', content, re.IGNORECASE)
        if archetype_match:
            character_data['archetype'] = archetype_match.group(1).strip()
        
        # Extract attributes (SR6E standard attributes)
        attributes = ['Body', 'Agility', 'Reaction', 'Strength', 'Willpower', 'Logic', 'Intuition', 'Charisma', 'Edge']
        for attr in attributes:
            pattern = f'{attr}:\s*(\d+)'
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                character_data['attributes'][attr.lower()] = int(match.group(1))
        
        # Extract skills (look for skill: rating patterns)
        skill_pattern = r'([A-Za-z\s]+?):\s*(\d+)(?:\s*\([^)]+\))?'
        skill_matches = re.findall(skill_pattern, content)
        
        # Filter out attributes and focus on skills
        known_skills = [
            'Astral', 'Athletics', 'Biotech', 'Close Combat', 'Con', 'Conjuring', 'Cracking',
            'Electronics', 'Enchanting', 'Engineering', 'Exotic Weapons', 'Firearms', 'Influence',
            'Outdoors', 'Perception', 'Piloting', 'Sorcery', 'Stealth', 'Tasking'
        ]
        
        for skill_name, rating in skill_matches:
            skill_name = skill_name.strip()
            if any(known_skill.lower() in skill_name.lower() for known_skill in known_skills):
                character_data['skills'][skill_name.lower().replace(' ', '_')] = int(rating)
        
        # Extract Edge
        edge_match = re.search(r'Edge:\s*(\d+)', content, re.IGNORECASE)
        if edge_match:
            character_data['edge'] = int(edge_match.group(1))
        
        # Extract Karma
        karma_match = re.search(r'Karma:\s*(\d+)', content, re.IGNORECASE)
        if karma_match:
            character_data['karma'] = int(karma_match.group(1))
        
        # Extract Nuyen
        nuyen_match = re.search(r'(?:Nuyen|¥):\s*([0-9,]+)', content, re.IGNORECASE)
        if nuyen_match:
            character_data['nuyen'] = int(nuyen_match.group(1).replace(',', ''))
        
        # Extract qualities
        qualities_section = re.search(r'Qualities:(.*?)(?:Equipment|Gear|$)', content, re.IGNORECASE | re.DOTALL)
        if qualities_section:
            qualities_text = qualities_section.group(1)
            # Simple extraction - could be enhanced with more sophisticated parsing
            quality_lines = [line.strip() for line in qualities_text.split('\n') if line.strip()]
            character_data['qualities']['positive'] = quality_lines
        
        return character_data
    
    async def update_character_sheet(self, document_id: str, character_data: Dict[str, Any]) -> bool:
        """Update a character sheet in Google Docs with new data"""
        try:
            # Get current document
            document = self.service.documents().get(documentId=document_id).execute()
            
            # Create update requests
            requests = self._build_update_requests(document, character_data)
            
            if requests:
                # Execute batch update
                result = self.service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': requests}
                ).execute()
                
                logger.info(f"Successfully updated character sheet {document_id}")
                return True
            else:
                logger.info("No updates needed for character sheet")
                return True
                
        except HttpError as e:
            logger.error(f"Google Docs API error during update: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating character sheet: {e}")
            return False
    
    def _build_update_requests(self, document: Dict, character_data: Dict[str, Any]) -> List[Dict]:
        """Build Google Docs API update requests based on character data changes"""
        requests = []
        content = self._extract_text_content(document)
        
        # Add timestamp update
        timestamp = f"\n\nLast updated by WREN: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        requests.append({
            'insertText': {
                'location': {'index': len(content)},
                'text': timestamp
            }
        })
        
        # Add edge tracking update if changed
        if 'current_edge' in character_data:
            edge_text = f"\nCurrent Edge: {character_data['current_edge']}/{character_data.get('edge', 0)}"
            requests.append({
                'insertText': {
                    'location': {'index': len(content) + len(timestamp)},
                    'text': edge_text
                }
            })
        
        return requests
    
    async def create_character_sheet_copy(self, document_id: str, session_id: str) -> str:
        """Create a copy of character sheet for WREN to manage"""
        try:
            # Get original document metadata
            original = self.drive_service.files().get(fileId=document_id).execute()
            
            # Create copy
            copy_metadata = {
                'name': f"WREN_Copy_{original['name']}_{session_id}",
                'parents': [original.get('parents', [None])[0]] if original.get('parents') else None
            }
            
            copied_file = self.drive_service.files().copy(
                fileId=document_id,
                body=copy_metadata
            ).execute()
            
            logger.info(f"Created character sheet copy: {copied_file['id']}")
            return copied_file['id']
            
        except HttpError as e:
            logger.error(f"Error creating character sheet copy: {e}")
            raise
    
    async def list_accessible_documents(self, user_email: str = None) -> List[Dict[str, str]]:
        """List character sheets accessible to WREN"""
        try:
            query = "name contains 'character' or name contains 'shadowrun'"
            if user_email:
                query += f" and '{user_email}' in writers"
            
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, modifiedTime, owners)"
            ).execute()
            
            documents = []
            for file in results.get('files', []):
                documents.append({
                    'id': file['id'],
                    'name': file['name'],
                    'modified': file['modifiedTime'],
                    'owner': file.get('owners', [{}])[0].get('emailAddress', 'Unknown')
                })
            
            return documents
            
        except HttpError as e:
            logger.error(f"Error listing documents: {e}")
            return []

class CharacterSheetSync:
    """Manages synchronization between Google Docs and local database"""
    
    def __init__(self, google_docs_service: GoogleDocsCharacterSheet, db_session):
        self.google_docs = google_docs_service
        self.db = db_session
    
    async def sync_character_sheet(self, document_id: str, session_id: str, user_id: str) -> Dict[str, Any]:
        """Sync character sheet from Google Docs to local database"""
        try:
            # Parse character data from Google Docs
            character_data = await self.google_docs.parse_character_sheet(document_id)
            
            # Import the Character model here to avoid circular imports
            from app import Character, db
            
            # Check if character already exists
            existing_character = Character.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).first()
            
            if existing_character:
                # Update existing character
                for field in ['name', 'handle', 'archetype', 'attributes', 'skills', 'qualities']:
                    if field in character_data:
                        if field in ['attributes', 'skills', 'qualities']:
                            setattr(existing_character, field, json.dumps(character_data[field]))
                        else:
                            setattr(existing_character, field, character_data[field])
                
                # Add integration metadata
                extra_data = json.loads(existing_character.extra_data or '{}')
                extra_data['google_docs'] = {
                    'document_id': document_id,
                    'last_sync': datetime.utcnow().isoformat()
                }
                existing_character.extra_data = json.dumps(extra_data)
                
                character = existing_character
            else:
                # Create new character
                character = Character(
                    session_id=session_id,
                    user_id=user_id,
                    name=character_data.get('name', ''),
                    handle=character_data.get('handle', ''),
                    archetype=character_data.get('archetype', ''),
                    attributes=json.dumps(character_data.get('attributes', {})),
                    skills=json.dumps(character_data.get('skills', {})),
                    qualities=json.dumps(character_data.get('qualities', {})),
                    extra_data=json.dumps({
                        'google_docs': {
                            'document_id': document_id,
                            'last_sync': datetime.utcnow().isoformat()
                        }
                    })
                )
                db.session.add(character)
            
            db.session.commit()
            
            logger.info(f"Successfully synced character sheet for user {user_id}")
            return {
                'status': 'success',
                'character_id': character.id,
                'character_name': character.name,
                'sync_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error syncing character sheet: {e}")
            db.session.rollback()
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def push_updates_to_docs(self, character_id: int, updates: Dict[str, Any]) -> bool:
        """Push character updates back to Google Docs"""
        try:
            from app import Character
            
            character = Character.query.get(character_id)
            if not character:
                return False
            
            extra_data = json.loads(character.extra_data or '{}')
            google_docs_info = extra_data.get('google_docs')
            
            if not google_docs_info or 'document_id' not in google_docs_info:
                logger.warning(f"No Google Docs integration for character {character_id}")
                return False
            
            # Update the Google Doc
            success = await self.google_docs.update_character_sheet(
                google_docs_info['document_id'],
                updates
            )
            
            if success:
                # Update sync timestamp
                google_docs_info['last_update_push'] = datetime.utcnow().isoformat()
                extra_data['google_docs'] = google_docs_info
                character.extra_data = json.dumps(extra_data)
                self.db.session.commit()
            
            return success
            
        except Exception as e:
            logger.error(f"Error pushing updates to Google Docs: {e}")
            return False 