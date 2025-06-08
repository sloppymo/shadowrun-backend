# Image Generation System Documentation

## Overview

The Image Generation System allows players and Game Masters to create visual representations of scenes, characters, locations, and items within Shadowrun sessions. The system supports multiple AI image generation providers and includes features for prompt enhancement, image management, and gallery viewing.

## Features

### Core Functionality
- **Multi-Provider Support**: DALL-E 3, Stable Diffusion, and extensible architecture for additional providers
- **Shadowrun-Specific Enhancement**: AI-powered prompt enhancement for cyberpunk aesthetics
- **Real-time Generation**: Instant image generation with progress tracking
- **Queue Management**: Asynchronous processing for high-demand scenarios
- **Image Gallery**: Session-based image storage and viewing
- **Favorites System**: Mark and organize important scene images

### User Interface
- **Console Commands**: Generate images directly from the terminal interface
- **Visual Gallery**: Modern UI for browsing and managing generated images
- **Provider Selection**: Choose between available image generation services
- **Style Preferences**: Customize generation parameters

## API Endpoints

### Image Generation

#### Generate Image (Queued)
```http
POST /api/session/{session_id}/generate-image
```

**Request Body:**
```json
{
  "user_id": "string",
  "prompt": "string",
  "type": "scene|character|location|item",
  "priority": 1-3,
  "style_preferences": {
    "provider": "dalle|stability",
    "quality": "standard|hd",
    "size": "1024x1024"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "request_id": "uuid",
  "message": "Image generation request queued"
}
```

#### Generate Image (Instant)
```http
POST /api/session/{session_id}/generate-image-instant
```

**Request Body:**
```json
{
  "user_id": "string",
  "prompt": "string",
  "provider": "dalle|stability",
  "style_preferences": {
    "quality": "standard|hd",
    "size": "1024x1024"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "image_id": "uuid",
  "image_url": "string",
  "generation_time": 12.34,
  "provider": "dalle"
}
```

### Image Management

#### Get Session Images
```http
GET /api/session/{session_id}/images?user_id={user_id}&limit={limit}
```

**Response:**
```json
{
  "status": "success",
  "images": [
    {
      "id": "uuid",
      "prompt": "string",
      "image_url": "string",
      "provider": "dalle",
      "status": "completed",
      "created_at": "2024-01-01T00:00:00Z",
      "is_favorite": false,
      "tags": []
    }
  ],
  "count": 5
}
```

#### Get Image Details
```http
GET /api/session/{session_id}/image/{image_id}
```

#### Toggle Favorite
```http
POST /api/session/{session_id}/image/{image_id}/favorite
```

**Request Body:**
```json
{
  "user_id": "string",
  "is_favorite": true
}
```

#### Get Available Providers
```http
GET /api/session/{session_id}/image-providers
```

**Response:**
```json
{
  "status": "success",
  "providers": ["dalle", "stability"],
  "default": "dalle"
}
```

## Console Commands

### Image Generation Commands

#### Open Image Gallery
```
/image gallery
```
Opens the Scene Visualizer interface for browsing and generating images.

#### Generate Scene Image
```
/image generate [description]
```
Generates an image based on the provided description and opens the gallery.

**Examples:**
```
/image generate A rain-soaked Seattle street with neon signs
/image generate Corporate boardroom with holographic displays
/image generate Shadowrunner in tactical gear with cybernetic implants
```

## Database Schema

### GeneratedImage Table
```sql
CREATE TABLE generated_image (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    prompt TEXT NOT NULL,
    enhanced_prompt TEXT,
    image_url VARCHAR,
    thumbnail_url VARCHAR,
    provider VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    error_message TEXT,
    generation_time FLOAT,
    tags TEXT,
    is_favorite BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);
```

### ImageGeneration Table
```sql
CREATE TABLE image_generation (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    request_type VARCHAR NOT NULL,
    context TEXT NOT NULL,
    style_preferences TEXT,
    priority INTEGER NOT NULL DEFAULT 1,
    status VARCHAR NOT NULL DEFAULT 'queued',
    result_image_id VARCHAR,
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME
);
```

## Configuration

### Environment Variables

#### DALL-E 3 (OpenAI)
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

#### Stable Diffusion (Stability AI)
```bash
export STABILITY_API_KEY="your-stability-api-key"
```

### Provider Configuration

The system automatically detects available providers based on configured API keys:

