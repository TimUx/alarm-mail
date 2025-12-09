# ⚡ Schnellstart - alarm-mail

Diese Anleitung hilft Ihnen, den alarm-mail Service **in 5 Minuten** einzurichten und zu starten.

> 💡 **Tipp:** Für detaillierte Informationen siehe die vollständige [README.md](README.md)

---

## 📋 Voraussetzungen

Wählen Sie eine der beiden Optionen:

### Option A: Docker (Empfohlen) 🐋
- ✅ Docker 20.10 oder höher
- ✅ Docker Compose v2.0 oder höher

### Option B: Native Python 🐍
- ✅ Python 3.11 oder höher
- ✅ pip und venv

**Plus in beiden Fällen:**
- ✅ IMAP-Postfach mit Zugangsdaten
- ✅ Optional: laufende Instanzen von alarm-monitor und/oder alarm-messenger

---

## 🚀 Option 1: Docker (Empfohlen)

**Geschätzte Zeit:** ⏱️ 3 Minuten

### Schritt 1️⃣: Repository klonen

```bash
git clone https://github.com/TimUx/alarm-mail.git
cd alarm-mail
```

### Schritt 2️⃣: Konfiguration erstellen

```bash
cp .env.example .env
nano .env  # oder Ihr bevorzugter Editor (vim, code, etc.)
```

**Minimal erforderliche Einstellungen:**

```bash
# IMAP-Zugangsdaten (PFLICHT)
ALARM_MAIL_IMAP_HOST=imap.ihremailserver.de
ALARM_MAIL_IMAP_USERNAME=alarm@ihre-feuerwehr.de
ALARM_MAIL_IMAP_PASSWORD=IhrPasswort

# Optional: Integration mit alarm-monitor
#ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000
#ALARM_MAIL_ALARM_MONITOR_API_KEY=ihr-monitor-api-key

# Optional: Integration mit alarm-messenger
#ALARM_MAIL_ALARM_MESSENGER_URL=http://alarm-messenger:3000
#ALARM_MAIL_ALARM_MESSENGER_API_KEY=ihr-messenger-api-key
```

💡 **Hinweis:** Für die Integrationen müssen URL **und** API-Key gesetzt sein.

### Schritt 3️⃣: Service starten

```bash
docker compose up -d
```

Das war's! 🎉 Der Service baut das Image und startet im Hintergrund.

### Schritt 4️⃣: Status überprüfen

```bash
# Live-Logs anzeigen
docker compose logs -f alarm-mail

# Health-Check
curl http://localhost:8000/health
# Expected: {"status":"ok","service":"alarm-mail"}

# Service-Info
curl http://localhost:8000/
# Zeigt konfigurierte Targets und Polling-Intervall
```

✅ **Fertig!** Der Service läuft jetzt und überwacht Ihr E-Mail-Postfach.

---

## 🐍 Option 2: Native Python-Installation

**Geschätzte Zeit:** ⏱️ 5-7 Minuten

### Schritt 1️⃣: Projekt klonen und Python-Umgebung einrichten

```bash
# Repository klonen
git clone https://github.com/TimUx/alarm-mail.git
cd alarm-mail

# Virtual Environment erstellen
python3 -m venv .venv

# Environment aktivieren
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Dependencies installieren
pip install -r requirements.txt
```

### Schritt 2️⃣: Konfiguration erstellen

```bash
cp .env.example .env
nano .env  # Ihre Zugangsdaten eintragen
```

Siehe Option 1, Schritt 2 für die erforderlichen Einstellungen.

### Schritt 3️⃣: Service starten

**Für Entwicklung/Testing:**
```bash
flask --app alarm_mail.app run --host 0.0.0.0 --port 8000
```

**Für Produktion (mit Gunicorn):**
```bash
gunicorn --bind 0.0.0.0:8000 "alarm_mail.app:create_app()" --workers 1 --threads 4
```

✅ **Service läuft!** Öffnen Sie http://localhost:8000 im Browser.

### Schritt 4️⃣ (Optional): Als Systemd-Dienst einrichten

Für automatischen Start beim Systemstart:

```bash
# Service-Datei kopieren und anpassen
sudo cp alarm-mail.service /etc/systemd/system/
sudo nano /etc/systemd/system/alarm-mail.service

# Pfade in der Service-Datei anpassen:
# WorkingDirectory=/opt/alarm-mail
# EnvironmentFile=/opt/alarm-mail/.env
# ExecStart=/opt/alarm-mail/.venv/bin/gunicorn ...

# Dienst aktivieren und starten
sudo systemctl daemon-reload
sudo systemctl enable alarm-mail
sudo systemctl start alarm-mail

# Status prüfen
sudo systemctl status alarm-mail

# Logs ansehen
sudo journalctl -u alarm-mail -f
```

---

## 🔗 Integration mit anderen Services

### Mit alarm-monitor verbinden

**Voraussetzungen:**
- alarm-monitor läuft und ist erreichbar
- API-Key ist in alarm-monitor konfiguriert (`ALARM_DASHBOARD_API_KEY`)

**Konfiguration in alarm-mail `.env`:**
```bash
ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000
ALARM_MAIL_ALARM_MONITOR_API_KEY=gleicher-key-wie-im-monitor
```

**Wichtig:** API-Keys müssen übereinstimmen!

### Mit alarm-messenger verbinden

**Voraussetzungen:**
- alarm-messenger läuft und ist erreichbar
- API-Key ist in alarm-messenger konfiguriert (`API_SECRET_KEY`)

