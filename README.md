# 🚨 alarm-mail

**Intelligente E-Mail-Verarbeitung für Feuerwehr-Alarmierungssysteme**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

`alarm-mail` ist ein automatisierter Service, der Alarm-E-Mails aus einem IMAP-Postfach abruft, die XML-Einsatzinformationen parst und strukturiert an nachgelagerte Systeme weiterleitet. Als zentrale Schnittstelle zwischen der Leitstelle und den Alarmierungssystemen ermöglicht der Service eine flexible und skalierbare Verarbeitung von Einsatzmeldungen.

---

## 📋 Inhaltsverzeichnis

- [Überblick](#-überblick)
- [Funktionsumfang](#-funktionsumfang)
- [Architektur](#-architektur)
- [Schnellstart](#-schnellstart)
- [Installation](#-installation)
- [Konfiguration](#-konfiguration)
- [Integration](#-integration)
- [Deployment](#-deployment)
- [API-Dokumentation](#-api-dokumentation)
- [Entwicklung](#-entwicklung)
- [Sicherheit](#-sicherheit)
- [Fehlerbehebung](#-fehlerbehebung)
- [Support & Beiträge](#-support--beiträge)
- [Lizenz](#-lizenz)

---

## 🎯 Überblick

### Was macht alarm-mail?

Der **alarm-mail Service** bildet die zentrale E-Mail-Verarbeitungskomponente im Feuerwehr-Alarmierungssystem. Er:

- **Ruft automatisch** Alarm-E-Mails von einem IMAP-Server ab
- **Parst** XML-strukturierte Einsatzinformationen (INCIDENT-Format)
- **Verarbeitet** alle relevanten Einsatzdaten (Stichwort, Ort, Einheiten, etc.)
- **Verteilt** die strukturierten Daten an verschiedene Zielsysteme

### Warum alarm-mail verwenden?

✅ **Zentrale E-Mail-Verarbeitung** - Ein Service für mehrere Empfängersysteme  
✅ **Entkopplung** - Unabhängige Skalierung und Wartung der Komponenten  
✅ **Flexibilität** - Unterstützung mehrerer Zielsysteme gleichzeitig  
✅ **Sicherheit** - Verschlüsselte IMAP-Verbindung und API-Authentifizierung  
✅ **Zuverlässigkeit** - Robuste Fehlerbehandlung und strukturiertes Logging  
✅ **Einfache Bereitstellung** - Docker-Support für schnelles Setup

### Anwendungsfall

Die Leitstelle sendet Alarmmeldungen als E-Mail mit XML-Anhang an ein Postfach. Der alarm-mail Service überwacht dieses Postfach kontinuierlich, extrahiert alle relevanten Informationen und leitet sie an:

- **[alarm-monitor](https://github.com/TimUx/alarm-monitor)** - Web-Dashboard zur Einsatzanzeige
- **[alarm-messenger](https://github.com/TimUx/alarm-messenger)** - Mobile Push-Alarmierung mit Rückmeldung

---

## ⚡ Funktionsumfang

### E-Mail-Verarbeitung
- ✅ Automatisches IMAP-Polling in konfigurierbaren Intervallen
- ✅ Unterstützung für SSL/TLS-verschlüsselte Verbindungen
- ✅ Flexible Suchkriterien (UNSEEN, ALL, etc.)
- ✅ Robuste Fehlerbehandlung bei Verbindungsabbrüchen

### XML-Parsing
- ✅ Vollständige Verarbeitung des INCIDENT-XML-Formats
- ✅ Extraktion aller Einsatzinformationen:
  - Einsatznummer und Zeitstempel
  - Stichwort (Haupt- und Unterstichwort)
  - Diagnose und Bemerkungen
  - Einsatzort (Straße, Ort, Ortsteil, Koordinaten)
  - Alarmierte Einheiten (AAO)
  - Einsatzmaßnahmen (TME-Codes für Gruppenalarmierung)
- ✅ Sichere XML-Verarbeitung mit defusedxml
- ✅ Validierung und Fehlerbehandlung

### API-Integration
- ✅ Push an alarm-monitor mit strukturierten Alarmdaten
- ✅ Push an alarm-messenger im Emergency-Format
- ✅ API-Key-basierte Authentifizierung
- ✅ Automatische Format-Konvertierung für verschiedene Zielsysteme
- ✅ Gleichzeitige Unterstützung mehrerer Targets
- ✅ Fehlertoleranz bei Target-Ausfällen

### Betrieb & Monitoring
- ✅ Health-Check-Endpoint für Monitoring
- ✅ Strukturiertes Logging für einfache Fehlersuche
- ✅ Docker und Docker Compose Support
- ✅ Systemd-Service-Integration
- ✅ Konfiguration über Umgebungsvariablen
- ✅ Non-root Container-Betrieb

---

## 🏗️ Architektur

### Systemübersicht

```
┌─────────────────────────────────────────────────────────────┐
│                     Leitstelle / ILS                         │
│  Sendet Alarm-E-Mails mit XML-Einsatzinformationen         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ E-Mail (IMAP/TLS)
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  IMAP-Postfach                               │
│            (z.B. alarm@feuerwehr.de)                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ IMAP-Polling (alle 60s)
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │      🚨 alarm-mail Service            │
        │                                       │
        │  ┌─────────────────────────────────┐ │
        │  │   IMAP Fetcher                  │ │
        │  │   - Verbindung zu IMAP          │ │
        │  │   - Polling neuer E-Mails       │ │
        │  └──────────┬──────────────────────┘ │
        │             │                         │
        │             ▼                         │
        │  ┌─────────────────────────────────┐ │
        │  │   XML Parser                    │ │
        │  │   - INCIDENT-XML parsen         │ │
        │  │   - Daten extrahieren           │ │
        │  │   - Strukturieren               │ │
        │  └──────────┬──────────────────────┘ │
        │             │                         │
        │             ▼                         │
        │  ┌─────────────────────────────────┐ │
        │  │   Push Service                  │ │
        │  │   - Format-Konvertierung        │ │
        │  │   - API-Authentifizierung       │ │
        │  │   - Target-Distribution         │ │
        │  └──────────┬──────────────────────┘ │
        └─────────────┼─────────────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
         │ REST API                │ REST API
         │ (X-API-Key)             │ (X-API-Key)
         │                         │
         ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│  alarm-monitor   │      │ alarm-messenger  │
│                  │      │                  │
│  - Web-Dashboard │      │  - Mobile App    │
│  - Einsatzübersicht│    │  - Push-Alarme   │
│  - Kartendarstellung│   │  - Rückmeldung   │
│                  │      │  - Gruppierung   │
└──────────────────┘      └──────────────────┘
         │                         │
         ▼                         ▼
    Dashboard-User          Einsatzkräfte
```

### Datenfluss

1. **E-Mail-Empfang**: Leitstelle sendet Alarm-E-Mail mit XML-Inhalt
2. **Polling**: alarm-mail prüft regelmäßig auf neue ungelesene E-Mails
3. **Parsing**: XML-Struktur wird analysiert und in strukturiertes Format überführt
4. **Validierung**: Vollständigkeit und Korrektheit der Daten werden geprüft
5. **Distribution**: Daten werden an konfigurierte Zielsysteme gesendet
   - **alarm-monitor**: Empfängt vollständige Alarmdaten zur Anzeige
   - **alarm-messenger**: Empfängt Emergency-Format für mobile Alarmierung
6. **Logging**: Alle Schritte werden protokolliert für Monitoring und Debugging

### Komponenten

#### IMAP Fetcher (`mail_checker.py`)
- Verwaltet IMAP-Verbindung mit SSL/TLS
- Polling-Thread mit konfigurierbarem Intervall
- Robuste Fehlerbehandlung und Reconnect-Logik
- Unterstützung für verschiedene Zeichensätze

#### XML Parser (`parser.py`)
- Sichere XML-Verarbeitung mit defusedxml
- Extraktion aller INCIDENT-Felder
- Zeitstempel-Konvertierung ins ISO-Format
- Koordinaten-Validierung
- TME-Code-Extraktion für Gruppenalarmierung

#### Push Service (`push_service.py`)
- Format-Adaption für verschiedene Zielsysteme
- API-Key-Management
- HTTP-Client mit Timeout und Retry-Logik
- Separate Fehlerbehandlung pro Target

#### Flask App (`app.py`)
- REST-API mit Health-Check
- Service-Status-Endpunkt
- Lifecycle-Management des Polling-Threads
- Konfigurationsvalidierung beim Start

---

## 🚀 Schnellstart

Möchten Sie schnell loslegen? Folgen Sie der **[Schnellstart-Anleitung](QUICKSTART.md)** für ein Setup in 5 Minuten!

### Voraussetzungen

- **Docker & Docker Compose** (empfohlen) ODER
- **Python 3.11+** mit pip und venv
- IMAP-Postfach mit Zugangsdaten
- Optional: Laufende Instanzen von alarm-monitor und/oder alarm-messenger

### Minimale Installation (Docker)

```bash
# Repository klonen
git clone https://github.com/TimUx/alarm-mail.git
cd alarm-mail

# Konfiguration erstellen
cp .env.example .env
nano .env  # IMAP-Zugangsdaten eintragen

# Service starten
docker compose up -d

# Status prüfen
curl http://localhost:8000/health
```

✅ **Fertig!** Der Service läuft und überwacht Ihr Postfach.

Für detaillierte Installationsoptionen siehe [Installation](#-installation).

---

## 📦 Installation

Der alarm-mail Service kann auf verschiedene Arten installiert werden. Wählen Sie die für Ihre Umgebung passende Methode.

### Option 1: Docker (Empfohlen) 🐋

Docker ist die einfachste und zuverlässigste Installationsmethode.

**Vorteile:**
- Keine lokalen Abhängigkeiten außer Docker
- Konsistente Umgebung
- Einfache Updates
- Isolierte Ausführung

**Installation:**

```bash
# Repository klonen
git clone https://github.com/TimUx/alarm-mail.git
cd alarm-mail

# Konfiguration erstellen
cp .env.example .env
nano .env  # Ihre IMAP-Zugangsdaten und API-Keys eintragen

# Service bauen und starten
docker compose up -d --build

# Logs anzeigen
docker compose logs -f

# Status prüfen
curl http://localhost:8000/health

# Service stoppen
docker compose down
```

**Wichtig:** Der Container läuft als non-root User für erhöhte Sicherheit.

### Option 2: Native Python-Installation 🐍

Für direkte Installation auf dem Host-System.

**Voraussetzungen:**
- Python 3.11 oder höher
- pip und venv
- Systemzugriff für Paketinstallation

**Schritt 1: System vorbereiten**

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

**Schritt 2: Projekt klonen und Umgebung erstellen**
```bash
git clone https://github.com/TimUx/alarm-mail.git
cd alarm-mail
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Schritt 3: Konfiguration erstellen**
```bash
cp .env.example .env
nano .env  # Ihre Zugangsdaten eintragen
```

**Schritt 4: Service starten**

Für Entwicklung:
```bash
flask --app alarm_mail.app run --host 0.0.0.0 --port 8000
```

Für Produktion (mit Gunicorn):
```bash
gunicorn --bind 0.0.0.0:8000 "alarm_mail.app:create_app()" --workers 1 --threads 4
```

**Schritt 5: Als Systemd-Dienst einrichten (optional)**

Erstellen Sie `/etc/systemd/system/alarm-mail.service`:

```ini
[Unit]
Description=Feuerwehr Alarm Mail Service
After=network.target
Documentation=https://github.com/TimUx/alarm-mail

[Service]
Type=simple
User=alarm
Group=alarm
WorkingDirectory=/opt/alarm-mail
Environment="PATH=/opt/alarm-mail/.venv/bin"
EnvironmentFile=/opt/alarm-mail/.env
ExecStart=/opt/alarm-mail/.venv/bin/gunicorn --bind 0.0.0.0:8000 "alarm_mail.app:create_app()" --workers 1 --threads 4
Restart=always
RestartSec=10

# Sicherheitsoptionen
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Dienst aktivieren und starten:
```bash
sudo systemctl daemon-reload
sudo systemctl enable alarm-mail
sudo systemctl start alarm-mail
sudo systemctl status alarm-mail
```

### Option 3: Docker Build (Manuell)

Für erweiterte Kontrolle über den Container-Build.

```bash
# Image bauen
docker build -t alarm-mail:latest .

# Container starten mit Environment-Variablen
docker run -d \
  --name alarm-mail \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  alarm-mail:latest

# Logs anzeigen
docker logs -f alarm-mail

# Container stoppen
docker stop alarm-mail
docker rm alarm-mail
```

---

## ⚙️ Konfiguration

Der alarm-mail Service wird vollständig über Umgebungsvariablen konfiguriert. Alle Variablen tragen das Präfix `ALARM_MAIL_`.

### Übersicht der Konfigurationsvariablen

#### 🔴 IMAP-Konfiguration (Pflicht)

Diese Einstellungen sind zwingend erforderlich für den Betrieb des Services.

| Variable | Typ | Default | Beschreibung |
|----------|-----|---------|--------------|
| `IMAP_HOST` | String | **Pflicht** | Hostname oder IP-Adresse des IMAP-Servers<br>Beispiel: `imap.gmail.com` |
| `IMAP_USERNAME` | String | **Pflicht** | Benutzername/E-Mail für die Anmeldung<br>Beispiel: `alarm@feuerwehr.de` |
| `IMAP_PASSWORD` | String | **Pflicht** | Passwort für die Anmeldung<br>⚠️ Nie in Version Control einchecken! |
| `IMAP_PORT` | Integer | `993` | Port des IMAP-Servers<br>Standard: 993 (SSL), 143 (unverschlüsselt) |
| `IMAP_USE_SSL` | Boolean | `true` | SSL/TLS-Verschlüsselung aktivieren<br>Werte: `true` oder `false` |
| `IMAP_MAILBOX` | String | `INBOX` | Zu überwachender E-Mail-Ordner<br>Beispiel: `INBOX`, `Alarme` |
| `IMAP_SEARCH` | String | `UNSEEN` | IMAP-Suchkriterium für E-Mails<br>Werte: `UNSEEN`, `ALL`, `SINCE`, etc. |
| `POLL_INTERVAL` | Integer | `60` | Abrufintervall in Sekunden<br>Minimum: 10, empfohlen: 60 |

#### 📊 Alarm Monitor Integration (Optional)

Aktiviert die Weiterleitung an das [alarm-monitor](https://github.com/TimUx/alarm-monitor) Dashboard.

| Variable | Typ | Beschreibung |
|----------|-----|--------------|
| `ALARM_MONITOR_URL` | String | Basis-URL des alarm-monitor<br>Beispiel: `http://alarm-monitor:8000` oder `https://monitor.feuerwehr.de`<br>⚠️ Muss zusammen mit `ALARM_MONITOR_API_KEY` gesetzt sein |
| `ALARM_MONITOR_API_KEY` | String | API-Schlüssel für Authentifizierung<br>Wird vom alarm-monitor über `ALARM_DASHBOARD_API_KEY` definiert<br>⚠️ Geheim halten! |
| `ALARM_MONITOR_VERIFY_SSL` | Boolean | SSL-Zertifikat des alarm-monitor prüfen<br>Standard: `true`. Nur für selbstsignierte Zertifikate deaktivieren. |

**Hinweis:** `ALARM_MONITOR_URL` und `ALARM_MONITOR_API_KEY` müssen beide gesetzt sein, damit die Integration aktiv ist.

#### 📱 Alarm Messenger Integration (Optional)

Aktiviert die Weiterleitung an den [alarm-messenger](https://github.com/TimUx/alarm-messenger) für mobile Alarmierung.

| Variable | Typ | Beschreibung |
|----------|-----|--------------|
| `ALARM_MESSENGER_URL` | String | Basis-URL des alarm-messenger<br>Beispiel: `http://alarm-messenger:3000` oder `https://messenger.feuerwehr.de`<br>⚠️ Muss zusammen mit `ALARM_MESSENGER_API_KEY` gesetzt sein |
| `ALARM_MESSENGER_API_KEY` | String | API-Schlüssel für Authentifizierung<br>Wird vom alarm-messenger über `API_SECRET_KEY` definiert<br>⚠️ Geheim halten! |
| `ALARM_MESSENGER_VERIFY_SSL` | Boolean | SSL-Zertifikat des alarm-messenger prüfen<br>Standard: `true`. Nur für selbstsignierte Zertifikate deaktivieren. |

**Hinweis:** `ALARM_MESSENGER_URL` und `ALARM_MESSENGER_API_KEY` müssen beide gesetzt sein, damit die Integration aktiv ist.

#### 🎯 Multi-Target-Konfiguration – mehrere Instanzen mit Gruppenfilter (Optional)

Wenn mehrere alarm-monitor-Instanzen an verschiedenen Standorten betrieben werden (z. B. verschiedene Feuerwachen mit unterschiedlichen Alarmierungsgruppen), kann jeder Empfänger über nummerierte Variablen `TARGET_<N>_*` konfiguriert werden.

**Vorteile gegenüber den Legacy-Variablen:**
- Beliebig viele Targets konfigurierbar (N = 1, 2, 3, …)
- Jeder Target erhält optional einen **Gruppenfilter**: nur Alarme mit passenden Dispatch-Codes werden weitergeleitet
- **E-Mails werden nur als gelesen markiert**, wenn mindestens ein Target den Alarm tatsächlich erhalten hat

| Variable | Typ | Beschreibung |
|----------|-----|--------------|
| `TARGET_<N>_URL` | String | Basis-URL des Targets (Pflicht für Target N) |
| `TARGET_<N>_API_KEY` | String | API-Schlüssel des Targets ⚠️ Geheim halten! |
| `TARGET_<N>_TYPE` | String | Typ: `alarm-monitor` (Standard) oder `alarm-messenger` |
| `TARGET_<N>_GROUPS` | String | Kommaseparierte Dispatch-Codes (z. B. `WIL28,WIL29`)<br>Leer lassen = kein Filter, alle Alarme werden weitergeleitet |
| `TARGET_<N>_VERIFY_SSL` | Boolean | SSL-Zertifikat prüfen. Standard: `true` |

**Verhalten bei Gruppenfilter:**
- Alarm-Dispatch-Codes (aus `<TME>/<BEZEICHNUNG>`) werden **case-insensitiv** gegen die konfigurierten Gruppen geprüft.
- Wenn kein Target den Alarm empfängt (alle Filter greifen), bleibt die E-Mail **ungelesen** im Postfach. Beim nächsten Poll-Zyklus wird sie erneut verarbeitet, sofern neue Targets konfiguriert werden.
- E-Mails ohne valides `<INCIDENT>`-XML werden immer als gelesen markiert (kein Alarm → Posteingang aufräumen).

#### ⚙️ Weitere optionale Einstellungen

| Variable | Typ | Default | Beschreibung |
|----------|-----|---------|--------------|
| `HTTP_TIMEOUT` | Integer | `10` | Timeout in Sekunden für ausgehende HTTP-Requests an Targets |
| `LOG_LEVEL` | String | `INFO` | Log-Level des Service<br>Werte: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `DEDUP_TTL` | Integer | `300` | Gültigkeitsdauer (Sekunden) für die Duplikat-Erkennung anhand der Einsatznummer |
| `DEDUP_DB` | String | – | Optionaler Pfad zu einer SQLite-Datei für persistente Duplikat-Erkennung (überlebt Neustarts) |

### Konfigurationsbeispiele

#### Minimal-Konfiguration (nur IMAP)

```bash
# Nur E-Mail-Parsing, keine Weiterleitung
ALARM_MAIL_IMAP_HOST=imap.mailserver.de
ALARM_MAIL_IMAP_USERNAME=alarm@feuerwehr.de
ALARM_MAIL_IMAP_PASSWORD=geheimes-passwort
```

#### Standard-Konfiguration (mit alarm-monitor)

```bash
# IMAP Konfiguration
ALARM_MAIL_IMAP_HOST=imap.mailserver.de
ALARM_MAIL_IMAP_PORT=993
ALARM_MAIL_IMAP_USE_SSL=true
ALARM_MAIL_IMAP_USERNAME=alarm@feuerwehr.de
ALARM_MAIL_IMAP_PASSWORD=geheimes-passwort
ALARM_MAIL_IMAP_MAILBOX=INBOX
ALARM_MAIL_IMAP_SEARCH=UNSEEN
ALARM_MAIL_POLL_INTERVAL=60

# Alarm Monitor Integration
ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000
ALARM_MAIL_ALARM_MONITOR_API_KEY=monitor-secret-key-123
```

#### Vollständige Konfiguration (beide Integrationen)

```bash
# IMAP Konfiguration
ALARM_MAIL_IMAP_HOST=imap.mailserver.de
ALARM_MAIL_IMAP_PORT=993
ALARM_MAIL_IMAP_USE_SSL=true
ALARM_MAIL_IMAP_USERNAME=alarm@feuerwehr.de
ALARM_MAIL_IMAP_PASSWORD=geheimes-passwort
ALARM_MAIL_IMAP_MAILBOX=INBOX
ALARM_MAIL_IMAP_SEARCH=UNSEEN
ALARM_MAIL_POLL_INTERVAL=60

# Alarm Monitor Integration
ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000
ALARM_MAIL_ALARM_MONITOR_API_KEY=monitor-secret-key-123

# Alarm Messenger Integration
ALARM_MAIL_ALARM_MESSENGER_URL=http://alarm-messenger:3000
ALARM_MAIL_ALARM_MESSENGER_API_KEY=messenger-secret-key-456
```

#### Multi-Target-Konfiguration (mehrere alarm-monitor-Instanzen)

Zwei alarm-monitor-Instanzen an verschiedenen Standorten, jede nur für ihre Alarmierungsgruppen, plus ein alarm-messenger ohne Gruppenfilter:

```bash
# IMAP Konfiguration
ALARM_MAIL_IMAP_HOST=imap.mailserver.de
ALARM_MAIL_IMAP_USERNAME=alarm@feuerwehr.de
ALARM_MAIL_IMAP_PASSWORD=geheimes-passwort

# Standort 1: Zuständig für WIL28 und WIL29
ALARM_MAIL_TARGET_1_TYPE=alarm-monitor
ALARM_MAIL_TARGET_1_URL=https://monitor-standort1.feuerwehr.de
ALARM_MAIL_TARGET_1_API_KEY=key-standort1
ALARM_MAIL_TARGET_1_GROUPS=WIL28,WIL29

# Standort 2: Zuständig für WIL30 und WIL31
ALARM_MAIL_TARGET_2_TYPE=alarm-monitor
ALARM_MAIL_TARGET_2_URL=https://monitor-standort2.feuerwehr.de
ALARM_MAIL_TARGET_2_API_KEY=key-standort2
ALARM_MAIL_TARGET_2_GROUPS=WIL30,WIL31

# Messenger: empfängt alle Alarme (kein Gruppenfilter)
ALARM_MAIL_TARGET_3_TYPE=alarm-messenger
ALARM_MAIL_TARGET_3_URL=https://messenger.feuerwehr.de
ALARM_MAIL_TARGET_3_API_KEY=key-messenger
```

> **Hinweis:** E-Mails werden nur als gelesen markiert, wenn mindestens ein Target den Alarm empfangen hat. Wenn kein Target für die Alarmgruppen des Einsatzes zuständig ist, bleibt die E-Mail ungelesen und wird beim nächsten Poll-Zyklus erneut geprüft.

### Sicherheitshinweise für die Konfiguration

⚠️ **Wichtig:**

1. **Niemals** Passwörter oder API-Keys in Git committen
2. Verwenden Sie `.env` für lokale Entwicklung (bereits in `.gitignore`)
3. In Produktion: Nutzen Sie Docker Secrets oder Vault-Systeme
4. API-Keys sollten mindestens 32 Zeichen lang sein
5. Rotieren Sie Secrets regelmäßig (empfohlen: alle 90 Tage)

**Generierung sicherer API-Keys:**
```bash
# Linux/macOS
openssl rand -hex 32

# Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🔗 Integration

Der alarm-mail Service fungiert als zentrale Schnittstelle und kann mit verschiedenen Zielsystemen integriert werden.

### Integration mit alarm-monitor

Der **[alarm-monitor](https://github.com/TimUx/alarm-monitor)** ist ein Web-Dashboard zur Visualisierung von Einsätzen mit Kartendarstellung.

#### Datenfluss

```
alarm-mail  →  POST /api/alarm  →  alarm-monitor
            ↓
    Vollständige Alarmdaten (JSON)
            ↓
    {
      "incident_number": "2024-001",
      "timestamp": "2024-12-08T14:30:00",
      "keyword": "BRAND 3 – Wohnungsbrand",
      "location": "Hauptstraße 123, Musterstadt",
      "latitude": 51.2345,
      "longitude": 9.8765,
      "groups": [...],
      ...
    }
```

#### Konfiguration alarm-mail

```bash
ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000
ALARM_MAIL_ALARM_MONITOR_API_KEY=ihr-geheimer-monitor-key
```

#### Konfiguration alarm-monitor

Der alarm-monitor muss einen API-Endpunkt bereitstellen. Beispiel-Implementation:

```python
@app.route("/api/alarm", methods=["POST"])
def api_alarm():
    """Receive alarm data from alarm-mail service."""
    # API-Key-Authentifizierung
    api_key = request.headers.get("X-API-Key")
    expected_key = os.environ.get("ALARM_DASHBOARD_API_KEY")
    
    if not api_key or api_key != expected_key:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Alarm-Daten verarbeiten
    alarm_data = request.get_json()
    
    # Alarm speichern und anzeigen
    # ... Ihre Logik hier ...
    
    return jsonify({"status": "ok", "message": "Alarm received"}), 200
```

Umgebungsvariable in alarm-monitor `.env`:
```bash
ALARM_DASHBOARD_API_KEY=ihr-geheimer-monitor-key
```

**Wichtig:** Der API-Key muss in beiden Services identisch sein!

#### Übertragene Datenfelder

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `incident_number` | String | Einsatznummer der Leitstelle |
| `timestamp` | String (ISO) | Zeitpunkt des Alarms |
| `timestamp_display` | String | Formatierter Zeitstempel zur Anzeige |
| `keyword` | String | Kombiniertes Stichwort für Anzeige |
| `keyword_primary` | String | Hauptstichwort (z.B. "F3Y") |
| `keyword_secondary` | String | Unterstichwort |
| `diagnosis` | String | Einsatzdiagnose |
| `remark` | String | Bemerkungen zum Einsatz |
| `location` | String | Vollständige Ortsangabe |
| `location_details` | Object | Strukturierte Ortsinformationen |
| `latitude` | Float | Breitengrad (WGS84) |
| `longitude` | Float | Längengrad (WGS84) |
| `groups` | Array | Liste aller Einheiten (AAO + TME) |
| `aao_groups` | Array | Alarmierte Einheiten (AAO) |
| `dispatch_groups` | Array | Einsatzmaßnahmen (TME) |
| `dispatch_group_codes` | Array | Extrahierte TME-Codes |
| `subject` | String | E-Mail-Betreff |

### Integration mit alarm-messenger

Der **[alarm-messenger](https://github.com/TimUx/alarm-messenger)** ermöglicht die mobile Alarmierung von Einsatzkräften mit Push-Benachrichtigungen und Rückmeldung.

#### Datenfluss

```
alarm-mail  →  POST /api/emergencies  →  alarm-messenger
            ↓
    Emergency-Format (JSON)
            ↓
    {
      "emergencyNumber": "2024-001",
      "emergencyDate": "2024-12-08T14:30:00",
      "emergencyKeyword": "F3Y",
      "emergencyDescription": "Wohnungsbrand",
      "emergencyLocation": "Hauptstraße 123, Musterstadt",
      "groups": "WIL26,WIL41"  // Optional für Gruppenalarmierung
    }
```

#### Konfiguration alarm-mail

```bash
ALARM_MAIL_ALARM_MESSENGER_URL=http://alarm-messenger:3000
ALARM_MAIL_ALARM_MESSENGER_API_KEY=ihr-geheimer-messenger-key
```

#### Konfiguration alarm-messenger

Umgebungsvariable in alarm-messenger `.env`:
```bash
API_SECRET_KEY=ihr-geheimer-messenger-key
```

**Wichtig:** Der API-Key muss in beiden Services identisch sein!

#### Format-Konvertierung

Der alarm-mail Service konvertiert die XML-Daten automatisch in das von alarm-messenger erwartete Format:

| alarm-mail (Intern) | alarm-messenger (API) |
|---------------------|----------------------|
| `incident_number` | `emergencyNumber` |
| `timestamp` | `emergencyDate` |
| `keyword_primary` | `emergencyKeyword` |
| `diagnosis` | `emergencyDescription` |
| `location` | `emergencyLocation` |
| `dispatch_group_codes` | `groups` (optional) |

#### Gruppenalarmierung

Wenn in der XML TME-Codes vorhanden sind, werden diese extrahiert und als `groups` übergeben:

**Beispiel XML:**
```xml
<EINSATZMASSNAHMEN>
  <TME>
    <BEZEICHNUNG>Wilersdorf 1 (TME WIL26)</BEZEICHNUNG>
    <BEZEICHNUNG>Wilersdorf 2 (TME WIL41)</BEZEICHNUNG>
  </TME>
</EINSATZMASSNAHMEN>
```

**Resultat:**
```json
{
  "groups": "WIL26,WIL41"
}
```

Der alarm-messenger nutzt diese Codes zur selektiven Alarmierung der entsprechenden Gruppen.

### Gleichzeitige Integration beider Systeme

Sie können alarm-mail gleichzeitig mit beiden Systemen betreiben:

```bash
# Beide Integrationen aktiv
ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000
ALARM_MAIL_ALARM_MONITOR_API_KEY=monitor-key

ALARM_MAIL_ALARM_MESSENGER_URL=http://alarm-messenger:3000
ALARM_MAIL_ALARM_MESSENGER_API_KEY=messenger-key
```

**Vorteile:**
- Redundante Alarmierung
- Dashboard-Anzeige + Mobile Alarmierung
- Unabhängige Fehlerbehandlung (Ausfall eines Systems beeinträchtigt das andere nicht)

**Beispiel-Szenario:**
1. Alarm-E-Mail wird empfangen
2. alarm-mail parst die Daten
3. Push an **alarm-monitor** → Dashboard zeigt Einsatz an
4. Push an **alarm-messenger** → Einsatzkräfte werden per Push benachrichtigt
5. Beide Systeme arbeiten unabhängig

---

## 📡 API-Dokumentation

Der alarm-mail Service stellt drei REST-Endpunkte bereit.

### GET /health

**Health-Check-Endpunkt** für Monitoring und Load Balancer.

**Request:**
```bash
curl http://localhost:8000/health
```

**Response:** `200 OK`
```json
{
  "status": "ok",
  "polling": "running",
  "service": "alarm-mail"
}
```

**Response:** `503 Service Unavailable` (wenn der Polling-Thread nicht läuft)
```json
{
  "status": "degraded",
  "polling": "stopped",
  "service": "alarm-mail"
}
```

**Verwendung:**
- Docker Health-Checks
- Kubernetes Liveness/Readiness Probes
- Monitoring-Systeme (Prometheus, Nagios, etc.)
- Load Balancer Health-Checks

**Beispiel Docker Health-Check:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
  CMD curl --fail http://localhost:8000/health || exit 1
```

### GET /

**Service-Status-Endpunkt** mit erweiterten Informationen.

**Request:**
```bash
curl http://localhost:8000/
```

**Response:** `200 OK`
```json
{
  "service": "alarm-mail",
  "status": "running",
  "targets": ["alarm-monitor", "alarm-messenger"],
  "poll_interval": 60
}
```

**Response-Felder:**

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `service` | String | Servicename (immer "alarm-mail") |
| `status` | String | Aktueller Status (immer "running") |
| `targets` | Array | Liste der konfigurierten Zielsysteme |
| `poll_interval` | Integer | Konfiguriertes Polling-Intervall in Sekunden |

**Beispiel - Nur alarm-monitor konfiguriert:**
```json
{
  "service": "alarm-mail",
  "status": "running",
  "targets": ["alarm-monitor"],
  "poll_interval": 60
}
```

**Beispiel - Keine Targets konfiguriert:**
```json
{
  "service": "alarm-mail",
  "status": "running",
  "targets": [],
  "poll_interval": 60
}
```

### GET /metrics

**Prometheus-kompatibler Metriken-Endpunkt** im Plain-Text-Format.

**Request:**
```bash
curl http://localhost:8000/metrics
```

**Response:** `200 OK` (`text/plain; version=0.0.4`)
```
# HELP alarm_mail_messages_processed_total Total number of emails processed
# TYPE alarm_mail_messages_processed_total counter
alarm_mail_messages_processed_total 42

# HELP alarm_mail_push_success_total Successful pushes per target
# TYPE alarm_mail_push_success_total counter
alarm_mail_push_success_total{target="alarm-monitor"} 40
alarm_mail_push_success_total{target="alarm-messenger"} 41

# HELP alarm_mail_push_failure_total Failed pushes per target
# TYPE alarm_mail_push_failure_total counter
alarm_mail_push_failure_total{target="alarm-monitor"} 2
alarm_mail_push_failure_total{target="alarm-messenger"} 1

# HELP alarm_mail_last_poll_timestamp_seconds Unix timestamp of last successful poll
# TYPE alarm_mail_last_poll_timestamp_seconds gauge
alarm_mail_last_poll_timestamp_seconds 1749123456.789
```

**Verfügbare Metriken:**

| Metrik | Typ | Beschreibung |
|--------|-----|--------------|
| `alarm_mail_messages_processed_total` | Counter | Gesamtanzahl der verarbeiteten E-Mails seit Start |
| `alarm_mail_push_success_total` | Counter | Erfolgreiche API-Pushes, aufgeschlüsselt nach Target |
| `alarm_mail_push_failure_total` | Counter | Fehlgeschlagene API-Pushes, aufgeschlüsselt nach Target |
| `alarm_mail_last_poll_timestamp_seconds` | Gauge | Unix-Timestamp des letzten erfolgreichen IMAP-Polls |

**Prometheus-Konfiguration:**
```yaml
- job_name: 'alarm-mail'
  static_configs:
    - targets: ['alarm-mail:8000']
  metrics_path: /metrics
```

---

## 📧 E-Mail-Format-Spezifikation

Der alarm-mail Service erwartet E-Mails mit XML-strukturierten Einsatzinformationen im `<INCIDENT>`-Format. Dieses Format wird von vielen Leitstellen-Systemen in Deutschland verwendet.

### Unterstützte XML-Struktur

**Vollständiges Beispiel:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<INCIDENT>
  <!-- Einsatz-Stichwörter -->
  <STICHWORT>F3Y</STICHWORT>
  <ESTICHWORT_1>F3Y</ESTICHWORT_1>
  <ESTICHWORT_2>Personen in Gefahr</ESTICHWORT_2>
  
  <!-- Einsatz-Identifikation -->
  <ENR>7850001123</ENR>
  <EBEGINN>08.12.2024 14:30:00</EBEGINN>
  
  <!-- Einsatz-Informationen -->
  <DIAGNOSE>Brand in Wohngebäude</DIAGNOSE>
  <EO_BEMERKUNG>Starke Rauchentwicklung im 2. OG</EO_BEMERKUNG>
  
  <!-- Einsatzort -->
  <ORT>Musterstadt</ORT>
  <ORTSTEIL>Nordviertel</ORTSTEIL>
  <STRASSE>Hauptstraße</STRASSE>
  <HAUSNUMMER>123</HAUSNUMMER>
  <OBJEKT>Mehrfamilienhaus</OBJEKT>
  <ORTSZUSATZ>Hintereingang</ORTSZUSATZ>
  
  <!-- Koordinaten (WGS84) -->
  <KOORDINATE_LAT>51.2345</KOORDINATE_LAT>
  <KOORDINATE_LON>9.8765</KOORDINATE_LON>
  
  <!-- Alarmierte Einheiten (AAO) -->
  <AAO>LF Musterstadt 1;DLK Musterstadt;ELW 1</AAO>
  
  <!-- Einsatzmaßnahmen / TME-Codes -->
  <EINSATZMASSNAHMEN>
    <TME>
      <BEZEICHNUNG>Musterstadt Nord 1 (TME MUS11)</BEZEICHNUNG>
      <BEZEICHNUNG>Musterstadt Innenstadt (TME MUS05)</BEZEICHNUNG>
      <BEZEICHNUNG>Nachbarort Zentrum (TME NAC22)</BEZEICHNUNG>
    </TME>
  </EINSATZMASSNAHMEN>
</INCIDENT>
```

### XML-Feld-Referenz

| XML-Feld | Pflicht | Beschreibung | Beispiel |
|----------|---------|--------------|----------|
| `<STICHWORT>` | Nein | Allgemeines Stichwort | `F3Y`, `TH1` |
| `<ESTICHWORT_1>` | Nein | Hauptstichwort (bevorzugt) | `F3Y` |
| `<ESTICHWORT_2>` | Nein | Unterstichwort | `Personen in Gefahr` |
| `<ENR>` | Ja | Einsatznummer | `7850001123` |
| `<EBEGINN>` | Ja | Einsatzbeginn | `08.12.2024 14:30:00` |
| `<DIAGNOSE>` | Nein | Einsatzdiagnose | `Brand in Wohngebäude` |
| `<EO_BEMERKUNG>` | Nein | Bemerkungen | `Starke Rauchentwicklung` |
| `<EOZUSATZ>` | Nein | Alternative zu EO_BEMERKUNG | |
| `<ORT>` | Ja | Ortsname | `Musterstadt` |
| `<ORTSTEIL>` | Nein | Ortsteil | `Nordviertel` |
| `<STRASSE>` | Nein | Straßenname | `Hauptstraße` |
| `<HAUSNUMMER>` | Nein | Hausnummer | `123`, `45a` |
| `<OBJEKT>` | Nein | Objektbezeichnung | `Mehrfamilienhaus` |
| `<ORTSZUSATZ>` | Nein | Zusatzinformationen | `Hintereingang` |
| `<KOORDINATE_LAT>` | Nein | Breitengrad (WGS84) | `51.2345` |
| `<KOORDINATE_LON>` | Nein | Längengrad (WGS84) | `9.8765` |
| `<AAO>` | Nein | Alarmierte Einheiten (AAO) | `LF 1;DLK;ELW` |
| `<EINSATZMASSNAHMEN>` | Nein | Container für TME | siehe unten |

### AAO-Format (Alarmierte Einheiten)

Die AAO (Alarm- und Ausrückeordnung) listet die alarmierten Fahrzeuge/Einheiten auf:

```xml
<AAO>Löschzug Musterstadt;Drehleiter;Einsatzleitwagen;RW</AAO>
```

- Trennung durch **Semikolon** (`;`)
- Wird als Liste gespeichert: `["Löschzug Musterstadt", "Drehleiter", "Einsatzleitwagen", "RW"]`

### TME-Format (Einsatzmaßnahmen / Gruppen)

TME-Codes werden für die Gruppenalarmierung verwendet:

```xml
<EINSATZMASSNAHMEN>
  <TME>
    <BEZEICHNUNG>Musterstadt Nord 1 (TME MUS11)</BEZEICHNUNG>
    <BEZEICHNUNG>Musterstadt Süd (TME MUS22)</BEZEICHNUNG>
  </TME>
</EINSATZMASSNAHMEN>
```

**Code-Extraktion:**
- Der Service extrahiert Codes im Format: `[A-Z]+[0-9]+`
- Aus `Musterstadt Nord 1 (TME MUS11)` wird: `MUS11`
- Mehrere Codes werden als kommaseparierte Liste weitergegeben: `MUS11,MUS22`

**Verwendung:**
- alarm-messenger nutzt diese Codes zur selektiven Alarmierung
- Nur Mitglieder der entsprechenden Gruppen werden benachrichtigt

### Zeitstempel-Format

Unterstützte Formate für `<EBEGINN>`:

```
08.12.2024 14:30:00  →  2024-12-08T14:30:00 (ISO 8601)
08.12.2024 14:30     →  2024-12-08T14:30:00 (ISO 8601)
```

Der Service konvertiert automatisch in ISO 8601 Format für einheitliche Weiterverarbeitung.

### Minimal-Beispiel

Minimal erforderliche XML-Struktur für erfolgreiche Verarbeitung:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<INCIDENT>
  <ENR>2024-001</ENR>
  <EBEGINN>08.12.2024 14:30:00</EBEGINN>
  <ESTICHWORT_1>F3Y</ESTICHWORT_1>
  <ORT>Musterstadt</ORT>
</INCIDENT>
```

---

## 🚀 Deployment

### Deployment-Szenarien

Je nach Infrastruktur und Anforderungen gibt es verschiedene Deployment-Möglichkeiten.

#### Szenario 1: All-in-One mit Docker Compose

**Ideal für:** Kleine bis mittlere Feuerwehren, Test-Umgebungen

Alle Services (alarm-mail, alarm-monitor, alarm-messenger) laufen zusammen auf einem Host.

**Vorteile:**
- Einfaches Setup
- Alle Services in einem Netzwerk
- Gemeinsames Management
- Ressourcensparend

**Verzeichnisstruktur:**
```
feuerwehr-alarm/
├── alarm-mail/          # Dieses Repository
├── alarm-monitor/       # Dashboard Repository
├── alarm-messenger/     # Messenger Repository
└── docker-compose.yaml  # Zentrale Compose-Datei
```

**Gemeinsame `docker-compose.yaml`:**

```yaml
version: '3.8'

services:
  alarm-mail:
    build: ./alarm-mail
    restart: unless-stopped
    environment:
      # IMAP Konfiguration
      - ALARM_MAIL_IMAP_HOST=${IMAP_HOST}
      - ALARM_MAIL_IMAP_USERNAME=${IMAP_USERNAME}
      - ALARM_MAIL_IMAP_PASSWORD=${IMAP_PASSWORD}
      - ALARM_MAIL_IMAP_MAILBOX=INBOX
      - ALARM_MAIL_POLL_INTERVAL=60
      # Targets
      - ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000
      - ALARM_MAIL_ALARM_MONITOR_API_KEY=${API_KEY_SHARED}
      - ALARM_MAIL_ALARM_MESSENGER_URL=http://alarm-messenger:3000
      - ALARM_MAIL_ALARM_MESSENGER_API_KEY=${API_KEY_SHARED}
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
    environment:
      - ALARM_DASHBOARD_API_KEY=${API_KEY_SHARED}
    volumes:
      - monitor-data:/app/data
    networks:
      - alarm-network

  alarm-messenger:
    build: ./alarm-messenger/server
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - API_SECRET_KEY=${API_KEY_SHARED}
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/messenger
    depends_on:
      - postgres
    networks:
      - alarm-network

  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_DB=messenger
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - alarm-network

volumes:
  monitor-data:
  postgres-data:

networks:
  alarm-network:
    driver: bridge
```

**`.env` Datei für Compose:**
```bash
# IMAP Zugangsdaten
IMAP_HOST=imap.mailserver.de
IMAP_USERNAME=alarm@feuerwehr.de
IMAP_PASSWORD=geheimes-passwort

# Gemeinsamer API-Key für alle Services
API_KEY_SHARED=ihr-sehr-geheimer-api-key-min-32-zeichen
```

**Starten:**
```bash
docker compose up -d
docker compose logs -f
```

#### Szenario 2: Getrennte Server (Verteiltes Setup)

**Ideal für:** Größere Organisationen, Hochverfügbarkeit

Services laufen auf separaten Servern mit externer Kommunikation.

**Architektur:**
```
Server 1 (alarm-mail)     →  HTTPS  →  Server 2 (alarm-monitor)
                          →  HTTPS  →  Server 3 (alarm-messenger)
```

**Vorteile:**
- Unabhängige Skalierung
- Höhere Verfügbarkeit
- Getrennte Wartungsfenster
- Bessere Lastverteilung

**Konfiguration alarm-mail:**
```bash
# Externe HTTPS-URLs verwenden
ALARM_MAIL_ALARM_MONITOR_URL=https://monitor.feuerwehr.de
ALARM_MAIL_ALARM_MESSENGER_URL=https://messenger.feuerwehr.de
```

**Wichtig:** 
- Nutzen Sie HTTPS für externe Kommunikation
- Firewall-Regeln für API-Zugriffe einrichten
- API-Keys über sichere Kanäle austauschen

#### Szenario 3: Standalone alarm-mail

**Ideal für:** Entwicklung, Testing, spätere Integration

Nur alarm-mail läuft, keine Weiterleitung an Targets.

**Konfiguration:**
```bash
# Nur IMAP konfigurieren
ALARM_MAIL_IMAP_HOST=imap.mailserver.de
ALARM_MAIL_IMAP_USERNAME=alarm@feuerwehr.de
ALARM_MAIL_IMAP_PASSWORD=geheim

# Keine Target-URLs setzen
# Alarme werden geparst aber nicht weitergeleitet
```

**Verwendung:**
- Testen der E-Mail-Verarbeitung
- Validierung des XML-Formats
- Log-Analyse ohne Live-Alarmierung

#### Szenario 4: Kubernetes Deployment

**Ideal für:** Enterprise-Umgebungen, Cloud-Deployment

**Beispiel Deployment:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alarm-mail
  namespace: feuerwehr
spec:
  replicas: 1
  selector:
    matchLabels:
      app: alarm-mail
  template:
    metadata:
      labels:
        app: alarm-mail
    spec:
      containers:
      - name: alarm-mail
        image: alarm-mail:latest
        ports:
        - containerPort: 8000
        env:
        - name: ALARM_MAIL_IMAP_HOST
          valueFrom:
            secretKeyRef:
              name: alarm-mail-secrets
              key: imap-host
        - name: ALARM_MAIL_IMAP_USERNAME
          valueFrom:
            secretKeyRef:
              name: alarm-mail-secrets
              key: imap-username
        - name: ALARM_MAIL_IMAP_PASSWORD
          valueFrom:
            secretKeyRef:
              name: alarm-mail-secrets
              key: imap-password
        - name: ALARM_MAIL_ALARM_MONITOR_URL
          value: "http://alarm-monitor:8000"
        - name: ALARM_MAIL_ALARM_MONITOR_API_KEY
          valueFrom:
            secretKeyRef:
              name: alarm-mail-secrets
              key: monitor-api-key
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: alarm-mail
  namespace: feuerwehr
spec:
  selector:
    app: alarm-mail
  ports:
  - port: 8000
    targetPort: 8000
```

### Reverse Proxy Setup

Für externen Zugriff empfiehlt sich ein Reverse Proxy (nginx, Traefik, etc.).

**Beispiel nginx-Konfiguration:**

```nginx
server {
    listen 443 ssl http2;
    server_name alarm-mail.feuerwehr.de;

    ssl_certificate /etc/ssl/certs/alarm-mail.crt;
    ssl_certificate_key /etc/ssl/private/alarm-mail.key;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Backup-Strategie

**Was sollte gesichert werden:**

1. **Konfiguration** (`.env` Dateien)
   - Regelmäßige verschlüsselte Backups
   - Sichere Aufbewahrung außerhalb des Servers

2. **Logs** (optional)
   - Für Compliance und Debugging
   - Rotation nach 30-90 Tagen

3. **Keine E-Mail-Inhalte**
   - alarm-mail speichert keine E-Mails
   - Nur Parsing und Weiterleitung

**Backup-Beispiel:**
```bash
#!/bin/bash
# Backup-Script
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf backup-alarm-mail-${DATE}.tar.gz .env docker-compose.yaml
gpg -c backup-alarm-mail-${DATE}.tar.gz
rm backup-alarm-mail-${DATE}.tar.gz
```

---

## 📊 Monitoring & Logging

### Log-Ausgabe

Der Service nutzt strukturiertes Logging mit verschiedenen Log-Levels.

**Log-Format:**
```
2024-12-08 14:30:00 - alarm_mail.mail_checker - INFO - Fetching new message UID 123
2024-12-08 14:30:01 - alarm_mail.parser - INFO - Parsed alarm: 2024-001 - F3Y
2024-12-08 14:30:02 - alarm_mail.push_service - INFO - Successfully pushed alarm to alarm-monitor
```

**Logs anzeigen:**

Docker:
```bash
# Live-Logs
docker compose logs -f alarm-mail

# Nur Fehler
docker compose logs alarm-mail | grep ERROR

# Letzte 100 Zeilen
docker compose logs --tail=100 alarm-mail
```

Systemd:
```bash
# Live-Logs
sudo journalctl -u alarm-mail -f

# Nur heute
sudo journalctl -u alarm-mail --since today

# Nur Fehler
sudo journalctl -u alarm-mail -p err
```

### Health-Checks

**Manueller Check:**
```bash
curl http://localhost:8000/health

# Expected: {"status":"ok","polling":"running","service":"alarm-mail"}
```

**Automatisches Monitoring mit Prometheus:**

Der Service stellt einen nativen `/metrics`-Endpunkt bereit. Dieser liefert Counters für verarbeitete E-Mails, Push-Erfolge und Push-Fehler sowie einen Timestamp des letzten Polls (siehe [API-Dokumentation](#-api-dokumentation)).

**Prometheus-Konfiguration:**
```yaml
- job_name: 'alarm-mail'
  static_configs:
    - targets: ['alarm-mail:8000']
  metrics_path: /metrics
```

**Shell-Script für Monitoring:**
```bash
#!/bin/bash
# check-alarm-mail.sh

HEALTH_URL="http://localhost:8000/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ "$RESPONSE" != "200" ]; then
    echo "CRITICAL - alarm-mail health check failed (HTTP $RESPONSE)"
    exit 2
fi

echo "OK - alarm-mail is running"
exit 0
```

### Monitoring-Integration

**Nagios/Icinga:**
```bash
check_http -H localhost -p 8000 -u /health -s "ok"
```

**Prometheus (nativer `/metrics`-Endpunkt):**
```yaml
- job_name: 'alarm-mail'
  static_configs:
    - targets: ['alarm-mail:8000']
  metrics_path: /metrics
```

**Uptime Kuma:**
- Monitor-Typ: HTTP(s)
- URL: `http://alarm-mail:8000/health`
- Intervall: 60 Sekunden
- Expected Status: 200

---

## 🔧 Entwicklung

### Projekt-Setup für Entwickler

```bash
# Repository klonen
git clone https://github.com/TimUx/alarm-mail.git
cd alarm-mail

# Virtual Environment erstellen
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Dependencies installieren
pip install -r requirements.txt

# Development Dependencies (optional)
pip install pytest pytest-cov black flake8 mypy
```

### Projektstruktur

```
alarm-mail/
├── alarm_mail/              # Hauptanwendung (Python Package)
│   ├── __init__.py         # Package-Initialisierung
│   ├── app.py              # Flask-Applikation & Lifecycle
│   ├── config.py           # Konfigurationsverwaltung
│   ├── mail_checker.py     # IMAP-Polling-Thread
│   ├── parser.py           # XML-Parsing-Logik
│   └── push_service.py     # API-Push-Service
│
├── tests/                   # Unit Tests
│   ├── test_app.py         # Tests für Flask App
│   ├── test_config.py      # Tests für Konfiguration
│   ├── test_mail_checker.py# Tests für IMAP-Fetcher
│   ├── test_parser.py      # Tests für XML-Parser
│   └── test_push_service.py# Tests für Push Service
│
├── docs/                    # Dokumentation (erweitert)
│   ├── images/             # Screenshots & Diagramme
│   └── examples/           # Beispiel-Konfigurationen
│
├── .env.example            # Beispiel-Konfiguration
├── .gitignore              # Git-Ignore-Regeln
├── compose.yaml            # Docker Compose Definition
├── CONTRIBUTING.md         # Beiträge-Richtlinien
├── Dockerfile              # Container-Image-Build
├── LICENSE                 # MIT Lizenz
├── README.md               # Hauptdokumentation
├── QUICKSTART.md           # Schnellstart-Anleitung
├── requirements.txt        # Python-Abhängigkeiten
├── requirements-test.txt   # Test-Abhängigkeiten
└── alarm-mail.service      # Systemd-Service-Datei
```

### Lokale Entwicklung

**Service im Debug-Modus starten:**
```bash
# Flask Development Server
export FLASK_ENV=development
flask --app alarm_mail.app run --host 0.0.0.0 --port 8000 --reload

# Oder mit Python direkt
python -m alarm_mail.app
```

**Mit Test-E-Mail-Server:**

Für Tests ohne echten IMAP-Server:
```bash
# MailHog starten (Test-IMAP-Server)
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog

# In .env konfigurieren
ALARM_MAIL_IMAP_HOST=localhost
ALARM_MAIL_IMAP_PORT=1025
ALARM_MAIL_IMAP_USE_SSL=false
```

### Code-Qualität

**Linting mit flake8:**
```bash
flake8 alarm_mail/
```

**Formatting mit black:**
```bash
black alarm_mail/
```

**Type Checking mit mypy:**
```bash
mypy alarm_mail/
```

### Testing

**Unit Tests (falls vorhanden):**
```bash
# Alle Tests ausführen
pytest

# Mit Coverage
pytest --cov=alarm_mail --cov-report=html

# Spezifische Tests
pytest tests/test_parser.py -v
```

### Beitragen

Beiträge sind willkommen! Bitte beachten Sie:

1. **Fork** des Repositories erstellen
2. **Feature-Branch** erstellen (`git checkout -b feature/amazing-feature`)
3. **Code-Stil** einhalten (black, flake8)
4. **Commits** mit aussagekräftigen Nachrichten
5. **Tests** hinzufügen für neue Features
6. **Pull Request** erstellen

**Commit-Message-Format:**
```
feat: Add support for new XML field
fix: Correct timestamp parsing for edge case
docs: Update installation instructions
refactor: Simplify parser logic
test: Add tests for push service
```

---

## 🔒 Sicherheit

### Implementierte Sicherheitsmaßnahmen

✅ **Verschlüsselte Kommunikation**
- IMAP-Verbindung über SSL/TLS (Port 993)
- Unterstützung für TLS-verschlüsselte SMTP-Server
- Sichere XML-Verarbeitung mit defusedxml (verhindert XXE-Angriffe)

✅ **Authentifizierung & Autorisierung**
- API-Key-basierte Authentifizierung für alle Zielsysteme
- HTTP-Header: `X-API-Key`
- Keine Authentifizierung für Health-Checks erforderlich

✅ **Datensicherheit**
- **Keine Speicherung** von E-Mail-Inhalten
- E-Mails werden nur im Speicher verarbeitet
- Geparste Daten werden direkt weitergeleitet
- Keine Persistierung sensibler Informationen

✅ **Container-Sicherheit**
- Container läuft als **non-root User** (`appuser`)
- Minimales Python-Base-Image (`python:3.11-slim`)
- Nur notwendige Abhängigkeiten installiert
- Multi-Stage-Build für kleinere Images (optional erweiterbar)

✅ **Konfigurationssicherheit**
- Secrets nur über Umgebungsvariablen
- Keine Hard-coded Credentials im Code
- `.env` in `.gitignore`
- Health-Check enthält keine sensitiven Daten

### Sicherheits-Best Practices

#### 1. Starke API-Keys verwenden

```bash
# Generieren Sie sichere, zufällige API-Keys (mindestens 32 Zeichen)
openssl rand -hex 32

# Oder mit Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Anforderungen:**
- Mindestens 32 Zeichen
- Zufällig generiert
- Eindeutig für jeden Service

#### 2. Secrets-Management

**Entwicklung:**
```bash
# .env Datei verwenden (nicht in Git!)
cp .env.example .env
nano .env
```

**Produktion mit Docker Secrets:**
```yaml
services:
  alarm-mail:
    image: alarm-mail:latest
    secrets:
      - imap_password
      - api_key_monitor
      - api_key_messenger
    environment:
      - ALARM_MAIL_IMAP_PASSWORD_FILE=/run/secrets/imap_password
      - ALARM_MAIL_ALARM_MONITOR_API_KEY_FILE=/run/secrets/api_key_monitor

secrets:
  imap_password:
    external: true
  api_key_monitor:
    external: true
  api_key_messenger:
    external: true
```

**Produktion mit Vault:**
```bash
# Secrets aus HashiCorp Vault laden
vault kv get -field=imap_password secret/alarm-mail
```

#### 3. Netzwerk-Sicherheit

**Firewall-Regeln (iptables-Beispiel):**
```bash
# Nur IMAP-Server erlauben
iptables -A OUTPUT -p tcp --dport 993 -d imap.mailserver.de -j ACCEPT

# Nur Target-Services erlauben
iptables -A OUTPUT -p tcp --dport 8000 -d alarm-monitor -j ACCEPT
iptables -A OUTPUT -p tcp --dport 3000 -d alarm-messenger -j ACCEPT

# Alles andere blockieren
iptables -A OUTPUT -j DROP
```

**Docker-Netzwerk isolieren:**
```yaml
networks:
  alarm-network:
    driver: bridge
    internal: true  # Kein Internet-Zugang
```

#### 4. TLS/HTTPS für externe Kommunikation

Verwenden Sie für externe Zielsysteme immer HTTPS:

```bash
# ❌ NICHT für öffentliche Netze
ALARM_MAIL_ALARM_MONITOR_URL=http://monitor.example.com

# ✅ HTTPS verwenden
ALARM_MAIL_ALARM_MONITOR_URL=https://monitor.example.com
```

#### 5. Logging-Sicherheit

Sensible Daten werden nicht geloggt:
- ✅ Einsatznummern werden geloggt
- ✅ Stichwörter werden geloggt
- ❌ IMAP-Passwörter werden NICHT geloggt
- ❌ API-Keys werden NICHT geloggt
- ❌ E-Mail-Inhalte werden NICHT geloggt

#### 6. Regelmäßige Updates

```bash
# Dependencies aktualisieren
pip install --upgrade -r requirements.txt

# Docker-Image neu bauen
docker compose build --no-cache

# Security-Patches für Base-Image
docker pull python:3.11-slim
docker compose up -d --build
```

#### 7. Minimale Berechtigungen

**Systemd-Service mit eingeschränkten Rechten:**
```ini
[Service]
# Keine Root-Rechte
User=alarm
Group=alarm

# Sicherheitsoptionen
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/alarm-mail
```

### Sicherheits-Checkliste

Vor dem Produktiv-Einsatz:

- [ ] Starke, zufällige API-Keys generiert (mind. 32 Zeichen)
- [ ] SSL/TLS für IMAP-Verbindung aktiviert (`IMAP_USE_SSL=true`)
- [ ] HTTPS für externe API-Kommunikation
- [ ] Firewall-Regeln konfiguriert
- [ ] Secrets nicht in Git eingecheckt
- [ ] Container läuft als non-root User
- [ ] Regelmäßige Update-Strategie definiert
- [ ] Monitoring und Alerting eingerichtet
- [ ] Backup-Strategie für Konfiguration
- [ ] Logging auf sensible Daten überprüft

### Schwachstellen melden

Wenn Sie eine Sicherheitslücke entdecken:

1. **NICHT** als öffentliches Issue melden
2. Nutzen Sie [GitHub Security Advisories](https://github.com/TimUx/alarm-mail/security/advisories/new) für vertrauliche Meldungen
3. Oder erstellen Sie ein privates Security Issue auf GitHub
4. Fügen Sie hinzu:
   - Detaillierte Beschreibung der Schwachstelle
   - Proof-of-Concept (falls möglich)
   - Betroffene Versionen
   - Vorgeschlagene Fixes (optional)
5. Verantwortungsvolle Offenlegung (Responsible Disclosure)

Wir werden uns bemühen, innerhalb von 48 Stunden zu antworten und zeitnah einen Fix bereitzustellen.

---

## 🔧 Fehlerbehebung

### Häufige Probleme und Lösungen

#### Problem: Service startet nicht

**Symptome:**
- Container startet und stoppt sofort
- `docker compose up` zeigt Fehler

**Lösung:**
```bash
# Logs prüfen
docker compose logs alarm-mail

# Häufige Ursachen:
# 1. Fehlende Pflicht-Konfiguration
# Prüfen: IMAP_HOST, IMAP_USERNAME, IMAP_PASSWORD gesetzt?

# 2. Syntax-Fehler in .env
# Prüfen: Keine Leerzeichen um "=" , Werte in Anführungszeichen bei Sonderzeichen

# 3. Port bereits belegt
docker compose ps
netstat -tulpn | grep 8000
```

#### Problem: E-Mails werden nicht abgerufen

**Symptome:**
- Service läuft, aber keine Alarme werden verarbeitet
- Logs zeigen keine neuen Nachrichten

**Diagnose:**
```bash
# 1. IMAP-Verbindung testen
telnet imap.mailserver.de 993

# 2. Zugangsdaten überprüfen
docker compose exec alarm-mail env | grep IMAP

# 3. Mailbox-Namen prüfen (Case-sensitive!)
# INBOX vs Inbox vs inbox

# 4. Suchkriterien anpassen
# Vielleicht sind alle E-Mails bereits gelesen?
ALARM_MAIL_IMAP_SEARCH=ALL  # Temporär zum Testen
```

**Häufige Ursachen:**
- ❌ Falsche IMAP-Zugangsdaten
- ❌ Firewall blockiert Port 993
- ❌ SSL-Zertifikat-Problem
- ❌ 2FA ohne App-Passwort
- ❌ Mailbox-Name inkorrekt

**Lösungen:**
```bash
# SSL-Verbindung deaktivieren (nur für Debugging!)
ALARM_MAIL_IMAP_USE_SSL=false
ALARM_MAIL_IMAP_PORT=143

# Alternativen Mailbox-Namen versuchen
ALARM_MAIL_IMAP_MAILBOX=INBOX
# oder
ALARM_MAIL_IMAP_MAILBOX=Inbox

# Für Gmail: App-Passwort verwenden
# https://myaccount.google.com/apppasswords
```

#### Problem: Push zu Targets fehlschlägt

**Symptome:**
- E-Mails werden geparst
- Logs zeigen Fehler beim Push

**Diagnose:**
```bash
# 1. Target-Erreichbarkeit prüfen
curl http://alarm-monitor:8000/health
curl http://alarm-messenger:3000/api/health

# 2. API-Keys vergleichen
# alarm-mail .env:
grep ALARM_MONITOR_API_KEY .env
# alarm-monitor .env:
grep ALARM_DASHBOARD_API_KEY ../alarm-monitor/.env

# 3. Netzwerk-Verbindung prüfen
docker compose exec alarm-mail ping alarm-monitor
```

**Häufige Ursachen:**
- ❌ API-Keys stimmen nicht überein
- ❌ Target-Service läuft nicht
- ❌ Netzwerk-Konfiguration falsch
- ❌ Endpoint-URL falsch

**Lösungen:**
```bash
# API-Keys synchronisieren
# Beide Services müssen denselben Key verwenden!

# Service-Namen in Docker-Netzwerk verwenden
ALARM_MAIL_ALARM_MONITOR_URL=http://alarm-monitor:8000
# NICHT: http://localhost:8000

# Target-Service neu starten
docker compose restart alarm-monitor
```

#### Problem: Parsing fehlschlägt

**Symptome:**
- E-Mail wird abgerufen
- Log: "Received email without valid INCIDENT XML"

**Diagnose:**
```bash
# 1. E-Mail-Format prüfen
# Enthält die E-Mail wirklich <INCIDENT> XML?

# 2. Logs im Detail anschauen
docker compose logs alarm-mail | grep -A 10 "without valid"

# 3. Encoding-Probleme?
# XML muss UTF-8 oder ISO-8859-1 sein
```

**Lösungen:**
- XML-Format der Leitstelle überprüfen
- Beispiel-E-Mail zur Analyse bereitstellen
- Parser erweitern für alternative Formate

#### Problem: Health-Check schlägt fehl

**Symptome:**
- Container wird als "unhealthy" markiert
- Restart-Loop

**Diagnose:**
```bash
# Health-Check manuell ausführen
docker compose exec alarm-mail curl http://localhost:8000/health

# Oder von außen
curl http://localhost:8000/health
```

**Lösung:**
```bash
# Service-Port überprüfen
docker compose ps

# Firewall-Regeln prüfen
iptables -L -n

# Health-Check-Intervall anpassen
# In Dockerfile oder compose.yaml
```

### Debug-Modus aktivieren

Für erweiterte Fehlersuche:

```bash
# Python-Logging-Level auf DEBUG setzen
# In app.py temporär ändern:
# logging.basicConfig(level=logging.DEBUG, ...)

# Oder via Umgebungsvariable:
export ALARM_MAIL_LOG_LEVEL=DEBUG
```

### Support erhalten

Bei weiterhin bestehenden Problemen:

1. **Logs sammeln:**
   ```bash
   docker compose logs --tail=100 alarm-mail > logs.txt
   ```

2. **Konfiguration anonymisieren:**
   ```bash
   # Passwörter und Keys entfernen!
   cat .env | sed 's/PASSWORD=.*/PASSWORD=***/' > config-anonymized.txt
   ```

3. **Issue auf GitHub öffnen:**
   - https://github.com/TimUx/alarm-mail/issues
   - Logs anhängen
   - Anonymisierte Konfiguration
   - Beschreibung des Problems
   - Erwartetes vs. tatsächliches Verhalten

---

## 💬 Support & Beiträge

### Community & Kontakt

- **GitHub Issues:** [TimUx/alarm-mail/issues](https://github.com/TimUx/alarm-mail/issues)
- **Diskussionen:** [GitHub Discussions](https://github.com/TimUx/alarm-mail/discussions)
- **Verwandte Projekte:**
  - [alarm-monitor](https://github.com/TimUx/alarm-monitor) - Web-Dashboard
  - [alarm-messenger](https://github.com/TimUx/alarm-messenger) - Mobile Alarmierung

### Beiträge sind willkommen!

Wir freuen uns über jede Form von Beitrag:

- 🐛 Bug-Reports und Feature-Requests
- 📖 Verbesserungen der Dokumentation
- 💻 Code-Beiträge (Pull Requests)
- 🌐 Übersetzungen
- ⭐ Sterne auf GitHub

**Contribution Workflow:**
1. Fork erstellen
2. Feature-Branch erstellen (`feature/amazing-feature`)
3. Änderungen committen
4. Pull Request öffnen

Siehe auch: [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 Lizenz

Dieses Projekt ist lizenziert unter der **MIT License**.

```
MIT License

Copyright (c) 2024 TimUx

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Siehe [LICENSE](LICENSE) für den vollständigen Lizenztext.

---

## 🙏 Danksagungen

- Alle Beiträge zur Entwicklung
- Die Open-Source-Community
- Feuerwehren, die das System testen und Feedback geben

---

<div align="center">

**Entwickelt mit ❤️ für Feuerwehren**

[⬆️ Nach oben](#-alarm-mail)

</div>
