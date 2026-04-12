# Beispiel-Konfigurationen

Dieser Ordner enthält Beispiel-Konfigurationen für verschiedene Deployment-Szenarien des alarm-mail Service.

## 📁 Dateien

### docker-compose-all-in-one.yaml
**Vollständiges Docker Compose Setup** mit allen drei Services (alarm-mail, alarm-monitor, alarm-messenger) inklusive PostgreSQL-Datenbank.

**Verwendung:**
```bash
# Datei kopieren
cp docs/examples/docker-compose-all-in-one.yaml docker-compose.yaml

# .env erstellen (siehe env-template-complete.env)
cp docs/examples/env-template-complete.env .env
nano .env  # Werte anpassen

# Starten
docker compose up -d

# Logs anzeigen
docker compose logs -f
```

**Features:**
- ✅ Alle drei Services in einem Netzwerk
- ✅ Automatische Service-Discovery
- ✅ Health-Checks für alle Services
- ✅ Persistente Volumes für Daten
- ✅ Log-Rotation
- ✅ Timezone-Unterstützung

**Ideal für:**
- Kleine bis mittlere Feuerwehren
- Test- und Entwicklungsumgebungen
- Single-Server-Deployments
- Schnelles Setup

---

### env-template-complete.env
**Vollständige Konfigurationsvorlage** mit allen verfügbaren Umgebungsvariablen für alarm-mail.

**Verwendung:**
```bash
# Als Basis für .env verwenden
cp docs/examples/env-template-complete.env .env

# Mit Editor öffnen und anpassen
nano .env

# Oder direkt bearbeiten
cat docs/examples/env-template-complete.env > .env
```

**Enthält:**
- ✅ Alle IMAP-Konfigurationsoptionen
- ✅ Integration-Einstellungen für alarm-monitor
- ✅ Integration-Einstellungen für alarm-messenger
- ✅ Ausführliche Kommentare und Erklärungen
- ✅ Beispiele für verschiedene Szenarien
- ✅ Best Practices und Sicherheitshinweise

**Ideal für:**
- Neue Installationen
- Referenz für verfügbare Optionen
- Dokumentation der eigenen Konfiguration

---

## 🚀 Schnellstart-Szenarien

### Szenario 1: Nur alarm-mail (Standalone)

Nur E-Mail-Parsing ohne Weiterleitung an andere Services.

**Benötigte Dateien:**
- `env-template-complete.env` als Basis

**Minimale .env:**
```bash
ALARM_MAIL_IMAP_HOST=imap.mailserver.de
ALARM_MAIL_IMAP_USERNAME=alarm@feuerwehr.de
ALARM_MAIL_IMAP_PASSWORD=passwort
```

**Start:**
```bash
docker compose up -d
```

**Verwendung:**
- Testen der E-Mail-Verarbeitung
- Entwicklung und Debugging
- Validierung des XML-Formats

---

### Szenario 2: alarm-mail + alarm-monitor

E-Mail-Parsing mit Dashboard-Anzeige.

**Benötigte Dateien:**
- `docker-compose-all-in-one.yaml` (nur alarm-mail und alarm-monitor Abschnitte)
- `env-template-complete.env`

**Erforderliche .env-Variablen:**
```bash
# IMAP
ALARM_MAIL_IMAP_HOST=imap.mailserver.de
ALARM_MAIL_IMAP_USERNAME=alarm@feuerwehr.de
ALARM_MAIL_IMAP_PASSWORD=passwort

# alarm-monitor Integration
ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000
ALARM_MAIL_ALARM_MONITOR_API_KEY=ihr-monitor-key

# API-Key auch für alarm-monitor (muss übereinstimmen!)
API_KEY_SHARED=ihr-monitor-key
```

**Zugriff:**
- Dashboard: http://localhost:8000

---

### Szenario 3: alarm-mail + alarm-messenger

E-Mail-Parsing mit mobiler Alarmierung.

**Benötigte Dateien:**
- `docker-compose-all-in-one.yaml` (alarm-mail, alarm-messenger, postgres)
- `env-template-complete.env`

