# Slack Integration System Documentation

## Overview

The Slack Integration System extends the Shadowrun RPG system to work seamlessly within Slack workspaces. Players can use slash commands to interact with the AI, generate images, manage sessions, and roll dice directly from Slack channels.

## Key Features

### 1. **Slash Commands**
- `/sr-session` - Create and manage game sessions
- `/sr-ai` - Request AI responses (with DM review)
- `/sr-image` - Generate scene images
- `/sr-roll` - Roll dice
- `/sr-dm` - Access DM dashboard
- `/sr-help` - Show command help

### 2. **Session Management**
- Map Slack channels to game sessions
- Automatic session creation and player management
- Channel-based session isolation

### 3. **DM Review Integration**
- AI requests from Slack go through DM review system
- Real-time notifications to Slack when responses are approved
- Seamless integration with existing DM dashboard

### 4. **Image Sharing**
- Generate and share scene images directly in Slack
- Automatic upload to Slack with rich formatting
- Provider information and generation stats

## Architecture

### Core Components

#### 1. SlackBot Class (`slack_integration.py`)
```python
class SlackBot:
    - Handles Slack API communication
    - Manages authentication and verification
    - Formats messages with Shadowrun theming
    - Uploads images and media
```

#### 2. SlackCommandProcessor Class (`slack_integration.py`)
```python
class SlackCommandProcessor:
    - Processes slash commands
    - Maps commands to system functions
    - Handles command validation and routing
```

#### 3. SlackSession Model (`app.py`)
```python
class SlackSession(db.Model):
    - Maps Slack channels to game sessions
    - Ensures unique session per channel
    - Links team_id + channel_id to session_id
```

### API Endpoints

#### 1. Command Handler
```
POST /api/slack/command
- Receives slash command payloads
- Verifies Slack signatures
- Routes to appropriate handlers
```

#### 2. Events Handler
```
POST /api/slack/events
- Handles Slack events (mentions, etc.)
- URL verification for app setup
- App mention responses
```

#### 3. Interactive Components
```
POST /api/slack/interactive
- Handles button clicks and interactions
- DM dashboard button actions
- Modal submissions
```

## Slash Commands Reference

### `/sr-session [action] [parameters]`

**Create a new session:**
```
/sr-session create My Campaign Name
```
- Creates a new game session
- Maps to current Slack channel
- User becomes the Game Master

**Get session info:**
```
/sr-session info
```
- Shows current session details
- Lists GM and connected players
- Session status and statistics

### `/sr-ai [message]`

**Request AI response:**
```
/sr-ai What do I see when I enter the abandoned warehouse?
```
- Submits AI request for DM review
- Shows processing status
- Notifies when DM approves/rejects

### `/sr-image [description]`

**Generate scene image:**
```
/sr-image A rain-soaked Seattle street with neon signs reflecting on wet pavement
```
- Generates image using AI providers
- Uploads directly to Slack channel
- Shows generation statistics

### `/sr-roll [dice notation]`

**Roll dice:**
```
/sr-roll 3d6
/sr-roll 2d10
/sr-roll 1d20
```
- Supports standard dice notation
- Shows individual rolls and total
- Public roll results

### `/sr-dm [action]`

**Access DM dashboard:**
```
/sr-dm dashboard
```
- Provides link to web-based DM controls
- Only available to session GMs
- Opens review interface

### `/sr-help`

**Show command help:**
```
/sr-help
```
- Lists all available commands
- Usage examples
- Getting started guide

## Setup and Configuration

### 1. Slack App Creation

