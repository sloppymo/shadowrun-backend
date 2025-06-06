<<<<<<< HEAD
# Shadowrun Flask Backend

The backend API for the Shadowrun Multiplayer Engine. Provides session management, user roles, persistent chat memory, command routing, and real-time AI streaming for collaborative Shadowrun RPG sessions.

---

## Inhaltsverzeichnis / Table of Contents
- [Überblick / Overview](#überblick--overview)
- [Architektur / Architecture](#architektur--architecture)
- [Funktionen / Features](#funktionen--features)
- [Schnellstart / Quickstart](#schnellstart--quickstart)
- [API-Referenz / API Reference](#api-referenz--api-reference)
- [Session Memory & Streaming](#session-memory--streaming)
- [Erweiterbarkeit / Extensibility](#erweiterbarkeit--extensibility)
- [Fehlerbehebung / Troubleshooting](#fehlerbehebung--troubleshooting)
- [Roadmap](#roadmap)
- [Lizenz / License](#lizenz--license)

---

## Überblick / Overview

- **Python 3.13 Flask backend** for the Shadowrun Multiplayer Engine
- Provides RESTful API for session, user, and entity management
- Persistent chat memory per session/user/role
- Real-time streaming AI output (OpenAI, Mistral, etc.) via httpx
- SQLite storage, CORS enabled

---

## Architektur / Architecture

```
shadowrun-backend/
├── app.py            # Main Flask app
├── llm_utils.py      # Async OpenAI/LLM utilities
├── stream_proxy.py   # SSE proxy for frontend EventSource
├── .env              # Environment variables
├── requirements.txt  # Python dependencies
└── ...
```

---

## Funktionen / Features
- **Session Management:** Create, join, and list multiplayer sessions
- **User Roles:** Player, GM, Observer (with role-based permissions)
- **Command Routing:** API endpoints for specialized Shadowrun commands
- **Persistent Memory:** Chat history per session/user/role
- **Streaming:** Real-time AI output using SSE
- **CORS:** Enabled by default
- **Extensible:** Add new endpoints for Shadowrun-specific logic

---

## Schnellstart / Quickstart

### Voraussetzungen / Prerequisites
- Python 3.13+
- OpenAI API key (or other LLM provider)

### Installation & Start
```sh
pip install -r requirements.txt
cp .env.example .env  # Set your API key
python app.py
```

---

## API-Referenz / API Reference

- `POST /api/session` — Create a new session
- `POST /api/session/<session_id>/join` — Join a session
- `GET /api/session/<session_id>/users` — List users in a session
- `GET/POST /api/session/<session_id>/scene` — Manage scene summaries
- `GET/POST /api/session/<session_id>/entities` — Entity tracker
- `POST /api/chat` — AI chat (session memory, streaming)
- `GET /api/chat/stream-proxy` — SSE proxy for frontend
- `GET /api/ping` — Health check

See [shadowrun-interface/README.md](../shadowrun-interface/README.md) for frontend usage.

---

## Session Memory & Streaming
- **ChatMemory** table stores message history for each session/user/role
- AI responses use full session context
- Streaming output via Server-Sent Events (SSE)

---

## Erweiterbarkeit / Extensibility
- Add new Flask endpoints for custom Shadowrun logic
- Integrate additional LLM providers in `llm_utils.py`
- Extend database models as needed

---

## Fehlerbehebung / Troubleshooting
- **CORS:** Ensure frontend and backend are on correct ports
- **API Keys:** Set your OpenAI key in `.env`
- **Streaming:** If streaming fails, check `/api/chat/stream-proxy` and backend logs
- **DB:** Delete `shadowrun.db` to reset sessions (dev only)

---

## Roadmap
- Advanced dice roll logic (Shadowrun glitches)
- GM override panel for AI output
- Clerk authentication integration
- More RPG command endpoints

---

## Lizenz / License
MIT License. Shadowrun is a registered trademark of Catalyst Game Labs. This project is a fan work and not affiliated with or endorsed by the copyright holders.

---

# Shadowrun Flask Backend (Deutsch)

Das Backend-API für die Shadowrun Multiplayer Engine. Bietet Sitzungsverwaltung, Benutzerrollen, persistente Chat-Speicherung, Kommando-Routing und Echtzeit-AI-Streaming für kollaborative Shadowrun-RPG-Sitzungen.

## Architektur
- Python 3.13 Flask Backend
- RESTful API für Sitzungen, Benutzer und Entitäten
- Persistente Chat-Speicherung pro Sitzung/Benutzer/Rolle
- Echtzeit-Streaming von KI-Ausgaben (OpenAI, Mistral, etc.) via httpx
- SQLite-Speicherung, CORS aktiviert

## Funktionen
- Sitzungsverwaltung: Erstellen, Beitreten, Auflisten von Multiplayer-Sitzungen
- Benutzerrollen: Spieler, GM, Beobachter (mit rollenbasierten Berechtigungen)
- Kommando-Routing: API-Endpunkte für Shadowrun-spezifische Kommandos
- Persistente Speicherung: Chatverlauf pro Sitzung/Benutzer/Rolle
- Streaming: Echtzeit-KI-Ausgabe via SSE
- CORS: Standardmäßig aktiviert
- Erweiterbar: Neue Endpunkte für Shadowrun-Logik hinzufügen

## Schnellstart
1. Python 3.13+ installieren
2. Abhängigkeiten installieren: `pip install -r requirements.txt`
3. `.env.example` kopieren und API-Key setzen
4. Backend starten: `python app.py`

## API-Endpunkte
- `POST /api/session` — Neue Sitzung erstellen
- `POST /api/session/<session_id>/join` — Sitzung beitreten
- `GET /api/session/<session_id>/users` — Benutzer in Sitzung auflisten
- `GET/POST /api/session/<session_id>/scene` — Szenenzusammenfassung verwalten
- `GET/POST /api/session/<session_id>/entities` — Entitäten-Tracker
- `POST /api/chat` — AI-Chat (Sitzungsspeicher, Streaming)
- `GET /api/chat/stream-proxy` — SSE-Proxy für Frontend
- `GET /api/ping` — Health Check

## Fehlerbehebung
- CORS-Probleme: Ports prüfen
- API-Key: In `.env` setzen
- Streaming-Probleme: `/api/chat/stream-proxy` und Backend-Logs prüfen
- Datenbank: `shadowrun.db` löschen, um Sitzungen zurückzusetzen (nur Entwicklung)

## Roadmap
- Erweiterte Würfellogik (Shadowrun Glitches)
- GM-Override-Panel für KI-Ausgaben
- Clerk-Authentifizierung
- Weitere RPG-Kommando-Endpunkte

## Lizenz
MIT License. Shadowrun ist ein eingetragenes Warenzeichen von Catalyst Game Labs. Dieses Projekt ist ein Fanprojekt und steht in keiner Verbindung zu den Rechteinhabern.
=======
# shadowrun-backend
Flask-based API service powering the Shadowrun character creation system. Features include character data management, rule enforcement, skill calculation, equipment tracking, and spell systems. Implements comprehensive 6th Edition ruleset with SQLite persistence and RESTful endpoints for seamless frontend integration.
>>>>>>> 00baf9f313d4d30d8c4c8d5b5bdbd95b89a317f3
