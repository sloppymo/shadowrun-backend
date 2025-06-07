# Shadowrun DM Review System

## Overview

The DM Review System is a comprehensive workflow that allows Game Masters to review, approve, edit, or reject AI-generated responses before they are delivered to players. This ensures quality control and maintains narrative consistency in Shadowrun RPG sessions.

## Features

### Core Functionality
- **AI Response Generation**: Players can request AI responses that are queued for DM review
- **Review Dashboard**: GMs get a dedicated interface to review pending responses
- **Approval Workflow**: GMs can approve, edit, or reject AI responses
- **Notification System**: Real-time notifications for new review requests
- **Audit Trail**: Complete history of all review actions

### Priority System
- **Low Priority (1)**: Standard narrative responses
- **Medium Priority (2)**: Combat actions, skill checks
- **High Priority (3)**: Critical story moments, major decisions

## Database Models

### PendingResponse
Stores AI-generated responses awaiting review:
- `id`: Unique identifier
- `session_id`: Associated game session
- `user_id`: Player who triggered the response
- `context`: Original player input
- `ai_response`: Generated AI response
- `response_type`: Type of response (narrative, dice_roll, npc_action, etc.)
- `status`: Current status (pending, approved, rejected, edited)
- `dm_notes`: GM's comments
- `final_response`: Final approved/edited response
- `priority`: Priority level (1-3)
- `created_at`: Timestamp
- `reviewed_at`: Review completion timestamp

### DmNotification
Notifications for GMs about pending reviews:
- `id`: Unique identifier
- `session_id`: Associated game session
- `dm_user_id`: GM user ID
- `pending_response_id`: Related pending response
- `notification_type`: Type (new_review, urgent_review)
- `message`: Notification message
- `is_read`: Read status
- `created_at`: Timestamp

### ReviewHistory
Audit trail of GM review actions:
- `id`: Unique identifier
- `pending_response_id`: Related pending response
- `dm_user_id`: GM who performed the action
- `action`: Action taken (approved, rejected, edited)
- `original_response`: Original AI response
- `final_response`: Final response after review
- `notes`: GM notes
- `created_at`: Timestamp

## API Endpoints

### Session Management
- `POST /api/session` - Create new session
- `POST /api/session/{session_id}/join` - Join session

### DM Review Endpoints
- `GET /api/session/{session_id}/pending-responses` - Get pending responses (GM only)
- `POST /api/session/{session_id}/pending-response/{response_id}/review` - Review response
- `GET /api/session/{session_id}/dm/notifications` - Get DM notifications
- `POST /api/session/{session_id}/dm/notifications/{notification_id}/mark-read` - Mark notification as read
- `GET /api/session/{session_id}/player/{user_id}/approved-responses` - Get approved responses for player

### AI Integration
- `POST /api/session/{session_id}/llm-with-review` - Request AI response with review
- `GET /api/pending-response/{response_id}/status` - Check response status

## Frontend Components

### DmDashboard Component
A comprehensive React component providing:
- **Pending Reviews Tab**: List of responses awaiting review
- **Review Panel**: Interface for approving/editing/rejecting responses
- **Notifications Tab**: Unread notifications management
- **Priority Indicators**: Visual priority system
- **Real-time Updates**: Automatic refresh of pending items

### Console Integration
Enhanced ShadowrunConsole with:
- `/session create [name]` - Create new session as GM
- `/session join [id]` - Join existing session
- `/dm dashboard` - Open DM review dashboard (GM only)
- `/ai [message]` - Request AI response with review workflow

## Workflow

### Player Perspective
1. Player enters `/ai [message]` command
2. System generates AI response
3. Response is queued for DM review
4. Player receives confirmation with tracking ID
5. Player is notified when response is approved

### GM Perspective
1. GM receives notification of new review request
2. GM opens DM dashboard via `/dm dashboard`
3. GM reviews AI response and player context
4. GM can:
   - **Approve**: Accept AI response as-is
   - **Edit**: Modify response before approval
   - **Reject**: Decline response (player must try different approach)
5. GM adds optional notes for player
6. Response is delivered to player

## Testing

### Automated Testing
Run the test script to verify functionality:
```bash
cd /path/to/shadowrun-backend
python test_dm_review.py
```

### Manual Testing
1. Start the Flask backend: `python app.py`
2. Create a session: `POST /api/session`
3. Join as player: `POST /api/session/{id}/join`
4. Request AI response: `POST /api/session/{id}/llm-with-review`
5. Review as GM: Access pending responses and review

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for AI response generation
- `DEEPSEEK_API_KEY`: Alternative AI provider
- `ANTHROPIC_API_KEY`: Alternative AI provider

### Priority Thresholds
Configure in `llm_utils.py`:
- Combat actions: Priority 2
- Story-critical moments: Priority 3
- Standard narrative: Priority 1

## Security Considerations

### Access Control
- Only GMs can access review dashboard
- Only GMs can review responses
- Session-based permissions enforced
- User authentication via Clerk integration

### Data Protection
- All responses encrypted in transit
- Audit trail for compliance
- Configurable data retention policies

## Performance Optimization

### Caching Strategy
- Pending responses cached for quick access
- Notification polling optimized
- Database indexes on session_id and status

### Scalability
- Async AI response generation
- Background notification processing
- Horizontal scaling support

## Future Enhancements

### Planned Features
1. **Batch Review**: Review multiple responses simultaneously
2. **Auto-Approval Rules**: Configure automatic approval for certain response types
3. **Player Feedback**: Allow players to rate approved responses
4. **Analytics Dashboard**: GM insights into response patterns
5. **Integration with Slack**: Review responses directly in Slack
6. **Mobile Support**: Mobile-optimized review interface

### Integration Roadmap
1. **Phase 1**: DM Review System ✅ (Current)
2. **Phase 2**: Image Generation System
3. **Phase 3**: Slack Integration
4. **Phase 4**: Advanced Analytics

## Troubleshooting

### Common Issues
1. **Database Connection**: Ensure SQLite database is accessible
2. **AI API Keys**: Verify OpenAI API key is configured
3. **Session Management**: Check user authentication
4. **CORS Issues**: Verify frontend/backend communication

### Debug Mode
Enable debug logging in `app.py`:
```python
app.run(host="0.0.0.0", port=5000, debug=True)
```

### Monitoring
- Check Flask logs for API errors
- Monitor database for pending response buildup
- Track notification delivery success rates

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API endpoint documentation
3. Run the test script to verify functionality
4. Check database models for data consistency

---

*This system provides a robust foundation for AI-assisted Shadowrun gameplay while maintaining GM control over narrative quality and game balance.* 