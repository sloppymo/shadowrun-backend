import os
import json
import hmac
import hashlib
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier

class SlackBot:
    """Slack bot integration for Shadowrun system"""
    
    def __init__(self):
        self.client = None
        self.signing_secret = None
        self.bot_token = None
        self.app_token = None
        self.signature_verifier = None
        self._setup_credentials()
    
    def _setup_credentials(self):
        """Setup Slack credentials from environment variables"""
        self.bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.signing_secret = os.getenv("SLACK_SIGNING_SECRET")
        self.app_token = os.getenv("SLACK_APP_TOKEN")
        
        if self.bot_token:
            self.client = WebClient(token=self.bot_token)
        
        if self.signing_secret:
            self.signature_verifier = SignatureVerifier(self.signing_secret)
    
    def is_configured(self) -> bool:
        """Check if Slack integration is properly configured"""
        return self.bot_token is not None and self.signing_secret is not None
    
    def verify_slack_request(self, headers: Dict, body: str) -> bool:
        """Verify that the request came from Slack"""
        if not self.signature_verifier:
            return False
        
        try:
            timestamp = headers.get("X-Slack-Request-Timestamp", "")
            signature = headers.get("X-Slack-Signature", "")
            
            # Check timestamp to prevent replay attacks
            if abs(time.time() - int(timestamp)) > 60 * 5:  # 5 minutes
                return False
            
            return self.signature_verifier.is_valid(
                timestamp=timestamp,
                signature=signature,
                body=body
            )
        except Exception as e:
            print(f"Slack verification error: {e}")
            return False
    
    async def send_message(self, channel: str, text: str, blocks: List[Dict] = None, 
                          thread_ts: str = None, ephemeral_user: str = None) -> Dict:
        """Send a message to a Slack channel"""
        if not self.client:
            raise Exception("Slack client not configured")
        
        try:
            if ephemeral_user:
                # Send ephemeral message (only visible to specific user)
                response = self.client.chat_postEphemeral(
                    channel=channel,
                    user=ephemeral_user,
                    text=text,
                    blocks=blocks,
                    thread_ts=thread_ts
                )
            else:
                # Send public message
                response = self.client.chat_postMessage(
                    channel=channel,
                    text=text,
                    blocks=blocks,
                    thread_ts=thread_ts
                )
            return response.data
        except SlackApiError as e:
            print(f"Slack API error: {e.response['error']}")
            raise
    
    async def upload_image(self, channel: str, image_url: str, title: str, 
                          comment: str = None, thread_ts: str = None) -> Dict:
        """Upload an image to a Slack channel"""
        if not self.client:
            raise Exception("Slack client not configured")
        
        try:
            # For external URLs, we'll share the link with a rich preview
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{title}*\n{comment or ''}"
                    }
                },
                {
                    "type": "image",
                    "image_url": image_url,
                    "alt_text": title
                }
            ]
            
            return await self.send_message(
                channel=channel,
                text=f"Generated image: {title}",
                blocks=blocks,
                thread_ts=thread_ts
            )
        except SlackApiError as e:
            print(f"Slack upload error: {e.response['error']}")
            raise
    
    def format_shadowrun_response(self, response: str, response_type: str = "general") -> List[Dict]:
        """Format responses with Shadowrun-themed Slack blocks"""
        if response_type == "error":
            return [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":warning: *System Error*\n```{response}```"
                    }
                }
            ]
        elif response_type == "success":
            return [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":white_check_mark: *System Success*\n{response}"
                    }
                }
            ]
        elif response_type == "dm_notification":
            return [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":video_game: *DM Notification*\n{response}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Open DM Dashboard"
                            },
                            "value": "open_dm_dashboard",
                            "action_id": "dm_dashboard_button"
                        }
                    ]
                }
            ]
        elif response_type == "image_generated":
            return [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":art: *Scene Generated*\n{response}"
                    }
                }
            ]
        else:
            # General shadowrun-themed response
            return [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":robot_face: *Shadowrun Matrix Interface*\n```{response}```"
                    }
                }
            ]
    
    def get_user_info(self, user_id: str) -> Dict:
        """Get user information from Slack"""
        if not self.client:
            raise Exception("Slack client not configured")
        
        try:
            response = self.client.users_info(user=user_id)
            return response.data["user"]
        except SlackApiError as e:
            print(f"Error getting user info: {e}")
            return {}
    
    def get_channel_info(self, channel_id: str) -> Dict:
        """Get channel information from Slack"""
        if not self.client:
            raise Exception("Slack client not configured")
        
        try:
            response = self.client.conversations_info(channel=channel_id)
            return response.data["channel"]
        except SlackApiError as e:
            print(f"Error getting channel info: {e}")
            return {}

