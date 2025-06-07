# Shadowrun RPG Backend

A modular, AI-powered backend for running immersive Shadowrun 6E tabletop campaigns. This system supports dynamic NPC and encounter generation, real-time AI Game Mastering, DM review workflows, cyberpunk-themed player interfaces, and more.

---

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [API Reference](#api-reference)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Development Workflow](#development-workflow)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [Project Roadmap & Checklist](#project-roadmap--checklist)
- [Extensibility](#extensibility)
- [Security](#security)
- [License](#license)
- [Credits](#credits)

---

## Overview

Shadowrun Backend is a Python Flask API designed to power the Shadowrun character creation system and multiplayer engine. It provides a robust set of features to support character data management, rules enforcement, skill/equipment/magic systems, session management, real-time AI integration, and extensible endpoints for advanced gameplay.

---

## Architecture

```
shadowrun-backend/
├── app.py            # Main Flask app
├── character/        # Character creation modules
├── llm_utils.py      # Async OpenAI/LLM utilities
├── stream_proxy.py   # SSE proxy for EventSource
├── docs/             # Design docs, roadmap, QA, system guides
├── requirements.txt  # Python dependencies
├── .env              # Environment variables
└── ...
```

- **Backend**: Flask (Python), SQLAlchemy ORM, SQLite (default), Celery for async tasks
- **Frontend**: Next.js, React, Clerk authentication, Tailwind CSS (see companion repo)
- **AI/LLM**: OpenAI, DALL-E, Anthropic, Mistral, OpenRouter (configurable)
- **Image Generation**: DALL-E API (default, pluggable)
- **Async Queue**: Celery + Redis/RabbitMQ
- **Storage**: Local, S3, or CDN for image assets
- **Authentication**: Clerk (frontend), role-based access for DM features

---

## Features

### Character Creation
- Enforces Shadowrun 6E rules
- Skill, equipment, and magic systems
- Validates character sheets

### Multiplayer & Session Management
- Session creation/join/listing
- Player, GM, Observer roles
- Command routing for Shadowrun commands
- Persistent chat memory
- Real-time AI output (SSE)
- Extensible endpoints

### DM Review System
- Queue and approve AI-generated responses before they reach players
- DM Dashboard for review, editing, and workflow management
- Priority-based queue, notifications, and context panels

### NPC Generation
- Weighted randomization and archetype templates for diverse, lore-friendly NPCs
- Narrative hooks, personality traits, and dynamic equipment

### Combat System
- Initiative, turn management, attack resolution, and environment effects
- API endpoints for combat actions and special maneuvers

### Real-Time Image Generation
- DALL-E-powered scene, NPC, and item art
- Async job queue, storage, and frontend integration

### Testing & QA
- Comprehensive unit, integration, and performance test suites
- Automated CI/CD pipeline (see `.github/workflows/test.yml`)

### Extensibility
- Modular endpoints, LLM provider abstraction, and easy integration of new features

---

## API Reference

### Character Creation
- `GET /api/data/metatypes` — List metatypes
- `GET /api/data/skills` — List skills
- `POST /api/character/validate` — Validate character sheet
- `POST /api/character/save` — Save character

### Multiplayer
- `POST /api/session` — Create session
- `POST /api/session/<session_id>/join` — Join session
- `GET /api/session/<session_id>/users` — List users
- `GET/POST /api/session/<session_id>/scene` — Manage scene
- `GET/POST /api/session/<session_id>/entities` — Entity tracker
- `POST /api/chat` — AI chat
- `GET /api/chat/stream-proxy` — SSE proxy
- `GET /api/ping` — Health check

### DM Review System
- `POST /api/dm/review/queue` — Enqueue AI responses for DM review
- `GET /api/dm/review/queue` — Fetch pending reviews
- `POST /api/dm/review/<review_id>/approve` — Approve a response
- `POST /api/dm/review/<review_id>/reject` — Reject a response

### NPC Generation
- `POST /api/npc/generate` — Generate an NPC dynamically

### Combat
- `POST /api/combat/start` — Initiate combat
- `POST /api/combat/next_turn` — Advance to next turn
- `POST /api/combat/attack` — Resolve attack

### Real-Time Image Generation
- `POST /api/image/generate` — Request image generation
- `GET /api/image/status/<job_id>` — Check image job status
- `GET /api/image/<image_id>` — Retrieve generated image

---

## Setup & Installation

### Prerequisites
- Python 3.8+
- OpenAI API key (for AI features)

### Installation & Start
```sh
pip install -r requirements.txt
cp .env.example .env  # Set your API key(s) and other environment variables
python app.py
```

### Database Migration
```sh
flask db upgrade
```

### Celery Worker (for async tasks)
```sh
celery -A app.celery worker --loglevel=info
```

---

## Configuration

- All major providers and feature toggles are controlled via environment variables.
- See `.env.example` for required and optional variables.
- See `docs/roadmap.md` for implementation phases and checklist.
- See `docs/testing_and_qa.md` for testing setup and best practices.

---

## Development Workflow

1. **Follow the Roadmap:**  Work through `docs/roadmap.md`, checking off tasks as you go.
2. **Branching:**  Use feature branches for new endpoints, models, or major features.
3. **Testing:**  Run unit and integration tests before submitting PRs.
4. **Documentation:**  Update or create relevant docs in `docs/` for all new features.

---

## Testing & Quality Assurance

- Run all tests with:
  ```sh
  pytest
  ```
- See `docs/testing_and_qa.md` for detailed test plans and QA protocols.
- Automated CI/CD pipeline is defined in `.github/workflows/test.yml`.

---

## Project Roadmap & Checklist

- See `docs/roadmap.md` for a living, detailed checklist of all phases, tasks, and progress.
- Check off items as you complete them!

---

## Extensibility

- Add Flask endpoints for custom logic
- Integrate new LLM providers in `llm_utils.py`
- Extend database models
- Add new character modules
- Modularize prompt construction and AI integrations
- Plug in new image or AI providers easily

---

## Security

- API keys and secrets should NEVER be committed—use `.env`.
- Role-based access for DM and player endpoints.
- Rate limiting and quota controls for AI/image APIs.
- See docs for security best practices.

---

## License

MIT License. See [LICENSE](LICENSE).

---

## Credits

- Shadowrun® is a registered trademark of Catalyst Game Labs.  
- This project is a fan-made, non-commercial toolkit for tabletop RPG facilitation.
- Thanks to the open-source and AI communities for foundational tools and inspiration.

---

If you have any questions, suggestions, or want to contribute, please open an issue or contact the maintainer!
