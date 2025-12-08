# Schnellstart Anleitung - alarm-mail

Diese Kurzanleitung hilft Ihnen, den alarm-mail Service in wenigen Minuten zu starten.

## Voraussetzungen

- Docker und Docker Compose (empfohlen) ODER
- Python 3.11+ mit pip und venv

## Option 1: Docker (Empfohlen)

### Schritt 1: Projekt klonen
```bash
git clone https://github.com/TimUx/alarm-mail.git
cd alarm-mail
```

### Schritt 2: Konfiguration erstellen
```bash
cp .env.example .env
nano .env  # oder ein anderer Editor
```

Minimal erforderliche Konfiguration:
```bash
# IMAP Zugangsdaten (Pflicht)
ALARM_MAIL_IMAP_HOST=imap.ihremailserver.de
ALARM_MAIL_IMAP_USERNAME=alarm@ihre-feuerwehr.de
ALARM_MAIL_IMAP_PASSWORD=IhrPasswort

# Optional: alarm-monitor
ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000
ALARM_MAIL_ALARM_MONITOR_API_KEY=ihr-monitor-api-key

# Optional: alarm-messenger
ALARM_MAIL_ALARM_MESSENGER_URL=http://alarm-messenger:3000
ALARM_MAIL_ALARM_MESSENGER_API_KEY=ihr-messenger-api-key
```

### Schritt 3: Service starten
```bash
docker compose up -d
```

### Schritt 4: Status prüfen
```bash
# Logs anzeigen
docker compose logs -f

# Health-Check
curl http://localhost:8000/health
```

✅ Fertig! Der Service läuft jetzt und überwacht Ihr E-Mail-Postfach.

## Option 2: Native Installation

### Schritt 1: Projekt klonen und Setup
```bash
git clone https://github.com/TimUx/alarm-mail.git
cd alarm-mail
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Schritt 2: Konfiguration erstellen
```bash
cp .env.example .env
nano .env  # Zugangsdaten eintragen
```

### Schritt 3: Service starten
```bash
gunicorn --bind 0.0.0.0:8000 "alarm_mail.app:create_app()" --workers 1 --threads 4
```

### Schritt 4 (Optional): Als Systemd-Dienst einrichten
```bash
# Service-Datei anpassen
sudo cp alarm-mail.service /etc/systemd/system/
sudo nano /etc/systemd/system/alarm-mail.service

# Dienst aktivieren
sudo systemctl daemon-reload
sudo systemctl enable alarm-mail
sudo systemctl start alarm-mail

# Status prüfen
sudo systemctl status alarm-mail
```

## Integration mit anderen Services

### Mit alarm-monitor

1. Stellen Sie sicher, dass alarm-monitor läuft
2. Konfigurieren Sie die URL und API-Key in `.env`:
   ```bash
   ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000
   ALARM_MAIL_ALARM_MONITOR_API_KEY=monitor-key
   ```
3. Alarm-monitor muss einen `/api/alarm` Endpunkt bereitstellen

### Mit alarm-messenger

1. Stellen Sie sicher, dass alarm-messenger läuft
2. Konfigurieren Sie die URL und API-Key in `.env`:
   ```bash
   ALARM_MAIL_ALARM_MESSENGER_URL=http://alarm-messenger:3000
   ALARM_MAIL_ALARM_MESSENGER_API_KEY=messenger-key
   ```
3. Der alarm-messenger `/api/emergencies` Endpunkt wird automatisch genutzt

## Gemeinsames Docker Compose Setup

Für ein All-in-One Setup erstellen Sie eine `docker-compose.yaml`:

```yaml
version: '3.8'

services:
  alarm-mail:
    build: ./alarm-mail
    restart: unless-stopped
    environment:
      - ALARM_MAIL_IMAP_HOST=imap.example.com
      - ALARM_MAIL_IMAP_USERNAME=alarm@example.com
      - ALARM_MAIL_IMAP_PASSWORD=${IMAP_PASSWORD}
      - ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000
      - ALARM_MAIL_ALARM_MONITOR_API_KEY=${MONITOR_API_KEY}
      - ALARM_MAIL_ALARM_MESSENGER_URL=http://alarm-messenger:3000
      - ALARM_MAIL_ALARM_MESSENGER_API_KEY=${MESSENGER_API_KEY}
    depends_on:
      - alarm-monitor
      - alarm-messenger

  alarm-monitor:
    image: alarm-monitor:latest
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ALARM_DASHBOARD_API_KEY=${MONITOR_API_KEY}

  alarm-messenger:
    image: alarm-messenger:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - API_SECRET_KEY=${MESSENGER_API_KEY}
```

Starten mit:
```bash
docker compose up -d
```

## Fehlerbehebung

### Service startet nicht
```bash
# Logs prüfen
docker compose logs alarm-mail

# Oder bei nativer Installation
sudo journalctl -u alarm-mail -f
```

### IMAP-Verbindung schlägt fehl
- Prüfen Sie Benutzername und Passwort
- Testen Sie die Verbindung: `telnet imap.ihremailserver.de 993`
- Prüfen Sie Firewall-Regeln

### Push zu Targets schlägt fehl
- Prüfen Sie, ob die Target-Services laufen
- Testen Sie die Erreichbarkeit: `curl http://target-url/health`
- Prüfen Sie die API-Keys

## Nächste Schritte

- Lesen Sie die vollständige [README.md](README.md) für Details
- Konfigurieren Sie zusätzliche Optionen in `.env`
- Richten Sie Monitoring und Backups ein
- Testen Sie mit Test-E-Mails

## Support

Bei Problemen öffnen Sie ein Issue auf GitHub:
https://github.com/TimUx/alarm-mail/issues
