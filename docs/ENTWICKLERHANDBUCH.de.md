# Shadowrun Backend - Entwicklerhandbuch

## Überblick

Dieses Handbuch richtet sich an Entwickler, die am Shadowrun Backend-System arbeiten möchten. Es behandelt Architektur, Code-Organisation, Entwicklungsworkflow und Best Practices.

## Projektarchitektur

### High-Level-Übersicht

```
shadowrun-backend/
├── app.py                      # Haupt-Flask-Anwendung
├── models/                     # SQLAlchemy-Datenmodelle
├── routes/                     # API-Route-Handler
├── services/                   # Business-Logic-Services
├── utils/                      # Hilfsfunktionen
├── middleware/                 # Request/Response-Middleware
├── integrations/               # Externe Integrationen (Slack, Google Docs)
├── tests/                      # Test-Suite
├── docs/                       # Dokumentation
└── requirements.txt           # Python-Abhängigkeiten
```

### Datenmodelle

#### Kern-Entitäten

```python
# Session - Multiplayer-Sitzung
class Session(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    gm_user_id = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

# Character - Shadowrun 6E Charakterbogen
class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, db.ForeignKey('session.id'))
    user_id = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    handle = db.Column(db.String, nullable=True)
    archetype = db.Column(db.String, nullable=True)
    # ... weitere SR6E-spezifische Felder

# Combat - Kampf-Management
class Combat(db.Model):
    id = db.Column(db.String, primary_key=True)
    session_id = db.Column(db.String, db.ForeignKey('session.id'))
    status = db.Column(db.String, default='setup')
    current_round = db.Column(db.Integer, default=1)
    active_combatant_index = db.Column(db.Integer, default=0)
```

#### Review-System

```python
# PendingResponse - KI-Antworten zur GM-Freigabe
class PendingResponse(db.Model):
    id = db.Column(db.String, primary_key=True)
    session_id = db.Column(db.String, db.ForeignKey('session.id'))
    user_id = db.Column(db.String, nullable=False)
    ai_response = db.Column(db.Text, nullable=False)
    status = db.Column(db.String, default='pending')
    priority = db.Column(db.Integer, default=1)

# ReviewHistory - Audit-Trail für GM-Entscheidungen
class ReviewHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pending_response_id = db.Column(db.String, db.ForeignKey('pending_response.id'))
    action = db.Column(db.String, nullable=False)
    dm_notes = db.Column(db.Text, nullable=True)
```

### API-Struktur

#### RESTful-Endpunkte

```python
# Sitzungsverwaltung
POST   /api/session                    # Neue Sitzung erstellen
POST   /api/session/<id>/join          # Sitzung beitreten
GET    /api/session/<id>/users         # Benutzer auflisten

# Charaktermanagement
GET    /api/session/<id>/characters    # Alle Charaktere
POST   /api/session/<id>/character     # Charakter erstellen
PUT    /api/session/<id>/character/<char_id>  # Charakter aktualisieren
DELETE /api/session/<id>/character/<char_id>  # Charakter löschen

# Kampfmanagement
GET    /api/session/<id>/combat/status # Kampfstatus
POST   /api/session/<id>/combat/start  # Kampf beginnen
POST   /api/session/<id>/combat/action # Kampfaktion ausführen

# Matrix-System
GET    /api/session/<id>/matrix/grid   # Matrix-Grid
POST   /api/session/<id>/matrix/action # Matrix-Aktion

# Review-System
GET    /api/session/<id>/pending-responses    # Wartende Reviews
POST   /api/session/<id>/pending-response/<response_id>/review  # Review durchführen
```

#### Streaming-Endpunkte

```python
# KI-Chat mit Streaming
POST   /api/llm                        # Direkte KI-Anfrage
POST   /api/session/<id>/llm-with-review  # KI mit GM-Review
POST   /api/chat                       # Chat mit Sitzungskontext
```

## Entwicklungsworkflow

### Umgebung einrichten

```bash
# Repository klonen
git clone https://github.com/sloppymo/shadowrun-backend.git
cd shadowrun-backend

# Virtuelle Umgebung
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Abhängigkeiten installieren
pip install -r requirements-dev.txt

# Pre-commit-Hooks einrichten
pre-commit install
```

### Code-Style und Linting

```bash
# Code formatieren
black app.py routes/ services/ models/
isort app.py routes/ services/ models/

# Linting
flake8 app.py routes/ services/ models/
pylint app.py routes/ services/ models/

# Type-Checking
mypy app.py routes/ services/ models/
```

### Testing

```bash
# Alle Tests ausführen
pytest tests/ -v

# Spezifische Test-Datei
pytest tests/test_api.py -v

# Coverage-Report
pytest --cov=app --cov-report=html tests/

# Integration-Tests
pytest tests/integration/ -v
```

### Datenbank-Migrationen

```bash
# Neue Migration erstellen
flask db migrate -m "Beschreibung der Änderung"

# Migration anwenden
flask db upgrade

# Migration rückgängig machen
flask db downgrade
```

## Charakterbogen-Integration

### Google Docs Integration

```python
# integrations/google_docs.py
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from utils.character_parser import parse_shadowrun_sheet

class GoogleDocsIntegration:
    def __init__(self, credentials):
        self.service = build('docs', 'v1', credentials=credentials)
        
    def discover_character_sheets(self, user_id: str) -> list:
        """Charakterbögen in Google Docs finden"""
        
        # Durchsuche Dokumente nach SR6E-Mustern
        search_patterns = [
            "Shadowrun",
            "SR6E",
            "Charakterbogen",
            "Attribute:",
            "Fertigkeiten:"
        ]
        
        discovered_sheets = []
        
        # Google Drive API-Suche implementieren
        # ...
        
        return discovered_sheets
```

## Best Practices

### Code-Organisation

1. **Modularität:** Trennen Sie Business Logic in Services
2. **Validierung:** Immer Eingaben validieren
3. **Error Handling:** Umfassendes Exception Handling
4. **Testing:** Hohe Test-Coverage anstreben
5. **Documentation:** Docstrings für alle öffentlichen Funktionen

### Sicherheit

1. **Input Sanitization:** Alle Eingaben bereinigen
2. **SQL Injection:** Nur parameterisierte Abfragen
3. **Authentication:** Robuste Authentifizierung implementieren
4. **Rate Limiting:** API-Rate-Limits einführen
5. **Logging:** Sicherheitsereignisse protokollieren 