1. Go to [Slack API Console](https://api.slack.com/apps)
2. Create new app "Shadowrun RPG Assistant"
3. Configure OAuth & Permissions:
   ```
   Bot Token Scopes:
   - app_mentions:read
   - channels:read
   - chat:write
   - chat:write.public
   - commands
   - files:write
   - users:read
   ```

### 2. Slash Commands Setup

Configure each slash command in Slack app:

| Command | Request URL | Description |
|---------|-------------|-------------|
| `/sr-session` | `https://your-domain.com/api/slack/command` | Session management |
| `/sr-ai` | `https://your-domain.com/api/slack/command` | AI requests |
| `/sr-image` | `https://your-domain.com/api/slack/command` | Image generation |
| `/sr-roll` | `https://your-domain.com/api/slack/command` | Dice rolling |
| `/sr-dm` | `https://your-domain.com/api/slack/command` | DM dashboard |
| `/sr-help` | `https://your-domain.com/api/slack/command` | Command help |

### 3. Event Subscriptions

Configure event subscriptions:
```
Request URL: https://your-domain.com/api/slack/events

Subscribe to Bot Events:
- app_mention
```

### 4. Interactive Components

```
Request URL: https://your-domain.com/api/slack/interactive
```

### 5. Environment Variables

```bash
# Required Slack credentials
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token  # Optional for Socket Mode
```

## Database Schema

### SlackSession Table
```sql
CREATE TABLE slack_session (
    id INTEGER PRIMARY KEY,
    slack_team_id VARCHAR NOT NULL,
    slack_channel_id VARCHAR NOT NULL,
    session_id VARCHAR NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES session(id),
    UNIQUE(slack_team_id, slack_channel_id)
);
```

## Integration with Existing Systems

### 1. DM Review System Integration

When users submit AI requests via `/sr-ai`:
1. Request creates `PendingResponse` entry
2. DM receives notification in dashboard
3. Upon approval, response is posted to Slack channel
4. Rejection sends ephemeral message to user

### 2. Image Generation Integration

When users request images via `/sr-image`:
1. Request processed by `ImageGenerator`
2. Image saved to `GeneratedImage` table
3. Image uploaded to Slack with metadata
4. Generation stats included in message

### 3. Session Management Integration

Slack channels map to existing Session system:
1. Each channel can have one active session
2. Session permissions carry over (GM/Player roles)
3. All existing session features available

## Message Formatting

### Shadowrun-Themed Responses

The system uses consistent Shadowrun-themed formatting:

```python
# Success messages
✅ *System Success*
Operation completed successfully

# Error messages  
⚠️ *System Error*
```
Error details here
```

# AI responses
🤖 *Shadowrun Matrix Interface*
```
AI response content here
```

# DM notifications
🎮 *DM Notification*
Review required for player request
[Open DM Dashboard] (button)
```

## Security Features

### 1. Request Verification
- All requests verified with Slack signing secret
- Prevents replay attacks with timestamp validation
- Rejects unauthorized requests

### 2. Channel Isolation
- Sessions are isolated per Slack channel
- No cross-channel data leakage
- Team-specific session management

### 3. Permission System
- GM permissions enforced
- DM commands restricted to session GMs
- Player actions validated

## Error Handling

### Common Error Scenarios

1. **No Active Session**
   ```
   Error: No active session in this channel. 
   Use `/sr-session create` first.
   ```

2. **Invalid Dice Notation**
   ```
   Invalid dice notation. Use format like "3d6" or "2d10".
   ```

3. **AI Provider Errors**
   ```
   Image generation failed: API key not configured
   ```

4. **Permission Errors**
   ```
   This command is only available to Game Masters.
   ```

## Testing

### Unit Tests
```bash
# Run Slack integration tests
python -m pytest test_slack_integration.py -v
```

### Test Coverage
- ✅ Slash command processing
- ✅ Event handling
- ✅ Interactive components
- ✅ Session mapping
- ✅ Error handling
- ✅ Message formatting
- ✅ Database operations

### Manual Testing

1. **Command Testing**
   ```bash
   # Test in Slack channel
   /sr-session create Test Campaign
   /sr-ai What do I see?
   /sr-image A cyberpunk street
   /sr-roll 3d6
   /sr-help
   ```

2. **Integration Testing**
   - Create session in Slack
   - Submit AI request
   - Verify DM review process
   - Check image generation
   - Test dice rolling

## Deployment

### 1. Backend Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SLACK_BOT_TOKEN=your-token
export SLACK_SIGNING_SECRET=your-secret

# Run application
python app.py
```

### 2. Slack App Distribution

1. **Private Distribution**
   - Install to your workspace
   - Configure permissions
   - Test all commands

2. **Public Distribution** (Future)
   - App store submission
   - Privacy policy
   - Terms of service

## Usage Examples

### Complete Session Workflow

1. **Create Session**
   ```
   /sr-session create "Shadowrun: Seattle Shadows"
   ```

2. **Generate Opening Scene**
   ```
   /sr-image The team stands in a rain-soaked alley behind the Stuffer Shack, neon signs reflecting off wet concrete
   ```

3. **Player Interaction**
   ```
   /sr-ai I want to check the dumpster for any clues about the missing person
   ```

4. **Action Resolution**
   ```
   /sr-roll 3d6  # Perception check
   ```

5. **DM Review**
   - DM receives notification
   - Reviews AI response
   - Approves/edits response
   - Result posted to channel

## Advanced Features

### 1. Bulk Operations
- Multiple dice rolls
- Batch image generation
- Session statistics

### 2. Rich Formatting
- Embedded images
- Interactive buttons
- Threaded responses

### 3. Notifications
- Real-time DM alerts
- Player status updates
- Session reminders

## Troubleshooting

### Common Issues

1. **Commands Not Working**
   - Check Slack app permissions
   - Verify request URL configuration
   - Check environment variables

2. **Images Not Uploading**
   - Verify file write permissions
   - Check image provider API keys
   - Confirm Slack file upload permissions

3. **DM Review Not Working**
   - Ensure session exists
   - Check DM permissions
   - Verify database connectivity

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

### Planned Features

1. **Socket Mode Support**
   - Real-time bidirectional communication
   - Instant notifications
   - Better user experience

2. **Advanced Dice Rolling**
   - Shadowrun-specific mechanics
   - Edge dice
   - Glitch detection

3. **Character Sheet Integration**
   - Slack-based character creation
   - Stat tracking
   - Skill checks

4. **Campaign Management**
   - Multi-session campaigns
   - Story progression tracking
   - NPC databases

## Contributing

### Development Setup
```bash
git clone https://github.com/your-repo/shadowrun-backend
cd shadowrun-backend
pip install -r requirements.txt
python -m pytest test_slack_integration.py
```

### Code Style
- Follow PEP 8
- Use type hints
- Add docstrings
- Write tests for new features

## Support

For issues and questions:
- GitHub Issues: [Repository Issues](https://github.com/your-repo/issues)
- Documentation: [System Docs](./README.md)
- Discord: [Community Server](https://discord.gg/your-server) 