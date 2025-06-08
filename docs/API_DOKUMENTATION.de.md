# Shadowrun Backend - API-Dokumentation

## Überblick

Diese API-Dokumentation beschreibt alle verfügbaren REST-Endpunkte des Shadowrun Backend-Systems. Die API folgt RESTful-Prinzipien und verwendet JSON für Datenübertragung.

**Basis-URL:** `http://localhost:5000/api`

## Authentifizierung

### Session-basierte Authentifizierung

Die meisten Endpunkte erfordern eine gültige Session-ID und Benutzer-ID. Diese werden als URL-Parameter oder im Request-Body übertragen.

```http
POST /api/session/{session_id}/endpoint
Content-Type: application/json

{
  "user_id": "your-user-id",
  "data": {...}
}
```

### Rollen-System

- **Player (Spieler):** Grundlegende Spielfunktionen
- **GM (Spielleiter):** Vollzugriff auf Sitzungsverwaltung
- **Observer (Beobachter):** Nur Lesezugriff

## Sitzungsverwaltung

### Sitzung erstellen

Erstellt eine neue Multiplayer-Sitzung.

**Endpunkt:** `POST /api/session`

**Request:**
```json
{
  "name": "Meine Shadowrun-Kampagne",
  "gm_user_id": "gm-user-123"
}
```

**Response:**
```json
{
  "session_id": "uuid-12345",
  "name": "Meine Shadowrun-Kampagne",
  "gm_user_id": "gm-user-123"
}
```

**Status Codes:**
- `201 Created` - Sitzung erfolgreich erstellt
- `400 Bad Request` - Fehlende oder ungültige Parameter

### Sitzung beitreten

Fügt einen Benutzer zu einer bestehenden Sitzung hinzu.

**Endpunkt:** `POST /api/session/{session_id}/join`

**Request:**
```json
{
  "user_id": "player-456",
  "role": "player"
}
```

**Response:**
```json
{
  "session_id": "uuid-12345",
  "user_id": "player-456",
  "role": "player"
}
```

### Sitzungsbenutzer auflisten

Listet alle Benutzer in einer Sitzung auf.

**Endpunkt:** `GET /api/session/{session_id}/users`

**Response:**
```json
[
  {
    "user_id": "gm-user-123",
    "role": "gm"
  },
  {
    "user_id": "player-456",
    "role": "player"
  }
]
```

## Charakterverwaltung

### Alle Charaktere abrufen

Ruft alle Charaktere einer Sitzung ab.

**Endpunkt:** `GET /api/session/{session_id}/characters`