class SlackCommandProcessor:
    """Process Slack slash commands and map them to Shadowrun system"""
    
    def __init__(self, slack_bot: SlackBot):
        self.bot = slack_bot
        self.command_map = {
            '/sr-session': self.handle_session_command,
            '/sr-dm': self.handle_dm_command,
            '/sr-ai': self.handle_ai_command,
            '/sr-image': self.handle_image_command,
            '/sr-roll': self.handle_dice_command,
            '/sr-help': self.handle_help_command,
        }
    
    async def process_command(self, command_data: Dict) -> Dict:
        """Process incoming slash command"""
        command = command_data.get('command', '')
        text = command_data.get('text', '')
        user_id = command_data.get('user_id', '')
        channel_id = command_data.get('channel_id', '')
        team_id = command_data.get('team_id', '')
        
        # Create session context
        context = {
            'command': command,
            'args': text.split() if text else [],
            'user_id': user_id,
            'channel_id': channel_id,
            'team_id': team_id,
            'slack_session_id': f"{team_id}_{channel_id}"  # Use team+channel as session ID
        }
        
        handler = self.command_map.get(command)
        if handler:
            return await handler(context)
        else:
            return {
                'response_type': 'ephemeral',
                'text': f"Unknown command: {command}. Use `/sr-help` for available commands."
            }
    
    async def handle_session_command(self, context: Dict) -> Dict:
        """Handle session management commands"""
        args = context['args']
        if not args:
            return {
                'response_type': 'ephemeral',
                'text': 'Usage: `/sr-session [create|join|info] [name/id]`'
            }
        
        action = args[0]
        slack_session_id = context['slack_session_id']
        
        if action == 'create':
            session_name = ' '.join(args[1:]) if len(args) > 1 else f"Slack Session {context['channel_id']}"
            
            # Call backend to create session  
            try:
                # Import here to avoid circular imports
                import asyncio
                from app import create_session_for_slack
                
                session_data = asyncio.run(create_session_for_slack(
                    name=session_name,
                    gm_user_id=context['user_id'],
                    slack_channel_id=context['channel_id'],
                    slack_team_id=context['team_id']
                ))
                
                response_text = f"Session '{session_name}' created successfully!\n" \
                              f"Session ID: {session_data['session_id']}\n" \
                              f"You are the Game Master."
                
                return {
                    'response_type': 'in_channel',
                    'blocks': self.bot.format_shadowrun_response(response_text, "success")
                }
                
            except Exception as e:
                return {
                    'response_type': 'ephemeral',
                    'blocks': self.bot.format_shadowrun_response(str(e), "error")
                }
        
        elif action == 'info':
            # Get session info
            try:
                from app import get_slack_session_info
                session_info = asyncio.run(get_slack_session_info(slack_session_id))
                
                if session_info:
                    response_text = f"Active Session: {session_info['name']}\n" \
                                  f"GM: <@{session_info['gm_user_id']}>\n" \
                                  f"Players: {len(session_info['players'])} connected"
                else:
                    response_text = "No active session in this channel.\nUse `/sr-session create [name]` to start a new session."
                
                return {
                    'response_type': 'ephemeral',
                    'blocks': self.bot.format_shadowrun_response(response_text, "general")
                }
                
            except Exception as e:
                return {
                    'response_type': 'ephemeral',
                    'blocks': self.bot.format_shadowrun_response(str(e), "error")
                }
        
        else:
            return {
                'response_type': 'ephemeral',
                'text': 'Usage: `/sr-session [create|info] [name]`'
            }
    
    async def handle_dm_command(self, context: Dict) -> Dict:
        """Handle DM-specific commands"""
        args = context['args']
        
        if not args or args[0] == 'dashboard':
            # Generate DM dashboard link
            dashboard_url = f"http://localhost:3000/console?dm=true&session={context['slack_session_id']}"
            
            return {
                'response_type': 'ephemeral',
                'blocks': [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":video_game: *DM Dashboard*\nAccess your Game Master controls:"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Open DM Dashboard"
                                },
                                "url": dashboard_url,
                                "action_id": "open_dashboard"
                            }
                        ]
                    }
                ]
            }
        
        return {
            'response_type': 'ephemeral',
            'text': 'Usage: `/sr-dm [dashboard]`'
        }
    
    async def handle_ai_command(self, context: Dict) -> Dict:
        """Handle AI response requests"""
        if not context['args']:
            return {
                'response_type': 'ephemeral',
                'text': 'Usage: `/sr-ai [your message to the AI]`'
            }
        
        message = ' '.join(context['args'])
        
        # Send immediate response
        immediate_response = {
            'response_type': 'in_channel',
            'blocks': self.bot.format_shadowrun_response(
                f"AI request from <@{context['user_id']}>: {message}\n" \
                f"⏳ Processing request... DM will review before delivery.",
                "general"
            )
        }
        
        # Process AI request asynchronously  
        try:
            from app import process_slack_ai_request
            asyncio.run(process_slack_ai_request(
                session_id=context['slack_session_id'],
                user_id=context['user_id'],
                message=message,
                channel_id=context['channel_id']
            ))
        except Exception as e:
            print(f"Error processing AI request: {e}")
        
        return immediate_response
    
    async def handle_image_command(self, context: Dict) -> Dict:
        """Handle image generation commands"""
        args = context['args']
        
        if not args:
            return {
                'response_type': 'ephemeral',
                'text': 'Usage: `/sr-image [description of the scene]`'
            }
        
        description = ' '.join(args)
        
        # Send immediate response
        immediate_response = {
            'response_type': 'in_channel',
            'blocks': self.bot.format_shadowrun_response(
                f"Image generation request from <@{context['user_id']}>:\n" \
                f"*Scene:* {description}\n" \
                f"⏳ Generating image...",
                "general"
            )
        }
        
        # Process image generation asynchronously
        try:
            from app import process_slack_image_request
            asyncio.run(process_slack_image_request(
                session_id=context['slack_session_id'],
                user_id=context['user_id'],
                description=description,
                channel_id=context['channel_id']
            ))
        except Exception as e:
            print(f"Error processing image request: {e}")
        
        return immediate_response
    
    async def handle_dice_command(self, context: Dict) -> Dict:
        """Handle dice rolling commands"""
        args = context['args']
        
        if not args:
            return {
                'response_type': 'ephemeral',
                'text': 'Usage: `/sr-roll [dice notation, e.g., 3d6, 2d10]`'
            }
        
        dice_notation = args[0]
        
        try:
            # Simple dice rolling logic
            import random
            import re
            
            # Parse dice notation (e.g., "3d6")
            match = re.match(r'(\d+)d(\d+)', dice_notation.lower())
            if not match:
                return {
                    'response_type': 'ephemeral',
                    'text': 'Invalid dice notation. Use format like "3d6" or "2d10".'
                }
            
            num_dice = int(match.group(1))
            dice_size = int(match.group(2))
            
            if num_dice > 20 or dice_size > 100:
                return {
                    'response_type': 'ephemeral',
                    'text': 'Dice limits: Maximum 20 dice, maximum d100.'
                }
            
            # Roll dice
            rolls = [random.randint(1, dice_size) for _ in range(num_dice)]
            total = sum(rolls)
            
            # Format results
            rolls_text = ', '.join(map(str, rolls))
            result_text = f"<@{context['user_id']}> rolled {dice_notation}:\n" \
                         f"**Rolls:** {rolls_text}\n" \
                         f"**Total:** {total}"
            
            return {
                'response_type': 'in_channel',
                'blocks': self.bot.format_shadowrun_response(result_text, "success")
            }
            
        except Exception as e:
            return {
                'response_type': 'ephemeral',
                'blocks': self.bot.format_shadowrun_response(f"Dice roll error: {str(e)}", "error")
            }
    
    async def handle_help_command(self, context: Dict) -> Dict:
        """Show help for Slack commands"""
        help_text = """
*Shadowrun Slack Commands:*

• `/sr-session create [name]` - Create a new game session
• `/sr-session info` - Show current session info
• `/sr-dm dashboard` - Open DM control panel
• `/sr-ai [message]` - Send message to AI (requires DM review)
• `/sr-image [description]` - Generate scene image
• `/sr-roll [dice]` - Roll dice (e.g., 3d6, 2d10)
• `/sr-help` - Show this help

*Getting Started:*
1. Create a session: `/sr-session create My Campaign`
2. Players can then use other commands in the channel
3. DMs use `/sr-dm dashboard` to access advanced controls

*Examples:*
• `/sr-ai What do I see in the abandoned warehouse?`
• `/sr-image A rain-soaked Seattle street with neon signs`
• `/sr-roll 3d6`
        """
        
        return {
            'response_type': 'ephemeral',
            'blocks': [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": help_text
                    }
                }
            ]
        }

# Global instances
slack_bot = SlackBot()
slack_processor = SlackCommandProcessor(slack_bot) 