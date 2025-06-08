# Shadowrun Backend - Detaillierte Installationsanleitung

## Überblick

Diese Anleitung führt Sie durch die komplette Installation und Konfiguration des Shadowrun Flask Backend-Systems. Das Backend stellt die API-Infrastruktur für Multiplayer-Shadowrun-Sitzungen bereit und ermöglicht KI-gestützte Erzählungen.

## Systemvoraussetzungen

### Hardware
- **CPU:** Mindestens 2 Kerne, empfohlen 4+ Kerne
- **RAM:** Mindestens 4GB, empfohlen 8GB+
- **Speicher:** Mindestens 2GB freier Speicher
- **Netzwerk:** Stabile Internetverbindung für KI-API-Zugriff

### Software
- **Python:** Version 3.11+ (getestet mit 3.13)
- **Betriebssystem:** Windows 10+, macOS 10.15+, oder Linux (Ubuntu 20.04+)
- **Git:** Für Code-Repository-Zugriff

## Schritt-für-Schritt Installation

### 1. Repository klonen

```bash
# Repository herunterladen
git clone https://github.com/sloppymo/shadowrun-backend.git
cd shadowrun-backend

# Aktuelle Version überprüfen
git log --oneline -5
```

### 2. Python-Umgebung einrichten

#### Virtuelle Umgebung erstellen (empfohlen)
```bash
# Python venv erstellen
python -m venv shadowrun-env

# Aktivieren (Windows)
shadowrun-env\Scripts\activate

# Aktivieren (Linux/macOS)
source shadowrun-env/bin/activate
```

#### Abhängigkeiten installieren
```bash
# Produktionsabhängigkeiten
pip install -r requirements.txt

# Entwicklungsabhängigkeiten (optional)
pip install -r requirements-dev.txt

# Installation überprüfen
pip list | grep flask
```

### 3. Umgebungskonfiguration

#### .env-Datei erstellen
```bash
# Vorlage kopieren
cp .env.example .env

# Datei bearbeiten (wichtig!)
nano .env  # oder bevorzugter Editor
```

#### Erforderliche Umgebungsvariablen
```bash
# OpenAI API-Konfiguration
OPENAI_API_KEY=sk-proj-ihr-openai-api-key-hier
OPENAI_MODEL=gpt-4

# Flask-Konfiguration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=ihr-sicherer-geheimer-schluessel

# Datenbank
DATABASE_URL=sqlite:///shadowrun.db

# CORS-Konfiguration
FRONTEND_URL=http://localhost:3000

# Logging
LOG_LEVEL=INFO
```

### 4. Datenbank initialisieren

```bash
# Datenbank-Schema erstellen
python -c "from app import db; db.create_all(); print('Datenbank initialisiert!')"

# Tabellen überprüfen
python -c "from app import db; print('Tabellen:', db.metadata.tables.keys())"
```

### 5. Backend starten

```bash
# Entwicklungsserver starten
python app.py

# Erfolgreich wenn Sie sehen:
# * Running on http://127.0.0.1:5000
# * Debug mode: on
```

### 6. Installation überprüfen

#### Gesundheitscheck
```bash
# API-Ping testen
curl http://localhost:5000/api/ping

# Erwartete Antwort:
# {"status": "ok", "message": "Shadowrun Backend is running"}
```

#### Test-Sitzung erstellen
```bash
# Neue Sitzung erstellen
curl -X POST http://localhost:5000/api/session \
  -H "Content-Type: application/json" \
  -d '{"name": "Test-Sitzung", "gm_user_id": "test-gm"}'

# Erfolgreiche Antwort enthält session_id
```

## Erweiterte Konfiguration

### KI-Provider konfigurieren

#### OpenAI (Standard)
```bash
# In .env
OPENAI_API_KEY=sk-proj-ihr-schluessel
OPENAI_MODEL=gpt-4-turbo
OPENAI_MAX_TOKENS=2048
```

