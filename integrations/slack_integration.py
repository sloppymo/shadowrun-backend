"""
Slack Integration for Shadowrun Character Sheets
Allows WREN to access, parse, and manage character sheets shared in Slack
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import requests

logger = logging.getLogger(__name__)

class SlackCharacterSheet:
    """Manages character sheet integration with Slack"""
    
    def __init__(self, slack_token: str = None):
        self.slack_token = slack_token or os.getenv('SLACK_BOT_TOKEN')
        if not self.slack_token:
            raise ValueError("Slack token not provided and SLACK_BOT_TOKEN environment variable not set")
        
        self.client = WebClient(token=self.slack_token)
        self.user_client = WebClient(token=os.getenv('SLACK_USER_TOKEN'))  # For file access
        
    async def find_character_sheets(self, channel_id: str, user_id: str = None) -> List[Dict[str, Any]]:
        """Find character sheets shared in a Slack channel"""
        try:
            # Search for messages containing character sheet keywords
            query_terms = [
                "character sheet",
                "shadowrun character",
                "SR6E character",
                "runner profile",
                "character build"
            ]
            
            sheets = []
            
            for query in query_terms:
                try:
                    # Search for messages
                    response = await self._search_messages(channel_id, query, user_id)
                    
                    for message in response.get('messages', []):
                        # Check for file attachments
                        if 'files' in message:
                            for file in message['files']:
                                if self._is_character_sheet_file(file):
                                    sheets.append({
                                        'type': 'file',
                                        'file_id': file['id'],
                                        'file_name': file['name'],
                                        'file_type': file['filetype'],
                                        'user_id': message['user'],
                                        'timestamp': message['ts'],
                                        'channel_id': channel_id,
                                        'url': file.get('url_private', ''),
                                        'size': file.get('size', 0)
                                    })
                        
                        # Check for text-based character sheets
                        text = message.get('text', '')
                        if self._is_character_sheet_text(text):
                            sheets.append({
                                'type': 'message',
                                'message_ts': message['ts'],
                                'user_id': message['user'],
                                'channel_id': channel_id,
                                'text': text,
                                'timestamp': message['ts']
                            })
                            
                except SlackApiError as e:
                    logger.warning(f"Slack search error for query '{query}': {e}")
                    continue
            
            # Remove duplicates and sort by timestamp
            unique_sheets = {sheet['file_id'] if sheet['type'] == 'file' else sheet['message_ts']: sheet for sheet in sheets}
            sorted_sheets = sorted(unique_sheets.values(), key=lambda x: x['timestamp'], reverse=True)
            
            logger.info(f"Found {len(sorted_sheets)} character sheets in channel {channel_id}")
            return sorted_sheets
            
        except Exception as e:
            logger.error(f"Error finding character sheets: {e}")
            return []
    
    async def _search_messages(self, channel_id: str, query: str, user_id: str = None) -> Dict:
        """Search for messages in a specific channel"""
        try:
            search_query = f"in:#{channel_id} {query}"
            if user_id:
                search_query += f" from:{user_id}"
            
            response = self.client.search_messages(
                query=search_query,
                count=50,
                sort='timestamp',
                sort_dir='desc'
            )
            
            return response.data
            
        except SlackApiError as e:
            logger.error(f"Slack message search error: {e}")
            return {}
    
    def _is_character_sheet_file(self, file: Dict) -> bool:
        """Check if a file is likely a character sheet"""
        file_name = file.get('name', '').lower()
        file_type = file.get('filetype', '').lower()
        
        # Check file name patterns
        sheet_patterns = [
            'character', 'sheet', 'runner', 'shadowrun', 'sr6', 'sr6e',
            'build', 'stats', 'profile'
        ]
        
        name_match = any(pattern in file_name for pattern in sheet_patterns)
        
        # Check file types (documents, spreadsheets, text files)
        valid_types = ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'xlsx', 'ods', 'csv']
        type_match = file_type in valid_types
        
        return name_match and type_match
    
    def _is_character_sheet_text(self, text: str) -> bool:
        """Check if message text contains character sheet data"""
        # Look for common Shadowrun character sheet patterns
        patterns = [
            r'(?:Body|Agility|Reaction|Strength|Willpower|Logic|Intuition|Charisma|Edge):\s*\d+',
            r'(?:Firearms|Close Combat|Athletics|Stealth|Electronics):\s*\d+',
            r'Handle:\s*[\w\s"]+',
            r'Archetype:\s*[\w\s]+',
            r'Essence:\s*[\d.]+',
            r'Initiative:\s*\d+',
            r'Physical Monitor|Stun Monitor',
            r'Karma:\s*\d+',
            r'Nuyen|¥'
        ]
        
        # Need at least 3 patterns to consider it a character sheet
        matches = sum(1 for pattern in patterns if re.search(pattern, text, re.IGNORECASE))
        return matches >= 3
    
    async def download_character_sheet_file(self, file_id: str) -> Tuple[bytes, str]:
        """Download a character sheet file from Slack"""
        try:
            # Get file info
            file_info = self.client.files_info(file=file_id)
            file_data = file_info['file']
            
            # Download file content
            download_url = file_data['url_private']
            headers = {'Authorization': f'Bearer {self.slack_token}'}
            
            response = requests.get(download_url, headers=headers)
            response.raise_for_status()
            
            return response.content, file_data['filetype']
            
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            raise
    
    async def parse_character_sheet_from_file(self, file_content: bytes, file_type: str) -> Dict[str, Any]:
        """Parse character data from downloaded file"""
        try:
            # Convert file content to text based on type
            if file_type == 'txt':
                text = file_content.decode('utf-8')
            elif file_type == 'pdf':
                # Would need PyPDF2 or similar for PDF parsing
                text = self._extract_pdf_text(file_content)
            elif file_type in ['doc', 'docx']:
                # Would need python-docx for Word document parsing
                text = self._extract_word_text(file_content)
            else:
                # Fallback to text extraction
                try:
                    text = file_content.decode('utf-8')
                except UnicodeDecodeError:
                    text = file_content.decode('latin-1')
            
            # Parse the extracted text
            return self._parse_shadowrun_data(text)
            
        except Exception as e:
            logger.error(f"Error parsing character sheet file: {e}")
            raise
    
    def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF content (placeholder implementation)"""
        # This would require PyPDF2 or pdfplumber
        logger.warning("PDF parsing not implemented - install PyPDF2 or pdfplumber")
        return ""
    
    def _extract_word_text(self, content: bytes) -> str:
        """Extract text from Word document (placeholder implementation)"""
        # This would require python-docx
        logger.warning("Word document parsing not implemented - install python-docx")
        return ""
    
    async def parse_character_sheet_from_message(self, channel_id: str, message_ts: str) -> Dict[str, Any]:
        """Parse character data from a Slack message"""
        try:
            # Get message content
            response = self.client.conversations_history(
                channel=channel_id,
                latest=message_ts,
                inclusive=True,
                limit=1
            )
            
            if not response['messages']:
                raise ValueError("Message not found")
            
            message = response['messages'][0]
            text = message.get('text', '')
            
            # Parse character data
            character_data = self._parse_shadowrun_data(text)
            
            # Add Slack metadata
            character_data['source'] = 'slack_message'
            character_data['channel_id'] = channel_id
            character_data['message_ts'] = message_ts
            character_data['user_id'] = message.get('user')
            character_data['last_updated'] = datetime.utcnow().isoformat()
            
            return character_data
            
        except Exception as e:
            logger.error(f"Error parsing character sheet from message: {e}")
            raise
    
    def _parse_shadowrun_data(self, content: str) -> Dict[str, Any]:
        """Parse Shadowrun 6E character data from text content"""
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
            'nuyen': 0,
            'essence': 6.0,
            'initiative': 0
        }
        
        # Extract character name (multiple possible formats)
        name_patterns = [
            r'(?:Name|Character):\s*([^\n\r]+)',
            r'Character Name:\s*([^\n\r]+)',
            r'^([A-Za-z\s]+)(?:\s*-\s*Shadowrun)',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                character_data['name'] = match.group(1).strip()
                break
        
        # Extract handle/street name
        handle_patterns = [
            r'(?:Handle|Street Name|Runner Name):\s*["\']?([^"\'\n\r]+)["\']?',
            r'aka\s*["\']([^"\'\n\r]+)["\']'
        ]
        
        for pattern in handle_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                character_data['handle'] = match.group(1).strip()
                break
        
        # Extract archetype
        archetype_match = re.search(r'Archetype:\s*([^\n\r]+)', content, re.IGNORECASE)
        if archetype_match:
            character_data['archetype'] = archetype_match.group(1).strip()
        
        # Extract attributes
        attributes = ['Body', 'Agility', 'Reaction', 'Strength', 'Willpower', 'Logic', 'Intuition', 'Charisma', 'Edge']
        for attr in attributes:
            patterns = [
                f'{attr}:\s*(\d+)',
                f'{attr}\s*=\s*(\d+)',
                f'{attr}\s+(\d+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    character_data['attributes'][attr.lower()] = int(match.group(1))
                    break
        
        # Extract skills
        skill_patterns = [
            r'([A-Za-z\s]+?):\s*(\d+)(?:\s*\([^)]+\))?',
            r'([A-Za-z\s]+?)\s*=\s*(\d+)',
            r'([A-Za-z\s]+?)\s+(\d+)(?:\s*\([^)]+\))?'
        ]
        
        known_skills = [
            'Astral', 'Athletics', 'Biotech', 'Close Combat', 'Con', 'Conjuring', 'Cracking',
            'Electronics', 'Enchanting', 'Engineering', 'Exotic Weapons', 'Firearms', 'Influence',
            'Outdoors', 'Perception', 'Piloting', 'Sorcery', 'Stealth', 'Tasking'
        ]
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for skill_name, rating in matches:
                skill_name = skill_name.strip()
                if any(known_skill.lower() in skill_name.lower() for known_skill in known_skills):
                    if skill_name.lower() not in [attr.lower() for attr in attributes]:  # Exclude attributes
                        character_data['skills'][skill_name.lower().replace(' ', '_')] = int(rating)
        
        # Extract other values
        essence_match = re.search(r'Essence:\s*([\d.]+)', content, re.IGNORECASE)
        if essence_match:
            character_data['essence'] = float(essence_match.group(1))
        
        karma_match = re.search(r'Karma:\s*(\d+)', content, re.IGNORECASE)
        if karma_match:
            character_data['karma'] = int(karma_match.group(1))
        
        nuyen_match = re.search(r'(?:Nuyen|¥):\s*([0-9,]+)', content, re.IGNORECASE)
        if nuyen_match:
            character_data['nuyen'] = int(nuyen_match.group(1).replace(',', ''))
        
        initiative_match = re.search(r'Initiative:\s*(\d+)', content, re.IGNORECASE)
        if initiative_match:
            character_data['initiative'] = int(initiative_match.group(1))
        
        return character_data
    
    async def update_character_in_slack(self, channel_id: str, message_ts: str, character_data: Dict[str, Any]) -> bool:
        """Update character sheet message in Slack"""
        try:
            # Format character data as updated message
            updated_text = self._format_character_sheet(character_data)
            
            # Add WREN update notice
            updated_text += f"\n\n_Updated by WREN at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}_"
            
            # Update the message
            response = self.client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=updated_text
            )
            
            return response['ok']
            
        except SlackApiError as e:
            logger.error(f"Error updating Slack message: {e}")
            return False
    
    def _format_character_sheet(self, character_data: Dict[str, Any]) -> str:
        """Format character data as readable Slack message"""
        text = f"**{character_data.get('name', 'Unknown')}**"
        
        if character_data.get('handle'):
            text += f" (Handle: {character_data['handle']})"
        
        if character_data.get('archetype'):
            text += f"\nArchetype: {character_data['archetype']}"
        
        # Attributes
        if character_data.get('attributes'):
            text += "\n\n**Attributes:**"
            for attr, value in character_data['attributes'].items():
                text += f"\n{attr.title()}: {value}"
        
        # Skills
        if character_data.get('skills'):
            text += "\n\n**Skills:**"
            for skill, value in character_data['skills'].items():
                text += f"\n{skill.replace('_', ' ').title()}: {value}"
        
        # Other stats
        if character_data.get('essence'):
            text += f"\nEssence: {character_data['essence']}"
        
        if character_data.get('karma'):
            text += f"\nKarma: {character_data['karma']}"
        
        if character_data.get('nuyen'):
            text += f"\nNuyen: {character_data['nuyen']:,}"
        
        return text
    
    async def create_character_sheet_thread(self, channel_id: str, character_data: Dict[str, Any]) -> str:
        """Create a new character sheet message thread"""
        try:
            formatted_sheet = self._format_character_sheet(character_data)
            formatted_sheet += "\n\n_This character sheet is managed by WREN_"
            
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=formatted_sheet,
                thread_ts=None  # This will create a new thread
            )
            
            return response['ts']
            
        except SlackApiError as e:
            logger.error(f"Error creating character sheet thread: {e}")
            raise