**Erforderliche .env-Variablen:**
```bash
# IMAP
ALARM_MAIL_IMAP_HOST=imap.mailserver.de
ALARM_MAIL_IMAP_USERNAME=alarm@feuerwehr.de
ALARM_MAIL_IMAP_PASSWORD=passwort

# alarm-messenger Integration
ALARM_MAIL_ALARM_MESSENGER_URL=http://alarm-messenger:3000
ALARM_MAIL_ALARM_MESSENGER_API_KEY=ihr-messenger-key

# API-Key auch für alarm-messenger (muss übereinstimmen!)
API_KEY_SHARED=ihr-messenger-key

# PostgreSQL
POSTGRES_PASSWORD=postgres-passwort
```

**Zugriff:**
- Messenger-API: http://localhost:3000

---

### Szenario 4: Vollständiges Setup (All-in-One)

Alle Services zusammen - Dashboard + Mobile Alarmierung.

**Benötigte Dateien:**
- `docker-compose-all-in-one.yaml` (komplett)
- `env-template-complete.env`

**Erforderliche .env-Variablen:**
```bash
# IMAP
IMAP_HOST=imap.mailserver.de
IMAP_USERNAME=alarm@feuerwehr.de
IMAP_PASSWORD=passwort

# Gemeinsamer API-Key für beide Integrationen
API_KEY_SHARED=ihr-sehr-geheimer-key-mindestens-32-zeichen

# PostgreSQL
POSTGRES_PASSWORD=postgres-passwort
```

**Start:**
```bash
docker compose -f docker-compose-all-in-one.yaml up -d
```

**Zugriff:**
- Dashboard: http://localhost:8000
- Messenger: http://localhost:3000

---

### Szenario 5: Multi-Target – mehrere Standorte mit Gruppenfilter

Mehrere alarm-monitor-Instanzen an verschiedenen Standorten, jede nur für ihre Alarmierungsgruppen, plus ein alarm-messenger ohne Gruppenfilter.

**Benötigte Dateien:**
- `env-template-complete.env` als Basis

**Erforderliche .env-Variablen:**
```bash
# IMAP
ALARM_MAIL_IMAP_HOST=imap.mailserver.de
ALARM_MAIL_IMAP_USERNAME=alarm@feuerwehr.de
ALARM_MAIL_IMAP_PASSWORD=passwort

# Standort 1: alarm-monitor, nur für WIL28 und WIL29
ALARM_MAIL_TARGET_1_TYPE=alarm-monitor
ALARM_MAIL_TARGET_1_URL=https://monitor-standort1.feuerwehr.de
ALARM_MAIL_TARGET_1_API_KEY=key-standort1
ALARM_MAIL_TARGET_1_GROUPS=WIL28,WIL29

# Standort 2: alarm-monitor, nur für WIL30 und WIL31
ALARM_MAIL_TARGET_2_TYPE=alarm-monitor
ALARM_MAIL_TARGET_2_URL=https://monitor-standort2.feuerwehr.de
ALARM_MAIL_TARGET_2_API_KEY=key-standort2
ALARM_MAIL_TARGET_2_GROUPS=WIL30,WIL31

# Messenger: empfängt alle Alarme (kein Gruppenfilter)
ALARM_MAIL_TARGET_3_TYPE=alarm-messenger
ALARM_MAIL_TARGET_3_URL=https://messenger.feuerwehr.de
ALARM_MAIL_TARGET_3_API_KEY=key-messenger
```

**Verhalten:**
- Ein Alarm mit Dispatch-Code `WIL28` wird nur an Standort 1 weitergeleitet
- Ein Alarm mit `WIL30` nur an Standort 2
- Der alarm-messenger empfängt jeden Alarm unabhängig vom Dispatch-Code
- E-Mails werden nur als gelesen markiert, wenn mindestens ein Target den Alarm empfangen hat

**Ideal für:**
- Feuerwehren mit mehreren Standorten und getrennten Alarmierungsgruppen
- Szenarien mit mehreren alarm-monitor-Instanzen

---

## ⚙️ Anpassungen

### Docker Compose anpassen

**Ports ändern:**
```yaml
ports:
  - "8080:8000"  # alarm-monitor auf Port 8080
```

**Ressourcen limitieren:**
```yaml
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 512M
```

**Restart-Policy ändern:**
```yaml
restart: on-failure:3  # Maximal 3 Restart-Versuche
```

### Umgebungsvariablen

**Aus Datei laden:**
```yaml
env_file:
  - .env
  - .env.local  # Überschreibt .env
```