**Konfiguration in alarm-mail `.env`:**
```bash
ALARM_MAIL_ALARM_MESSENGER_URL=http://alarm-messenger:3000
ALARM_MAIL_ALARM_MESSENGER_API_KEY=gleicher-key-wie-im-messenger
```

### All-in-One Setup (Alle Services zusammen)

Erstellen Sie eine gemeinsame `docker-compose.yaml` für alle drei Services:

```yaml
version: '3.8'

services:
  alarm-mail:
    build: ./alarm-mail
    restart: unless-stopped
    env_file:
      - ./alarm-mail/.env
    depends_on:
      - alarm-monitor
      - alarm-messenger
    networks:
      - alarm-network

  alarm-monitor:
    build: ./alarm-monitor
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - ./alarm-monitor/.env
    networks:
      - alarm-network

  alarm-messenger:
    build: ./alarm-messenger/server
    restart: unless-stopped
    ports:
      - "3000:3000"
    env_file:
      - ./alarm-messenger/.env
    networks:
      - alarm-network

networks:
  alarm-network:
    driver: bridge
```

**Starten:**
```bash
docker compose up -d
docker compose logs -f
```

---

## 🔧 Fehlerbehebung

### ❌ Service startet nicht

```bash
# Docker: Logs prüfen
docker compose logs alarm-mail

# Native: Systemd-Logs prüfen
sudo journalctl -u alarm-mail -f

# Konfiguration prüfen
cat .env | grep -v PASSWORD  # Ohne Passwörter
```

**Häufige Ursachen:**
- Fehlende Pflicht-Variablen (IMAP_HOST, USERNAME, PASSWORD)
- Syntax-Fehler in .env
- Port bereits belegt

### ❌ IMAP-Verbindung schlägt fehl

```bash
# Verbindung testen
telnet imap.ihremailserver.de 993

# Oder mit OpenSSL
openssl s_client -connect imap.ihremailserver.de:993

# Logs anschauen
docker compose logs alarm-mail | grep -i imap
```

**Häufige Ursachen:**
- Falsche Zugangsdaten
- Firewall blockiert Port 993
- 2FA aktiviert (App-Passwort benötigt)
- SSL/TLS-Zertifikat-Problem

**Lösungsansätze:**
```bash
# App-Passwort für Gmail/Outlook verwenden
# SSL temporär deaktivieren (nur zum Testen!)
ALARM_MAIL_IMAP_USE_SSL=false
ALARM_MAIL_IMAP_PORT=143
```

### ❌ Push zu Targets schlägt fehl

```bash
# Erreichbarkeit prüfen
curl http://alarm-monitor:8000/health
curl http://alarm-messenger:3000/api/health

# Logs checken
docker compose logs alarm-mail | grep -i "push"
docker compose logs alarm-mail | grep -i "error"
```

**Häufige Ursachen:**
- API-Keys stimmen nicht überein
- Target-Service läuft nicht
- Falsche URL (z.B. localhost statt Service-Name in Docker)

**Lösung:**
```bash
# In Docker Compose: Service-Namen verwenden!
# ✅ Richtig:
ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000

# ❌ Falsch (im Docker-Netzwerk):
ALARM_MAIL_ALARM_MONITOR_URL=http://localhost:8000
```

### ❌ E-Mails werden nicht verarbeitet

```bash
# Suchkriterium überprüfen
docker compose logs alarm-mail | grep "Searching for messages"

# Temporär alle E-Mails abrufen (zum Testen)
ALARM_MAIL_IMAP_SEARCH=ALL
```

**Mögliche Ursachen:**
- Alle E-Mails bereits gelesen (UNSEEN findet nichts)
- Falscher Mailbox-Name
- E-Mail-Format wird nicht erkannt

---

## 📚 Nächste Schritte

✅ Service läuft? Großartig! Jetzt können Sie:

1. **Dokumentation lesen**
   - [README.md](README.md) - Vollständige Dokumentation
   - Konfigurationsoptionen erkunden
   - Sicherheits-Best-Practices umsetzen

2. **Test-Alarm senden**
   - E-Mail mit Test-XML an Postfach senden
   - Logs beobachten: `docker compose logs -f alarm-mail`
   - Verarbeitung im Dashboard / Messenger prüfen

3. **Monitoring einrichten**
   - Health-Checks konfigurieren
   - Log-Rotation einrichten
   - Alerting für Fehler aufsetzen

4. **Produktion vorbereiten**
   - Starke API-Keys generieren
   - SSL/TLS für IMAP aktivieren
   - Firewall-Regeln konfigurieren
   - Backup-Strategie definieren

5. **Integrationen erweitern**
   - alarm-monitor einrichten
   - alarm-messenger konfigurieren
   - Beide Systeme gleichzeitig nutzen

---

## 💬 Hilfe benötigt?

### 📖 Dokumentation
- [README.md](README.md) - Vollständige Dokumentation
- [GitHub Repository](https://github.com/TimUx/alarm-mail)

### 🐛 Bug gefunden?
- [Issue erstellen](https://github.com/TimUx/alarm-mail/issues/new)

### 💡 Fragen?
- [GitHub Discussions](https://github.com/TimUx/alarm-mail/discussions)

### 🔗 Verwandte Projekte
- [alarm-monitor](https://github.com/TimUx/alarm-monitor) - Dashboard für Einsatzanzeige
- [alarm-messenger](https://github.com/TimUx/alarm-messenger) - Mobile Alarmierung

---

<div align="center">

**Viel Erfolg mit alarm-mail! 🚒🚨**

[⬆️ Nach oben](#-schnellstart---alarm-mail)

</div>
