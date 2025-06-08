# Shadowrun GM Dashboard - Backend API Documentation

## Overview

The Shadowrun GM Dashboard backend is a Flask-based REST API that provides comprehensive campaign management capabilities for Shadowrun 6th Edition tabletop RPG sessions. The system supports character management, combat tracking, Matrix operations, AI-powered narrative assistance, image generation, and Slack integration.

## Architecture

### Technology Stack
- **Framework**: Flask (Python web framework)
- **Database**: SQLite with SQLAlchemy ORM
- **AI Integration**: OpenAI GPT models for narrative assistance
- **Image Generation**: DALL-E, Stable Diffusion, Midjourney
- **Real-time Communication**: Server-Sent Events (SSE)
- **External Integrations**: Slack API, Google Docs API
- **Security**: CORS, security headers, input validation

### Core Components
1. **Session Management**: Multi-user campaign sessions with role-based access
2. **Character System**: Complete SR6E character sheet storage and management
3. **Combat Manager**: Initiative tracking, damage calculation, action logging
4. **Matrix Dashboard**: Virtual reality hacking simulation
5. **DM Review System**: AI response moderation and approval workflow
6. **Image Generation**: AI-powered scene and character visualization
7. **Slack Integration**: Bot-based gameplay and notifications
8. **Character Sheet Integration**: Google Docs and Slack synchronization

## Database Models

### Core Session Models

#### Session
Represents a Shadowrun campaign session with GM and player participants.
Each session maintains its own isolated game state, characters, and narrative.

**Fields:**
- `id` (String, Primary Key): UUID identifier
- `name` (String): Campaign/session name
- `gm_user_id` (String): Game Master's user ID
- `created_at` (DateTime): Session creation timestamp

#### UserRole
Defines user permissions and roles within each session.
Supports multiple role types for flexible campaign management.

**Fields:**
- `id` (Integer, Primary Key): Auto-increment ID
- `session_id` (String, Foreign Key): Reference to session
- `user_id` (String): User identifier
- `role` (String): User role ('player', 'gm', 'observer')

#### Character
Comprehensive character sheet storage for Shadowrun 6E characters.
Supports all character creation methods and stores both mechanical stats and narrative elements.

**Key JSON Fields:**
- `attributes`: {body, agility, reaction, logic, intuition, willpower, charisma, edge}
- `skills`: {skill_name: rating, specialization: bonus, ...}
- `qualities`: {positive: [...], negative: [...], symbolic: [...]}
- `gear`: [{name, category, rating, availability, cost, description}, ...]
- `contacts`: [{name, connection, loyalty, archetype, description}, ...]

## API Endpoints

### Character Management

#### GET /api/session/{session_id}/characters
**Get All Characters in Session**

Retrieves all character sheets for a specific session with comprehensive character data.

**Parameters:**
- `session_id` (path): Session identifier

