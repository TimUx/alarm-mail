# Feuerwehr Alarm Mail Service

Dieser Service übernimmt das automatisierte Abrufen und Parsen von Alarm-E-Mails aus einem IMAP-Postfach und leitet die strukturierten Einsatzinformationen über gesicherte APIs an [alarm-monitor](https://github.com/TimUx/alarm-monitor) und/oder [alarm-messenger](https://github.com/TimUx/alarm-messenger) weiter.

## Überblick

Der alarm-mail Service entkoppelt die E-Mail-Verarbeitung von den Anzeige- und Alarmierungssystemen. Dies ermöglicht:

* Zentrale E-Mail-Verarbeitung für mehrere Zielsysteme
* Flexible Skalierung der einzelnen Komponenten
* Einfachere Wartung und Fehlersuche
* Verschlüsselte und authentifizierte API-Kommunikation

## Architektur

```
┌─────────────────┐
│  IMAP Postfach  │ (Leitstelle)
│  (Feuerwehr)    │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  alarm-mail     │
│  Service        │
│  - IMAP Polling │
│  - XML Parsing  │
└────────┬────────┘
         │
         ├──────────────┐
         │              │
         v              v
┌─────────────┐  ┌─────────────┐
│alarm-monitor│  │alarm-       │
│  Dashboard  │  │ messenger   │
└─────────────┘  └─────────────┘
```

Der Service:
1. Verbindet sich regelmäßig mit dem IMAP-Postfach
2. Sucht nach neuen ungelesenen Nachrichten
3. Parst die XML-Struktur der Alarm-E-Mails
4. Leitet die strukturierten Daten via API weiter an:
   - **alarm-monitor** - Zeigt Einsätze auf einem Dashboard an
   - **alarm-messenger** - Alarmiert Einsatzkräfte via Push-Benachrichtigungen

## Funktionsumfang

* ✅ IMAP-Polling nach neuen Alarm-E-Mails
* ✅ XML-Parsing von Einsatzinformationen (INCIDENT-Format)
* ✅ Strukturierte Datenextraktion:
  - Stichwort (Haupt- und Unterstichwort)
  - Einsatznummer
  - Zeitstempel
  - Diagnose und Bemerkungen
  - Einsatzort (Straße, Ort, Koordinaten)
  - Alarmierte Einheiten (AAO)
  - Einsatzmaßnahmen (TME-Codes)
* ✅ API-Push an alarm-monitor mit Authentifizierung
* ✅ API-Push an alarm-messenger mit Authentifizierung
* ✅ Flexible Konfiguration über Environment-Variablen
* ✅ Docker und Docker Compose Support
* ✅ Health-Check Endpoint für Monitoring
* ✅ Strukturiertes Logging

## Installation

Der Service kann nativ mit Python oder containerisiert mit Docker betrieben werden.

### Native Installation (Python)

1. **System vorbereiten**
   ```bash
   sudo apt update
   sudo apt install python3 python3-venv python3-pip
   ```

2. **Projekt klonen und Umgebung erstellen**
   ```bash
   git clone https://github.com/TimUx/alarm-mail.git
   cd alarm-mail
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Konfiguration festlegen**

   Kopieren Sie `.env.example` nach `.env` und passen Sie die Werte an:

   ```bash
   cp .env.example .env
   # Bearbeiten Sie .env mit Ihren Zugangsdaten
   ```

   Minimal erforderliche Konfiguration:
   ```bash
   ALARM_MAIL_IMAP_HOST=imap.example.com
   ALARM_MAIL_IMAP_USERNAME=alarm@example.com
   ALARM_MAIL_IMAP_PASSWORD=geheim
   ```

4. **Service starten**
   ```bash
   flask --app alarm_mail.app run --host 0.0.0.0 --port 8000
   ```

   Alternativ mit Gunicorn (empfohlen für Produktiv):
   ```bash
   gunicorn --bind 0.0.0.0:8000 "alarm_mail.app:create_app()" --workers 1 --threads 4
   ```

5. **Service als Systemd-Dienst einrichten** (optional)

   Erstellen Sie `/etc/systemd/system/alarm-mail.service`:

   ```ini
   [Unit]
   Description=Alarm Mail Service
   After=network.target

   [Service]
   Type=simple
   User=alarm
   WorkingDirectory=/opt/alarm-mail
   Environment="PATH=/opt/alarm-mail/.venv/bin"
   EnvironmentFile=/opt/alarm-mail/.env
   ExecStart=/opt/alarm-mail/.venv/bin/gunicorn --bind 0.0.0.0:8000 "alarm_mail.app:create_app()" --workers 1 --threads 4
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Aktivieren und starten:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable alarm-mail
   sudo systemctl start alarm-mail
   ```

### Container Deployment (Docker)

1. **Konfiguration vorbereiten**
   ```bash
   cd alarm-mail
   cp .env.example .env
   # Bearbeiten Sie .env mit Ihren Zugangsdaten
   ```

2. **Container bauen und starten**
   ```bash
   docker compose up -d --build
   ```

3. **Logs anzeigen**
   ```bash
   docker compose logs -f
   ```

4. **Health-Check**
   ```bash
   curl http://localhost:8000/health
   ```

5. **Stoppen**
   ```bash
   docker compose down
   ```

## Konfiguration

Alle Konfigurationsvariablen tragen den Präfix `ALARM_MAIL_`.

### IMAP-Konfiguration (Pflichtfelder)

| Variable | Pflicht | Default | Beschreibung |
|----------|---------|---------|--------------|
| `IMAP_HOST` | **ja** | - | Hostname oder IP des IMAP-Servers |
| `IMAP_PORT` | nein | 993 | Port des IMAP-Servers |
| `IMAP_USE_SSL` | nein | true | `true` für TLS, `false` für unverschlüsselt |
| `IMAP_USERNAME` | **ja** | - | Benutzername für das Postfach |
| `IMAP_PASSWORD` | **ja** | - | Passwort für das Postfach |
| `IMAP_MAILBOX` | nein | INBOX | Zu überwachender Ordner |
| `IMAP_SEARCH` | nein | UNSEEN | IMAP-Suchfilter |
| `POLL_INTERVAL` | nein | 60 | Abrufintervall in Sekunden |

### Alarm Monitor Target (Optional)

| Variable | Pflicht | Beschreibung |
|----------|---------|--------------|
| `ALARM_MONITOR_URL` | nein* | Basis-URL des alarm-monitor (z.B. `http://alarm-monitor:8000`) |
| `ALARM_MONITOR_API_KEY` | nein* | API-Schlüssel für Authentifizierung |

*Beide Variablen müssen gesetzt sein, damit der Push aktiviert wird.

### Alarm Messenger Target (Optional)

| Variable | Pflicht | Beschreibung |
|----------|---------|--------------|
| `ALARM_MESSENGER_URL` | nein* | Basis-URL des alarm-messenger (z.B. `http://alarm-messenger:3000`) |
| `ALARM_MESSENGER_API_KEY` | nein* | API-Schlüssel für Authentifizierung |

*Beide Variablen müssen gesetzt sein, damit der Push aktiviert wird.

### Beispielkonfiguration

```bash
# IMAP Konfiguration
ALARM_MAIL_IMAP_HOST=imap.mailserver.de
ALARM_MAIL_IMAP_PORT=993
ALARM_MAIL_IMAP_USE_SSL=true
ALARM_MAIL_IMAP_USERNAME=alarm@feuerwehr.de
ALARM_MAIL_IMAP_PASSWORD=sicheres-passwort
ALARM_MAIL_IMAP_MAILBOX=INBOX
ALARM_MAIL_IMAP_SEARCH=UNSEEN
ALARM_MAIL_POLL_INTERVAL=60

# Alarm Monitor
ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000
ALARM_MAIL_ALARM_MONITOR_API_KEY=monitor-api-key-123

# Alarm Messenger
ALARM_MAIL_ALARM_MESSENGER_URL=http://alarm-messenger:3000
ALARM_MAIL_ALARM_MESSENGER_API_KEY=messenger-api-key-456
```

## Integration mit alarm-monitor

Der alarm-mail Service sendet geparste Alarme an den `/api/alarm` Endpunkt des alarm-monitor.

### alarm-monitor API-Endpunkt einrichten

Der alarm-monitor muss einen API-Endpunkt bereitstellen, der Alarme entgegennimmt. Fügen Sie in der `alarm_dashboard/app.py` einen entsprechenden Endpunkt hinzu:

```python
@app.route("/api/alarm", methods=["POST"])
def api_alarm():
    """Receive alarm data via API."""
    # Verify API key
    api_key = request.headers.get("X-API-Key")
    if api_key != os.environ.get("ALARM_DASHBOARD_API_KEY"):
        return jsonify({"error": "Unauthorized"}), 401
    
    # Process alarm data
    alarm_data = request.get_json()
    # Store and display alarm...
    return jsonify({"status": "ok"}), 200
```

## Integration mit alarm-messenger

Der alarm-mail Service sendet Alarme an den `/api/emergencies` Endpunkt des alarm-messenger.

Das Format wird automatisch angepasst:

```python
{
    "emergencyNumber": "2024-001",
    "emergencyDate": "2024-12-08T14:30:00",
    "emergencyKeyword": "BRAND 3",
    "emergencyDescription": "Wohnungsbrand",
    "emergencyLocation": "Hauptstraße 123, 12345 Stadt",
    "groups": "WIL26,WIL41"  # Optional, wenn TME-Codes vorhanden
}
```

Der alarm-messenger benötigt in der `.env`:
```bash
API_SECRET_KEY=ihr-messenger-api-key
```

## API-Endpunkte

### GET /health
Health-Check Endpunkt für Monitoring

**Response:**
```json
{
  "status": "ok",
  "service": "alarm-mail"
}
```

### GET /
Service-Informationen

**Response:**
```json
{
  "service": "alarm-mail",
  "status": "running",
  "targets": ["alarm-monitor", "alarm-messenger"],
  "poll_interval": 60
}
```

## E-Mail-Format

Der Service erwartet E-Mails im XML-Format mit `<INCIDENT>` Struktur:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<INCIDENT>
  <STICHWORT>F3Y</STICHWORT>
  <ESTICHWORT_1>F3Y</ESTICHWORT_1>
  <ESTICHWORT_2>Personen in Gefahr</ESTICHWORT_2>
  <ENR>7850001123</ENR>
  <EBEGINN>08.12.2024 14:30:00</EBEGINN>
  <DIAGNOSE>Brand in Wohngebäude</DIAGNOSE>
  <EO_BEMERKUNG>Starke Rauchentwicklung</EO_BEMERKUNG>
  <ORT>Musterstadt</ORT>
  <ORTSTEIL>Nordviertel</ORTSTEIL>
  <STRASSE>Hauptstraße</STRASSE>
  <HAUSNUMMER>123</HAUSNUMMER>
  <KOORDINATE_LAT>51.2345</KOORDINATE_LAT>
  <KOORDINATE_LON>9.8765</KOORDINATE_LON>
  <AAO>LF Musterstadt 1;DLK Musterstadt</AAO>
  <EINSATZMASSNAHMEN>
    <TME>
      <BEZEICHNUNG>MUS Nord 1 (TME MUS11)</BEZEICHNUNG>
      <BEZEICHNUNG>MUS Innenstadt (TME MUS05)</BEZEICHNUNG>
    </TME>
  </EINSATZMASSNAHMEN>
</INCIDENT>
```

## Deployment-Szenarien

### Szenario 1: Alle Services mit Docker Compose

Erstellen Sie eine gemeinsame `docker-compose.yaml`:

```yaml
services:
  alarm-mail:
    build: ./alarm-mail
    restart: unless-stopped
    environment:
      - ALARM_MAIL_IMAP_HOST=imap.example.com
      - ALARM_MAIL_IMAP_USERNAME=alarm@example.com
      - ALARM_MAIL_IMAP_PASSWORD=geheim
      - ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000
      - ALARM_MAIL_ALARM_MONITOR_API_KEY=monitor-key
      - ALARM_MAIL_ALARM_MESSENGER_URL=http://alarm-messenger:3000
      - ALARM_MAIL_ALARM_MESSENGER_API_KEY=messenger-key
    depends_on:
      - alarm-monitor
      - alarm-messenger

  alarm-monitor:
    build: ./alarm-monitor
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ALARM_DASHBOARD_API_KEY=monitor-key

  alarm-messenger:
    build: ./alarm-messenger/server
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - API_SECRET_KEY=messenger-key
```

### Szenario 2: Nur alarm-mail mit externen Targets

```bash
ALARM_MAIL_ALARM_MONITOR_URL=https://monitor.feuerwehr.de
ALARM_MAIL_ALARM_MESSENGER_URL=https://messenger.feuerwehr.de
```

## Monitoring und Fehlersuche

### Logs anzeigen

**Docker:**
```bash
docker compose logs -f alarm-mail
```

**Systemd:**
```bash
sudo journalctl -u alarm-mail -f
```

### Health-Check

```bash
curl http://localhost:8000/health
```

### Häufige Probleme

**Problem:** Service startet nicht
```bash
# Prüfen Sie die Konfiguration
cat .env

# Prüfen Sie die Logs
docker compose logs alarm-mail
```

**Problem:** E-Mails werden nicht abgerufen
- IMAP-Zugangsdaten prüfen
- Netzwerkverbindung zum IMAP-Server testen
- Firewall-Regeln überprüfen

**Problem:** Push zu Targets fehlschlägt
- API-Keys überprüfen
- Erreichbarkeit der Targets prüfen (`curl http://target-url/health`)
- Logs auf Fehler überprüfen

## Sicherheit

* 🔒 IMAP-Verbindung über SSL/TLS (Standard)
* 🔒 API-Authentifizierung mit Keys
* 🔒 Keine Speicherung von E-Mail-Inhalten
* 🔒 Container läuft als non-root User
* 🔒 Secrets nur über Environment-Variablen
* 🔒 Health-Check ohne sensitive Daten

**Best Practices:**
- Verwenden Sie starke, zufällige API-Keys
- Rotieren Sie API-Keys regelmäßig
- Betreiben Sie alle Services in einem privaten Netzwerk
- Verwenden Sie HTTPS für externe Verbindungen
- Setzen Sie Firewall-Regeln für IMAP und API-Zugriffe

## Entwicklung

### Projektstruktur

```
alarm-mail/
├── alarm_mail/           # Hauptanwendung
│   ├── __init__.py      # Package init
│   ├── app.py           # Flask application
│   ├── config.py        # Konfiguration
│   ├── mail_checker.py  # IMAP polling
│   ├── parser.py        # XML parsing
│   └── push_service.py  # API push
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container image
├── compose.yaml         # Docker Compose
├── .env.example         # Konfigurationsvorlage
└── README.md           # Diese Datei
```

### Lokale Entwicklung

```bash
# Virtual environment erstellen
python3 -m venv .venv
source .venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# Service starten
flask --app alarm_mail.app run --host 0.0.0.0 --port 8000
```

### Tests

Tests können mit pytest durchgeführt werden (sofern Tests implementiert sind):

```bash
pip install pytest
pytest
```

## Lizenz

MIT License - siehe LICENSE Datei

## Support

Bei Fragen oder Problemen öffnen Sie bitte ein Issue auf GitHub:
https://github.com/TimUx/alarm-mail/issues