**Direkt setzen:**
```yaml
environment:
  - ALARM_MAIL_POLL_INTERVAL=30
```

**Aus Secrets (Docker Swarm):**
```yaml
secrets:
  - imap_password
environment:
  - ALARM_MAIL_IMAP_PASSWORD_FILE=/run/secrets/imap_password
```

---

## 🔒 Sicherheit

### API-Keys generieren

```bash
# Mit OpenSSL (Linux/macOS)
openssl rand -hex 32

# Mit Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Mit PowerShell (Windows)
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

### Secrets-Management

**Entwicklung:**
- `.env` Datei verwenden (in `.gitignore`)
- Nie in Git committen

**Produktion:**
- Docker Secrets verwenden
- Vault-Systeme (HashiCorp Vault)
- Cloud-Provider Secrets (AWS Secrets Manager, etc.)

### Netzwerk-Isolation

**Internes Netzwerk (kein Internet):**
```yaml
networks:
  alarm-network:
    driver: bridge
    internal: true  # Kein Zugriff nach außen
```

---

## 🧪 Testing

### Test-E-Mail senden

Erstellen Sie eine Test-E-Mail mit XML-Inhalt:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<INCIDENT>
  <ENR>TEST-001</ENR>
  <EBEGINN>08.12.2024 14:30:00</EBEGINN>
  <ESTICHWORT_1>TEST</ESTICHWORT_1>
  <ESTICHWORT_2>Testlauf</ESTICHWORT_2>
  <DIAGNOSE>Test-Einsatz für System-Validierung</DIAGNOSE>
  <ORT>Teststadt</ORT>
  <ORTSTEIL>Testzentrum</ORTSTEIL>
  <STRASSE>Teststraße</STRASSE>
  <HAUSNUMMER>123</HAUSNUMMER>
  <KOORDINATE_LAT>51.2345</KOORDINATE_LAT>
  <KOORDINATE_LON>9.8765</KOORDINATE_LON>
  <AAO>Test-Fahrzeug 1;Test-Fahrzeug 2</AAO>
</INCIDENT>
```

Senden Sie diese als E-Mail an Ihr konfiguriertes Postfach und beobachten Sie die Logs:

```bash
docker compose logs -f alarm-mail
```

---

## 📊 Monitoring

### Logs anzeigen

```bash
# Alle Services
docker compose logs -f

# Nur alarm-mail
docker compose logs -f alarm-mail

# Letzte 100 Zeilen
docker compose logs --tail=100 alarm-mail

# Nur Fehler
docker compose logs alarm-mail | grep ERROR
```

### Health-Checks prüfen

```bash
# alarm-mail
curl http://localhost:8000/health

# Service-Info
curl http://localhost:8000/

# Docker Health-Status
docker ps
```

### Performance überwachen

```bash
# Ressourcen-Verbrauch
docker stats

# Disk-Usage
docker system df
```

---

## 🛠️ Wartung

### Updates durchführen

```bash
# Images neu bauen
docker compose build --no-cache

# Services neu starten
docker compose up -d

# Alte Images aufräumen
docker image prune -a
```

### Backup erstellen

```bash
# Volumes sichern
docker run --rm -v alarm-monitor-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/monitor-backup.tar.gz /data

docker run --rm -v alarm-postgres-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup.tar.gz /data

# Konfiguration sichern (verschlüsselt)
tar czf config-backup.tar.gz .env docker-compose.yaml
gpg -c config-backup.tar.gz
rm config-backup.tar.gz
```

### Logs rotieren

Konfiguriert in `docker-compose-all-in-one.yaml`:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"  # Maximale Dateigröße
    max-file: "3"     # Anzahl rotierter Dateien
```

---

## 📚 Weiterführende Links

- [README.md](../../README.md) - Hauptdokumentation
- [QUICKSTART.md](../../QUICKSTART.md) - Schnellstart-Anleitung
- [docs/API.md](../API.md) - API-Dokumentation
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Beiträge

---

## 💬 Hilfe

Bei Fragen oder Problemen:

- **GitHub Issues:** [TimUx/alarm-mail/issues](https://github.com/TimUx/alarm-mail/issues)
- **Dokumentation:** [README.md](../../README.md)
- **Beispiele:** Dieser Ordner

---

**Stand:** Dezember 2024  
**Lizenz:** MIT