class SlackCharacterSheetSync:
    """Manages synchronization between Slack and local database"""
    
    def __init__(self, slack_service: SlackCharacterSheet, db_session):
        self.slack = slack_service
        self.db = db_session
    
    async def sync_from_slack(self, channel_id: str, user_id: str, session_id: str, 
                             sheet_reference: Dict[str, Any]) -> Dict[str, Any]:
        """Sync character sheet from Slack to local database"""
        try:
            # Parse character data based on type
            if sheet_reference['type'] == 'file':
                file_content, file_type = await self.slack.download_character_sheet_file(
                    sheet_reference['file_id']
                )
                character_data = await self.slack.parse_character_sheet_from_file(
                    file_content, file_type
                )
            else:  # message
                character_data = await self.slack.parse_character_sheet_from_message(
                    channel_id, sheet_reference['message_ts']
                )
            
            # Import the Character model
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
                
                # Add Slack metadata
                extra_data = json.loads(existing_character.extra_data or '{}')
                extra_data['slack'] = {
                    'channel_id': channel_id,
                    'reference': sheet_reference,
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
                        'slack': {
                            'channel_id': channel_id,
                            'reference': sheet_reference,
                            'last_sync': datetime.utcnow().isoformat()
                        }
                    })
                )
                db.session.add(character)
            
            db.session.commit()
            
            logger.info(f"Successfully synced character sheet from Slack for user {user_id}")
            return {
                'status': 'success',
                'character_id': character.id,
                'character_name': character.name,
                'sync_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error syncing character sheet from Slack: {e}")
            db.session.rollback()
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def push_updates_to_slack(self, character_id: int, updates: Dict[str, Any]) -> bool:
        """Push character updates back to Slack"""
        try:
            from app import Character
            
            character = Character.query.get(character_id)
            if not character:
                return False
            
            extra_data = json.loads(character.extra_data or '{}')
            slack_info = extra_data.get('slack')
            
            if not slack_info:
                logger.warning(f"No Slack integration for character {character_id}")
                return False
            
            channel_id = slack_info['channel_id']
            reference = slack_info['reference']
            
            # Update based on original type
            if reference['type'] == 'message':
                # Update the original message
                success = await self.slack.update_character_in_slack(
                    channel_id, reference['message_ts'], updates
                )
            else:
                # For file-based sheets, create a new message with updates
                await self.slack.create_character_sheet_thread(channel_id, updates)
                success = True
            
            if success:
                # Update sync timestamp
                slack_info['last_update_push'] = datetime.utcnow().isoformat()
                extra_data['slack'] = slack_info
                character.extra_data = json.dumps(extra_data)
                self.db.session.commit()
            
            return success
            
        except Exception as e:
            logger.error(f"Error pushing updates to Slack: {e}")
            return False 