- **DALL-E 3**: Requires `OPENAI_API_KEY`
- **Stable Diffusion**: Requires `STABILITY_API_KEY`

## Prompt Enhancement

The system includes AI-powered prompt enhancement specifically designed for Shadowrun imagery:

### Enhancement Features
- **Cyberpunk Aesthetics**: Adds appropriate visual style keywords
- **Shadowrun Context**: Incorporates setting-specific elements
- **Technical Optimization**: Optimizes prompts for better generation results
- **Fallback Enhancement**: Basic enhancement when LLM is unavailable

### Example Enhancement
**Original:** "A street scene"
**Enhanced:** "A rain-soaked Seattle street with neon lighting, cyberpunk aesthetic, urban decay, high-tech low-life atmosphere, corporate towers in background, cinematic lighting, detailed, 4k"

## Frontend Components

### ImageGallery Component

**Props:**
- `sessionId`: Current session identifier
- `isVisible`: Gallery visibility state
- `onClose`: Callback for closing the gallery

**Features:**
- **Tabbed Interface**: Generate and Gallery tabs
- **Real-time Updates**: Automatic refresh of image list
- **Modal Viewing**: Full-size image preview
- **Favorite Management**: Toggle favorite status
- **Provider Selection**: Choose generation provider

### Console Integration

The image generation system is fully integrated into the ShadowrunConsole component:

- **Command Recognition**: Handles `/image` commands
- **Session Validation**: Ensures user is in a session
- **Error Handling**: Provides clear error messages
- **UI Integration**: Seamlessly opens the gallery interface

## Error Handling

### Common Errors

#### API Key Not Configured
```json
{
  "error": "OpenAI API key not configured"
}
```

#### Session Validation
```json
{
  "error": "User not in session"
}
```

#### Generation Failures
```json
{
  "error": "DALL-E API error: 400 - Invalid prompt"
}
```

### Error Recovery

- **Automatic Retry**: Failed generations can be retried
- **Fallback Providers**: Switch to alternative providers
- **Graceful Degradation**: System continues functioning without image generation

## Performance Considerations

### Image Storage
- **Cloud Storage**: Production deployments should use cloud storage (AWS S3, etc.)
- **CDN Integration**: Implement CDN for faster image delivery
- **Thumbnail Generation**: Create thumbnails for gallery performance

### Rate Limiting
- **Provider Limits**: Respect API rate limits for each provider
- **Queue Management**: Implement proper queue processing
- **User Limits**: Consider per-user generation limits

### Caching
- **Image Caching**: Cache generated images appropriately
- **Prompt Caching**: Cache enhanced prompts to reduce LLM calls
- **Provider Status**: Cache provider availability status

## Testing

### Test Script
Run the comprehensive test suite:
```bash
python3 test_image_generation.py
```

### Test Coverage
- **Endpoint Functionality**: All API endpoints tested
- **Error Scenarios**: Missing API keys, invalid sessions
- **Database Operations**: Image storage and retrieval
- **Provider Detection**: Available provider enumeration

## Future Enhancements

### Planned Features
- **Batch Generation**: Generate multiple images from one prompt
- **Style Templates**: Pre-defined Shadowrun style templates
- **Image Editing**: Basic editing tools within the gallery
- **Collaborative Galleries**: Shared session galleries
- **Export Options**: Download images in various formats

### Provider Expansion
- **Midjourney Integration**: Add Midjourney support
- **Local Models**: Support for locally hosted models
- **Custom Providers**: Plugin architecture for custom providers

## Troubleshooting

### Common Issues

#### No Providers Available
1. Check environment variables are set
2. Restart the Flask server
3. Verify API key validity

#### Images Not Loading
1. Check image URLs are accessible
2. Verify CORS settings
3. Check network connectivity

#### Generation Failures
1. Review prompt content for policy violations
2. Check API key quotas and limits
3. Verify provider service status

### Debug Mode
Enable debug logging for detailed error information:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

### API Key Management
- **Environment Variables**: Store keys securely
- **Key Rotation**: Regularly rotate API keys
- **Access Control**: Limit key access to necessary services

### Content Filtering
- **Prompt Validation**: Validate prompts before generation
- **Content Moderation**: Implement content filtering
- **User Permissions**: Control who can generate images

### Data Privacy
- **Image Storage**: Secure image storage and access
- **User Data**: Protect user prompt history
- **Session Isolation**: Ensure session-based access control 