# Shadowrun Backend

A Python Flask API powering the Shadowrun character creation system and multiplayer engine. Supports character data management, rules enforcement, skill/equipment/magic systems, session management, and real-time AI integration. Implements Shadowrun 6E rules with SQLite persistence and RESTful endpoints.

---

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [API Reference](#api-reference)
- [Setup](#setup)
- [Extensibility](#extensibility)
- [License](#license)

---

## Overview

Shadowrun Backend is a Python Flask API designed to power the Shadowrun character creation system and multiplayer engine. It provides a robust set of features to support character data management, rules enforcement, skill/equipment/magic systems, session management, and real-time AI integration.

---

## Architecture

```
shadowrun-backend/
├── app.py            # Main Flask app
├── character/        # Character creation modules
├── llm_utils.py      # Async OpenAI/LLM utilities
├── stream_proxy.py   # SSE proxy for EventSource
├── .env              # Environment variables
├── requirements.txt  # Python dependencies
└── ...
```

---

## Features

### Character Creation
- Enforces Shadowrun 6E rules
- Skill, equipment, and magic systems
- Validates character sheets

### Multiplayer
- Session management (create/join/list)
- Player, GM, Observer roles
- Command routing for Shadowrun commands
- Persistent chat memory
- Real-time AI output (SSE)
- Extensible endpoints

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

---

## Setup

### Prerequisites
- Python 3.8+
- OpenAI API key (for AI features)

### Installation & Start
```sh
pip install -r requirements.txt
cp .env.example .env  # Set your API key
python app.py
```

---

## Extensibility

- Add Flask endpoints for custom logic
- Integrate new LLM providers in `llm_utils.py`
- Extend database models
- Add new character modules

---

## License

MIT License. Shadowrun is a trademark of Catalyst Game Labs. This project is a fan work and not affiliated with or endorsed by the copyright holders.