**Response Example:**
```json
[
  {
    "id": 1,
    "user_id": "user123",
    "name": "Alex Chen",
    "handle": "Neon",
    "archetype": "Decker",
    "attributes": "{\"body\": 3, \"agility\": 4, \"reaction\": 5, \"logic\": 6}",
    "skills": "{\"hacking\": 6, \"electronics\": 5}",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

#### POST /api/session/{session_id}/character
**Create New Character**

Creates a new character sheet in the specified session.

**Request Body:**
```json
{
  "user_id": "user123",
  "name": "Alex Chen",
  "handle": "Neon",
  "archetype": "Decker",
  "attributes": "{\"body\": 3, \"agility\": 4, \"reaction\": 5}",
  "skills": "{\"hacking\": 6, \"electronics\": 5}"
}
```

**Response:**
```json
{
  "status": "success",
  "character_id": 1
}
```

### Scene Management

#### GET /api/session/{session_id}/scene
**Get Current Scene**

Retrieves the current narrative scene description for the session.

**Response:**
```json
{
  "session_id": "session123",
  "summary": "The team stands in the neon-lit alley behind the Stuffer Shack, rain pattering on the concrete."
}
```

#### POST /api/session/{session_id}/scene
**Update Scene Description**

Updates the current narrative scene for the session. Only Game Masters can modify scenes.

**Request Body:**
```json
{
  "user_id": "gm_user123",
  "summary": "The team enters the abandoned warehouse. Dust motes dance in shafts of light."
}
```

### DM Review System

#### GET /api/session/{session_id}/pending-responses
**Get Pending AI Responses**

Retrieves all AI-generated responses awaiting Game Master review, sorted by priority.

**Query Parameters:**
- `user_id`: Game Master's user ID for authentication

**Response:**
```json
[
  {
    "id": "response123",
    "user_id": "player456",
    "context": "Player attempts to hack the corporate mainframe",
    "ai_response": "The ICE detects your intrusion attempt. Roll Hacking + Logic [6] vs. Firewall 8.",
    "response_type": "dice_roll",
    "priority": 3,
    "created_at": "2024-01-15T14:30:00Z"
  }
]
```

#### POST /api/session/{session_id}/pending-response/{response_id}/review
**Review AI Response**

Allows Game Masters to approve, reject, or edit AI-generated responses.

**Request Body (Approve):**
```json
{
  "user_id": "gm_user123",
  "action": "approved",
  "dm_notes": "Good response, approved as-is"
}
```

**Request Body (Edit):**
```json
{
  "user_id": "gm_user123",
  "action": "edited",
  "dm_notes": "Modified to increase difficulty",
  "final_response": "The military-grade ICE detects your intrusion. Roll Hacking + Logic [6] vs. Firewall 10."
}
```

### Image Generation

#### POST /api/session/{session_id}/generate-image
**Generate Scene Image**

Requests AI generation of a scene image with queuing and status tracking.

**Request Body:**
```json
{
  "user_id": "gm_user123",
  "description": "A neon-lit cyberpunk alley with rain-slicked streets",
  "style": "cyberpunk",
  "provider": "dalle"
}
```

**Response:**
```json
{
  "status": "queued",
  "image_id": "img123",
  "estimated_time": 30
}
```

#### GET /api/session/{session_id}/images
**Get Session Images**

Retrieves all generated images for a session with filtering options.

**Query Parameters:**
- `status` (optional): Filter by status (completed, pending, failed)
- `favorites_only` (optional): Show only favorited images

**Response:**
```json
{
  "images": [
    {
      "id": "img123",
      "prompt": "Cyberpunk alley scene",
      "image_url": "https://example.com/images/img123.jpg",
      "status": "completed",
      "is_favorite": true,
      "created_at": "2024-01-15T16:00:00Z"
    }
  ],
  "total": 1
}
```

### AI Integration

#### POST /api/llm
**Stream AI Response**

Generates streaming AI responses for narrative assistance.

**Request Body:**
```json
{
  "input": "The player wants to negotiate with the gang leader",
  "session_id": "session123",
  "user_id": "gm_user123",
  "context": "Previous scene context here"
}
```

**Response:** Server-Sent Events stream
```
data: {"type": "token", "content": "The gang leader"}
data: {"type": "token", "content": " leans back"}
data: {"type": "complete", "full_response": "The gang leader leans back in his chair."}
```

### Slack Integration

#### POST /api/slack/command
**Handle Slack Slash Commands**

Processes Slack slash commands for bot interactions.

**Supported Commands:**
- `/shadowrun roll 6d6` - Roll dice
- `/shadowrun scene [description]` - Update scene
- `/shadowrun image [description]` - Generate image

#### POST /api/slack/events
**Handle Slack Events**

Processes Slack events like app mentions and direct messages.

## Error Handling

### Standard Error Response Format
```json
{
  "status": "error",
  "error": "Descriptive error message",
  "error_code": "SPECIFIC_ERROR_CODE"
}
```

### Common HTTP Status Codes
- **200 OK**: Successful request
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

## Security Features

### Security Headers
- **HSTS**: Enforces HTTPS connections
- **Content Security Policy**: Prevents XSS attacks
- **X-Frame-Options**: Prevents clickjacking
- **X-Content-Type-Options**: Prevents MIME sniffing

### Authentication & Authorization
- Session-based authentication
- Role-based access control (GM, Player, Observer)
- Permission checks on all sensitive operations
- Audit logging for administrative actions

## Rate Limiting

### Limits by Endpoint Category
- **Character Operations**: 100 requests/minute
- **AI/LLM Requests**: 20 requests/minute
- **Image Generation**: 5 requests/minute
- **General API**: 200 requests/minute

## Development Setup

### Environment Variables
```bash
FLASK_ENV=development
DATABASE_URL=sqlite:///shadowrun.db
OPENAI_API_KEY=your_openai_key
SLACK_BOT_TOKEN=your_slack_token
GOOGLE_DOCS_API_KEY=your_google_key
```

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
flask db upgrade

# Run development server
python app.py
```

### Testing
```bash
# Run unit tests
python -m pytest tests/

# Run integration tests
python -m pytest tests/integration/

# Run with coverage
python -m pytest --cov=src tests/
``` 