**Response:**
```json
[
  {
    "id": 1,
    "user_id": "player-456",
    "name": "Marcus Chen",
    "handle": "Wire",
    "archetype": "Decker",
    "attributes": "{\"body\": 3, \"agility\": 5, \"reaction\": 4, \"strength\": 2, \"willpower\": 5, \"logic\": 6, \"intuition\": 5, \"charisma\": 3, \"edge\": 3}",
    "skills": "{\"computer\": 6, \"hacking\": 5, \"electronics\": 4}",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

### Charakter erstellen

Erstellt einen neuen Charakter in der Sitzung.

**Endpunkt:** `POST /api/session/{session_id}/character`

**Request:**
```json
{
  "user_id": "player-456",
  "name": "Marcus Chen",
  "handle": "Wire",
  "archetype": "Decker",
  "background_seed": "Ehemaliger Konzern-Decker",
  "gender": "männlich",
  "pronouns": "er/ihm",
  "essence_anchor": "Familie schützen",
  "build_method": "priority",
  "attributes": "{\"body\": 3, \"agility\": 5, \"reaction\": 4, \"strength\": 2, \"willpower\": 5, \"logic\": 6, \"intuition\": 5, \"charisma\": 3, \"edge\": 3}",
  "skills": "{\"computer\": 6, \"hacking\": 5, \"electronics\": 4}",
  "qualities": "{\"positive\": [\"Codeknacker\"], \"negative\": [\"SINlos\"]}",
  "gear": "[{\"name\": \"Cyberdeck\", \"rating\": 6}]"
}
```

**Response:**
```json
{
  "status": "success",
  "character_id": 1
}
```

### Charakter aktualisieren

Aktualisiert einen bestehenden Charakter.

**Endpunkt:** `PUT /api/session/{session_id}/character/{character_id}`

**Request:**
```json
{
  "name": "Marcus 'Wire' Chen",
  "skills": "{\"computer\": 7, \"hacking\": 6, \"electronics\": 4}"
}
```

**Response:**
```json
{
  "status": "success"
}
```

### Charakter löschen

Löscht einen Charakter permanent.

**Endpunkt:** `DELETE /api/session/{session_id}/character/{character_id}`

**Response:**
```json
{
  "status": "deleted"
}
```

## Szenenverwaltung

### Aktuelle Szene abrufen

Ruft die aktuelle Szenenbeschreibung ab.

**Endpunkt:** `GET /api/session/{session_id}/scene`

**Response:**
```json
{
  "session_id": "uuid-12345",
  "summary": "Die Gruppe befindet sich im unterirdischen Markt von Seattle. Neonlichter flackern und der Geruch von Straßenküche liegt in der Luft. Konzern-Sicherheit patrouilliert durch die oberen Ebenen."
}
```

### Szene aktualisieren

Aktualisiert die Szenenbeschreibung (nur GM).

**Endpunkt:** `POST /api/session/{session_id}/scene`

**Request:**
```json
{
  "user_id": "gm-user-123",
  "summary": "Die Runners erreichen das Ares-Gebäude. Hochgeschwindigkeits-Sicherheitsdrohen schwirren um die Spitze des 80-stöckigen Turms."
}
```

**Response:**
```json
{
  "session_id": "uuid-12345",
  "summary": "Die Runners erreichen das Ares-Gebäude..."
}
```

## Entitätenverwaltung

### Entitäten auflisten

Listet alle NPCs, Geister, Drohnen etc. in der Sitzung auf.

**Endpunkt:** `GET /api/session/{session_id}/entities`

**Response:**
```json
[
  {
    "id": 1,
    "name": "Konzern-Wache",
    "type": "npc",
    "status": "alarmiert",
    "extra_data": "{\"initiative\": 12, \"damage\": 0}"
  },
  {
    "id": 2,
    "name": "Sicherheitsdrohne",
    "type": "drone",
    "status": "patrol",
    "extra_data": "{\"sensor_rating\": 4}"
  }
]
```

### Entität hinzufügen/aktualisieren

Erstellt oder aktualisiert eine Entität (nur GM).

**Endpunkt:** `POST /api/session/{session_id}/entities`

**Request:**
```json
{
  "user_id": "gm-user-123",
  "name": "Mr. Johnson",
  "type": "npc",
  "status": "neutral",
  "extra_data": "{\"corporation\": \"Ares\", \"credibility\": 7}"
}
```

**Response:**
```json
{
  "id": 3,
  "name": "Mr. Johnson",
  "type": "npc",
  "status": "neutral",
  "extra_data": "{\"corporation\": \"Ares\", \"credibility\": 7}"
}
```

## GM Review-System

### Wartende Reviews abrufen

Ruft alle ausstehenden KI-Antworten zur GM-Freigabe ab (nur GM).

**Endpunkt:** `GET /api/session/{session_id}/pending-responses?user_id={gm_user_id}`

**Response:**
```json
[
  {
    "id": "response-uuid-123",
    "user_id": "player-456",
    "context": "Ich versuche, das Sicherheitssystem zu hacken",
    "ai_response": "Das Datenterminal zeigt eine Orange-ICE-Warnung. Dein Cyberdeck erkennt einen Trace-Algorithmus, der sich nähert...",
    "response_type": "matrix",
    "priority": 3,
    "created_at": "2024-01-15T14:22:00Z"
  }
]
```

### Response reviewen

Genehmigt, lehnt ab oder bearbeitet eine KI-Antwort (nur GM).

**Endpunkt:** `POST /api/session/{session_id}/pending-response/{response_id}/review`

**Request:**
```json
{
  "user_id": "gm-user-123",
  "action": "edit",
  "final_response": "Das Datenterminal zeigt eine Rot-ICE-Warnung! Dein Cyberdeck registriert einen aggressiven Trace-Algorithmus...",
  "dm_notes": "Erhöhte Schwierigkeit für dramatischen Effekt"
}
```

**Response:**
```json
{
  "status": "success",
  "action": "edit"
}
```

**Mögliche Actions:**
- `approve` - Antwort genehmigen
- `reject` - Antwort ablehnen
- `edit` - Antwort bearbeiten

## KI-Integration

### Direkte LLM-Anfrage

Sendet eine Anfrage direkt an die KI.

**Endpunkt:** `POST /api/llm`

**Request:**
```json
{
  "session_id": "uuid-12345",
  "user_id": "player-456",
  "input": "Ich schaue mich im Markt nach Kontakten um",
  "model": "openai",
  "model_name": "gpt-4"
}
```

**Response:** Server-Sent Events (SSE) Stream

```
data: {"speaker": "AI", "content": "Du bemerkst einen"}
data: {"speaker": "AI", "content": " bekannten Informationshändler"}
data: {"speaker": "AI", "content": " an einem der Stände..."}
```

### LLM mit GM-Review

Sendet KI-Anfrage zur GM-Überprüfung.

**Endpunkt:** `POST /api/session/{session_id}/llm-with-review`

**Request:**
```json
{
  "user_id": "player-456",
  "context": "Ich versuche, in das Konzernnetzwerk einzudringen",
  "response_type": "matrix",
  "priority": 3,
  "require_review": true
}
```

**Response:**
```json
{
  "status": "pending_review",
  "response_id": "response-uuid-456",
  "message": "Antwort zur GM-Überprüfung eingereicht"
}
```

## Bildgenerierung

### Sofortige Bildgenerierung

Generiert ein Bild sofort mit DALL-E.

**Endpunkt:** `POST /api/session/{session_id}/generate-image-instant`

**Request:**
```json
{
  "user_id": "gm-user-123",
  "prompt": "Neon-beleuchteter Straßenmarkt in cyberpunk Seattle bei Nacht",
  "provider": "dalle",
  "style_preferences": {
    "style": "cyberpunk noir"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "image_id": "img-uuid-789",
  "image_url": "https://storage.com/generated-image.jpg",
  "generation_time": 8.2,
  "provider": "dalle"
}
```

### Sitzungsbilder abrufen

Ruft alle generierten Bilder einer Sitzung ab.

**Endpunkt:** `GET /api/session/{session_id}/images?limit=20`

**Response:**
```json
{
  "status": "success",
  "images": [
    {
      "id": "img-uuid-789",
      "prompt": "Neon-beleuchteter Straßenmarkt",
      "image_url": "https://storage.com/generated-image.jpg",
      "provider": "dalle",
      "status": "completed",
      "created_at": "2024-01-15T15:30:00Z",
      "is_favorite": false,
      "tags": ["market", "neon", "cyberpunk"]
    }
  ],
  "count": 1
}
```

## Kampfmanagement

### Kampfstatus abrufen

Ruft den aktuellen Kampfstatus ab.

**Endpunkt:** `GET /api/session/{session_id}/combat/status`

**Response:**
```json
{
  "combat": {
    "id": "combat-uuid-123",
    "name": "Konzern-Überfall",
    "status": "active",
    "current_round": 3
  },
  "combatants": [
    {
      "id": "combatant-1",
      "name": "Marcus 'Wire' Chen",
      "type": "player",
      "initiative": 15,
      "physical_damage": 2,
      "stun_damage": 0,
      "status": "active",
      "edge": 3,
      "current_edge": 2
    }
  ],
  "round": 3,
  "activeIndex": 0
}
```

## Matrix-System

### Matrix-Grid abrufen

Ruft das aktuelle Matrix-Grid ab.

**Endpunkt:** `GET /api/session/{session_id}/matrix/grid`

**Response:**
```json
{
  "grid": {
    "id": "grid-uuid-456",
    "name": "Ares Mainframe",
    "security_rating": 8,
    "noise_level": 2
  },
  "nodes": [
    {
      "id": "node-1",
      "name": "Firewall",
      "node_type": "ice",
      "security": 6,
      "position_x": 0,
      "position_y": 0,
      "discovered": true,
      "compromised": false
    }
  ],
  "ice": [
    {
      "id": "ice-1",
      "name": "Killer ICE",
      "ice_type": "killer",
      "rating": 6,
      "status": "active"
    }
  ],
  "overwatch": 15
}
```

## Charakterbogen-Integration

### Charakterbögen entdecken

Findet Charakterbögen in Google Docs oder Slack.

**Endpunkt:** `GET /api/session/{session_id}/character-sheets/discover?user_id={user_id}`

**Response:**
```json
{
  "status": "success",
  "session_id": "uuid-12345",
  "discovered_sheets": {
    "google_docs": [
      {
        "document_id": "1A2B3C4D5E",
        "title": "Marcus Chen - Shadowrun Charakter",
        "last_modified": "2024-01-15T12:00:00Z"
      }
    ],
    "slack": [
      {
        "channel_id": "C1234567",
        "message_ts": "1705320000.123456",
        "user_id": "U7890123",
        "preview": "**Marcus Chen** - Decker\nKörper: 3, Geschicklichkeit: 5..."
      }
    ]
  }
}
```

### Charakterbogen importieren

Importiert einen Charakterbogen aus externer Quelle.

**Endpunkt:** `POST /api/session/{session_id}/character-sheets/import`

**Request:**
```json
{
  "user_id": "player-456",
  "source_type": "google_docs",
  "source_reference": {
    "document_id": "1A2B3C4D5E"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "character_id": 5,
  "import_summary": {
    "attributes_imported": 8,
    "skills_imported": 15,
    "gear_imported": 12,
    "source": "google_docs"
  }
}
```

## Slack-Integration

### Slack-Kommando verarbeiten

Verarbeitet Slash-Kommandos aus Slack.

**Endpunkt:** `POST /api/slack/command`

**Request:** (Slack-Format)
```json
{
  "command": "/sr-session",
  "text": "create My Campaign",
  "user_id": "U12345",
  "channel_id": "C67890",
  "team_id": "T54321"
}
```

**Response:**
```json
{
  "response_type": "ephemeral",
  "text": "Sitzung 'My Campaign' erstellt! Session ID: uuid-12345"
}
```

## Fehlercodes

Die API verwendet standard HTTP-Status-Codes:

| Code | Bedeutung | Beschreibung |
|------|-----------|--------------|
| 200 | OK | Anfrage erfolgreich |
| 201 | Created | Ressource erstellt |
| 400 | Bad Request | Ungültige Anfrage |
| 401 | Unauthorized | Authentifizierung erforderlich |
| 403 | Forbidden | Zugriff verweigert |
| 404 | Not Found | Ressource nicht gefunden |
| 500 | Internal Server Error | Serverfehler |

### Fehler-Format

```json
{
  "error": "Beschreibung des Fehlers",
  "type": "validation_error",
  "details": {
    "field": "user_id",
    "message": "user_id ist erforderlich"
  }
}
```

## Rate Limiting

Die API implementiert Rate Limiting um Missbrauch zu verhindern:

- **Allgemeine Endpunkte:** 100 Anfragen/Minute
- **KI-Endpunkte:** 20 Anfragen/Minute  
- **Bildgenerierung:** 5 Anfragen/Minute

Rate Limit-Header:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705324800
```

## WebSocket-Verbindungen

Für Echtzeit-Updates verwenden Sie WebSocket-Verbindungen:

**Endpunkt:** `ws://localhost:5000/ws/session/{session_id}`

**Nachrichten-Format:**
```json
{
  "type": "scene_update",
  "data": {
    "summary": "Neue Szenenbeschreibung..."
  },
  "timestamp": "2024-01-15T16:00:00Z"
}
```

## SDK und Client-Bibliotheken

### Python SDK

```python
from shadowrun_client import ShadowrunClient

client = ShadowrunClient(base_url="http://localhost:5000/api")

# Sitzung erstellen
session = client.create_session("Meine Kampagne", "gm-user-123")

# Charakter erstellen
character = client.create_character(
    session_id=session.id,
    user_id="player-456",
    name="Marcus Chen",
    archetype="Decker"
)
```

### JavaScript/TypeScript SDK

```typescript
import { ShadowrunClient } from 'shadowrun-client';

const client = new ShadowrunClient('http://localhost:5000/api');

// Sitzung erstellen
const session = await client.createSession('Meine Kampagne', 'gm-user-123');

// KI-Anfrage mit Review
const response = await client.llmWithReview(session.id, {
  userId: 'player-456',
  context: 'Ich hacke das System',
  responseType: 'matrix',
  priority: 3
});
```

## Entwicklung und Testing

### Lokale API testen

```bash
# Health Check
curl http://localhost:5000/api/ping

# Sitzung erstellen
curl -X POST http://localhost:5000/api/session \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Session", "gm_user_id": "test-gm"}'

# Charaktere abrufen
curl http://localhost:5000/api/session/{session_id}/characters
```

### Postman Collection

Eine vollständige Postman-Collection mit allen Endpunkten ist verfügbar unter:
`docs/Shadowrun_API.postman_collection.json`

## Versionierung

Die API folgt semantischer Versionierung (SemVer):
- **Major:** Breaking Changes
- **Minor:** Neue Features (rückwärtskompatibel)
- **Patch:** Bugfixes

Aktuelle Version: `v2.0.0`

API-Versionierung über Header:
```http
Accept: application/vnd.shadowrun.v2+json
``` 