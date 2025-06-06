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
