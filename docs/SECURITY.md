# Security Policy and Best Practices

This document outlines security considerations, best practices, and policies for the Shadowrun RPG System. Following these guidelines will help maintain the security and integrity of the application.

## Table of Contents
- [Environment Variables and API Keys](#environment-variables-and-api-keys)
- [Authentication and Authorization](#authentication-and-authorization)
- [API Security](#api-security)
- [Rate Limiting and Quotas](#rate-limiting-and-quotas)
- [Input Validation](#input-validation)
- [Content Security](#content-security)
- [Dependency Management](#dependency-management)
- [Reporting Security Issues](#reporting-security-issues)

## Environment Variables and API Keys

### Storage
- **NEVER commit API keys, tokens, or sensitive credentials to the repository**
- Store all sensitive values in `.env` files which are excluded via `.gitignore`
- For production, use secure environment variable management via your hosting provider

### Required Keys
The application requires these API keys/tokens:
- `OPENAI_API_KEY` - For LLM functionality and DALL-E image generation
- `CLERK_API_KEY` - For authentication (frontend)
- `DATABASE_URL` - For database connection (if not using SQLite default)

### Recommended Key Management
- Rotate keys periodically (every 30-90 days)
- Use separate API keys for development and production
- Implement the principle of least privilege (minimum necessary permissions)

## Authentication and Authorization

### Authentication
- Frontend authentication is handled via Clerk
- Backend API routes requiring authentication should validate tokens

### Role-Based Access Control
- Implement and enforce these roles:
  - **Player**: Access to own character and shared session data
  - **Game Master (DM)**: Full access to session data, NPC creation, and approval workflows
  - **Observer**: Read-only access to session data
  - **Admin**: System administration capabilities

### Implementation Guidelines
- Validate user roles on every privileged request
- Enforce object-level permissions (e.g., players can only modify their own characters)
- Use middleware to consistently apply authentication checks

## API Security

### General Guidelines
- Use HTTPS for all API communications
- Implement proper CORS settings to allow only intended origins
- Apply the principle of least privilege for all endpoints

### Endpoint Security
- Public endpoints: Minimal access, rate limited
- Player endpoints: Require authenticated user with valid session association
- DM endpoints: Require authenticated user with DM role for the requested session
- Admin endpoints: Require admin role

## Rate Limiting and Quotas

### Implementation
- Rate limit all API endpoints (especially those using external APIs)
- Apply stricter limits to authentication endpoints to prevent brute force attacks
- Monitor and alert on unusual traffic patterns

### AI Service Quotas
- Implement token counting for LLM requests to prevent resource exhaustion
- Set reasonable image generation limits per user/session
- Cache results where appropriate to reduce API calls

## Input Validation

### General Rules
- Validate all user inputs server-side
- Use parameterized queries to prevent SQL injection 
- Sanitize inputs used in dynamic queries

### Special Considerations
- Sanitize prompts sent to LLM services
- Validate and sanitize image generation prompts to prevent abuse
- Implement context-appropriate validation for game data

## Content Security

### User-Generated Content
- Validate and sanitize all user-generated content
- Implement moderation for AI-generated content
- Store user content securely with appropriate access controls

### Image Generation
- Implement keyword filtering for DALL-E prompts
- Review generated images in DM workflow before showing to players
- Honor copyright and fair use considerations

## Dependency Management

### Best Practices
- Regularly update dependencies to patch security vulnerabilities
- Use tools like `pip-audit` and `npm audit` to scan for known vulnerabilities
- Pin dependency versions for predictable builds

### Workflow Integration
- Add security scanning to CI/CD pipeline
- Automate dependency updates with security reviews

## Reporting Security Issues

If you discover a security vulnerability within the Shadowrun RPG System:

1. **DO NOT** disclose the issue publicly
2. Send a detailed report to [security@example.com](mailto:security@example.com)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

We will acknowledge receipt of your report within 48 hours and provide an estimated timeline for a fix. We appreciate your help in keeping the project secure!

---

## Compliance Checklist

Use this checklist to verify security compliance before deployment:

- [ ] All API keys and secrets stored securely in environment variables
- [ ] Authentication and authorization implemented for all endpoints
- [ ] Input validation applied to all user inputs
- [ ] Rate limiting configured for APIs and external service calls
- [ ] CORS properly configured
- [ ] Dependencies updated and scanned for vulnerabilities
- [ ] Error handling implemented to avoid information disclosure
- [ ] Logging configured without sensitive data
- [ ] Secure HTTPS communication enforced