#### Alternative Provider
```bash
# DeepSeek
DEEPSEEK_API_KEY=ihr-deepseek-schluessel
DEEPSEEK_MODEL=deepseek-coder

# Anthropic Claude
ANTHROPIC_API_KEY=ihr-anthropic-schluessel
ANTHROPIC_MODEL=claude-3-sonnet
```

### Datenbank-Konfiguration

#### SQLite (Standard)
```bash
# Automatisch erstellt, keine zusätzliche Konfiguration
DATABASE_URL=sqlite:///shadowrun.db
```

#### PostgreSQL (Produktion)
```bash
# PostgreSQL installieren und konfigurieren
pip install psycopg2-binary

# In .env
DATABASE_URL=postgresql://user:password@localhost:5432/shadowrun
```

### Logging-Konfiguration

#### Detailliertes Logging
```bash
# In .env für Entwicklung
LOG_LEVEL=DEBUG
LOG_FILE=logs/shadowrun.log

# Log-Verzeichnis erstellen
mkdir -p logs
```

## Fehlerbehebung

### Häufige Probleme

#### Port bereits belegt
```bash
# Anderen Port verwenden
export FLASK_RUN_PORT=5001
python app.py

# Oder in app.py ändern:
# app.run(host='0.0.0.0', port=5001, debug=True)
```

#### Datenbank-Fehler
```bash
# Datenbank zurücksetzen (Entwicklung)
rm shadowrun.db
python -c "from app import db; db.create_all()"

# Migrationen (falls vorhanden)
flask db upgrade
```

#### CORS-Fehler
```bash
# Frontend-URL in .env prüfen
FRONTEND_URL=http://localhost:3000

# Oder in app.py CORS-Konfiguration anpassen
```

#### API-Key-Fehler
```bash
# OpenAI-Key testen
python -c "
import openai
openai.api_key = 'ihr-key'
print('Key gültig:', openai.Model.list())
"
```

### Performance-Optimierung

#### Produktionseinstellungen
```bash
# In .env für Produktion
FLASK_ENV=production
FLASK_DEBUG=False
WORKERS=4

# Gunicorn verwenden
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

#### Caching aktivieren
```bash
# Redis installieren
pip install redis

# In .env
REDIS_URL=redis://localhost:6379/0
CACHE_TIMEOUT=300
```

## Automatisierte Tests

### Test-Suite ausführen
```bash
# Alle Tests
python -m pytest tests/

# Spezifische Tests
python -m pytest tests/test_api.py -v

# Coverage-Report
pip install pytest-cov
python -m pytest --cov=app tests/
```

### PowerShell-Tests (Windows)
```powershell
# Backend-Tests ausführen
.\test_all.ps1

# Spezifische API-Tests
.\test_api.ps1
```

## Nächste Schritte

Nach erfolgreicher Installation:

1. **Frontend installieren:** Siehe shadowrun-interface Dokumentation
2. **Erste Sitzung erstellen:** Über API oder Frontend
3. **GM-Dashboard konfigurieren:** Character sheets und Integrationssysteme
4. **Slack-Integration einrichten:** Für Team-Communication
5. **Produktion vorbereiten:** SSL, Reverse Proxy, Monitoring

## Support

Bei Problemen:
- **Issues:** GitHub Repository Issues
- **Dokumentation:** Weitere .de.md Dateien
- **Community:** Shadowrun RPG Communities
- **Logs prüfen:** `logs/shadowrun.log` für detaillierte Fehlermeldungen

## Sicherheitshinweise

- ⚠️ **API-Keys:** Niemals in Versionskontrolle committen
- ⚠️ **SECRET_KEY:** Starkes, zufälliges Passwort verwenden
- ⚠️ **Produktion:** Debug-Modus deaktivieren
- ⚠️ **Firewall:** Nur erforderliche Ports öffnen
- ⚠️ **Updates:** Regelmäßig Abhängigkeiten aktualisieren 