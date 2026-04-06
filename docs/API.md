# API-Dokumentation

Diese Dokumentation beschreibt die REST-API-Endpunkte des alarm-mail Service sowie die API-Integration mit den Zielsystemen.

## Inhaltsverzeichnis

- [alarm-mail Service API](#alarm-mail-service-api)
- [Integration mit alarm-monitor](#integration-mit-alarm-monitor)
- [Integration mit alarm-messenger](#integration-mit-alarm-messenger)

---

## alarm-mail Service API

Der alarm-mail Service stellt zwei öffentliche HTTP-Endpunkte bereit.

### Basis-URL

```
http://localhost:8000
```

oder im Docker-Netzwerk:
```
http://alarm-mail:8000
```

---

### GET /health

**Health-Check-Endpunkt** für Monitoring-Systeme.

#### Request

```http
GET /health HTTP/1.1
Host: localhost:8000
```

```bash
curl http://localhost:8000/health
```

#### Response

**Status:** `200 OK`

```json
{
  "status": "ok",
  "polling": "running",
  "service": "alarm-mail"
}
```

**Status:** `503 Service Unavailable` (when polling thread is not running)

```json
{
  "status": "degraded",
  "polling": "stopped",
  "service": "alarm-mail"
}
```

#### Response Fields

| Feld | Typ | Wert | Beschreibung |
|------|-----|------|--------------|
| `status` | String | `"ok"` / `"degraded"` | Gesundheitsstatus |
| `polling` | String | `"running"` / `"stopped"` | Status des IMAP-Polling-Threads |
| `service` | String | `"alarm-mail"` | Name des Service |

#### Verwendung

**Docker Health-Check:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
  CMD curl --fail http://localhost:8000/health || exit 1
```

**Kubernetes Probe:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 30
```

**Monitoring-Script:**
```bash
#!/bin/bash
if curl -sf http://localhost:8000/health > /dev/null; then
  echo "OK - alarm-mail is healthy"
  exit 0
else
  echo "CRITICAL - alarm-mail health check failed"
  exit 2
fi
```

---

### GET /

**Service-Status-Endpunkt** mit erweiterten Informationen.

#### Request

```http
GET / HTTP/1.1
Host: localhost:8000
```

```bash
curl http://localhost:8000/
```

#### Response

**Status:** `200 OK`

```json
{
  "service": "alarm-mail",
  "status": "running",
  "targets": ["alarm-monitor", "alarm-messenger"],
  "poll_interval": 60
}
```

#### Response Fields

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `service` | String | Name des Service (immer "alarm-mail") |
| `status` | String | Aktueller Status (immer "running") |
| `targets` | Array<String> | Liste der konfigurierten Zielsysteme |
| `poll_interval` | Integer | Konfiguriertes IMAP-Polling-Intervall in Sekunden |

#### Beispiele

**Nur alarm-monitor konfiguriert:**
```json
{
  "service": "alarm-mail",
  "status": "running",
  "targets": ["alarm-monitor"],
  "poll_interval": 60
}
```

**Keine Targets konfiguriert:**
```json
{
  "service": "alarm-mail",
  "status": "running",
  "targets": [],
  "poll_interval": 60
}
```

**Beide Targets konfiguriert:**
```json
{
  "service": "alarm-mail",
  "status": "running",
  "targets": ["alarm-monitor", "alarm-messenger"],
  "poll_interval": 30
}
```

---

## Integration mit alarm-monitor

Der alarm-mail Service sendet geparste Alarmdaten an den alarm-monitor.

### Endpoint

```
POST /api/alarm
```

### Request

#### Headers

```http
Content-Type: application/json
X-API-Key: <API_KEY>
```

Der `X-API-Key` Header muss den konfigurierten API-Key enthalten.

#### Body

Vollständiges Alarm-Daten-Objekt:

```json
{
  "incident_number": "2024-001",
  "timestamp": "2024-12-08T14:30:00",
  "timestamp_display": "08.12.2024 14:30:00",
  "keyword": "F3Y – Brand in Wohngebäude",
  "keyword_primary": "F3Y",
  "keyword_secondary": "Personen in Gefahr",
  "diagnosis": "Brand in Wohngebäude",
  "remark": "Starke Rauchentwicklung im 2. OG",
  "location": "Hauptstraße 123, Nordviertel, Musterstadt",
  "location_details": {
    "street": "Hauptstraße 123",
    "village": "Nordviertel",
    "town": "Musterstadt",
    "object": "Mehrfamilienhaus",
    "additional": "Hintereingang"
  },
  "latitude": 51.2345,
  "longitude": 9.8765,
  "groups": [
    "LF Musterstadt 1",
    "DLK Musterstadt",
    "Musterstadt Nord 1 (TME MUS11)",
    "Musterstadt Innenstadt (TME MUS05)"
  ],
  "aao_groups": [
    "LF Musterstadt 1",
    "DLK Musterstadt"
  ],
  "dispatch_groups": [
    "Musterstadt Nord 1 (TME MUS11)",
    "Musterstadt Innenstadt (TME MUS05)"
  ],
  "dispatch_group_codes": [
    "MUS11",
    "MUS05"
  ],
  "subject": "Einsatzalarmierung - F3Y"
}
```

#### Field Descriptions

| Feld | Typ | Optional | Beschreibung |
|------|-----|----------|--------------|
| `incident_number` | String | Nein | Einsatznummer der Leitstelle |
| `timestamp` | String | Nein | ISO 8601 Zeitstempel |
| `timestamp_display` | String | Ja | Formatierter Zeitstempel für Anzeige |
| `keyword` | String | Nein | Kombiniertes Stichwort für Anzeige |
| `keyword_primary` | String | Ja | Hauptstichwort (z.B. "F3Y") |
| `keyword_secondary` | String | Ja | Unterstichwort |
| `diagnosis` | String | Ja | Einsatzdiagnose |
| `remark` | String | Ja | Bemerkungen |
| `location` | String | Ja | Vollständige Ortsangabe |
| `location_details` | Object | Ja | Strukturierte Ortsinformationen |
| `latitude` | Float | Ja | Breitengrad (WGS84) |
| `longitude` | Float | Ja | Längengrad (WGS84) |
| `groups` | Array | Ja | Alle Einheiten (AAO + TME) |
| `aao_groups` | Array | Ja | AAO-Einheiten |
| `dispatch_groups` | Array | Ja | TME-Einheiten |
| `dispatch_group_codes` | Array | Ja | Extrahierte TME-Codes |
| `subject` | String | Ja | E-Mail-Betreff |

### Response

**Success:** `200 OK`
```json
{
  "status": "ok",
  "message": "Alarm received"
}
```

**Error:** `401 Unauthorized`
```json
{
  "error": "Unauthorized"
}
```

### Implementation (alarm-monitor)

Beispiel-Implementation für alarm-monitor:

```python
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route("/api/alarm", methods=["POST"])
def api_alarm():
    """Receive alarm data from alarm-mail service."""
    
    # Authentifizierung
    api_key = request.headers.get("X-API-Key")
    expected_key = os.environ.get("ALARM_DASHBOARD_API_KEY")
    
    if not api_key or api_key != expected_key:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Alarm-Daten empfangen
    alarm_data = request.get_json()
    
    if not alarm_data:
        return jsonify({"error": "No data provided"}), 400
    
    # Validierung
    required_fields = ["incident_number", "timestamp", "keyword"]
    for field in required_fields:
        if field not in alarm_data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Verarbeitung (Speichern, Anzeigen, etc.)
    # ... Ihre Logik hier ...
    
    return jsonify({"status": "ok", "message": "Alarm received"}), 200
```

---

## Integration mit alarm-messenger

Der alarm-mail Service sendet Alarmdaten im Emergency-Format an alarm-messenger.

### Endpoint

```
POST /api/emergencies
```

### Request

#### Headers

```http
Content-Type: application/json
X-API-Key: <API_KEY>
```

Der `X-API-Key` Header muss den konfigurierten API-Key enthalten.

#### Body

Emergency-Objekt im alarm-messenger Format:

```json
{
  "emergencyNumber": "2024-001",
  "emergencyDate": "2024-12-08T14:30:00",
  "emergencyKeyword": "F3Y",
  "emergencyDescription": "Brand in Wohngebäude",
  "emergencyLocation": "Hauptstraße 123, Nordviertel, Musterstadt",
  "groups": "MUS11,MUS05"
}
```

#### Field Descriptions

| Feld | Typ | Optional | Beschreibung |
|------|-----|----------|--------------|
| `emergencyNumber` | String | Nein | Einsatznummer |
| `emergencyDate` | String | Nein | ISO 8601 Zeitstempel |
| `emergencyKeyword` | String | Nein | Hauptstichwort |
| `emergencyDescription` | String | Ja | Einsatzbeschreibung |
| `emergencyLocation` | String | Ja | Einsatzort |
| `groups` | String | Ja | Kommaseparierte TME-Codes für Gruppenalarmierung |

### Format-Konvertierung

alarm-mail konvertiert automatisch:

| Intern (alarm-mail) | API (alarm-messenger) |
|---------------------|----------------------|
| `incident_number` | `emergencyNumber` |
| `timestamp` | `emergencyDate` |
| `keyword_primary` | `emergencyKeyword` |
| `diagnosis` | `emergencyDescription` |
| `location` | `emergencyLocation` |
| `dispatch_group_codes` (Array) | `groups` (String, kommasepariert) |

### Response

**Success:** `200 OK` oder `201 Created`
```json
{
  "status": "ok",
  "emergencyId": "uuid-here"
}
```

**Error:** `401 Unauthorized`
```json
{
  "error": "Unauthorized"
}
```

### Gruppenalarmierung

Wenn TME-Codes im XML vorhanden sind:

**XML:**
```xml
<EINSATZMASSNAHMEN>
  <TME>
    <BEZEICHNUNG>Wilersdorf 1 (TME WIL26)</BEZEICHNUNG>
    <BEZEICHNUNG>Wilersdorf 2 (TME WIL41)</BEZEICHNUNG>
  </TME>
</EINSATZMASSNAHMEN>
```

**Resultat im Request:**
```json
{
  "groups": "WIL26,WIL41"
}
```

Der alarm-messenger verwendet diese Codes zur selektiven Alarmierung.

---

## Fehlerbehandlung

### Fehler in alarm-mail

Bei Fehlern beim Push zu Targets:

- Fehler werden geloggt
- Service läuft weiter
- Nächster Alarm wird normal verarbeitet
- Fehlerhafte Pushes blockieren nicht andere Targets

**Log-Beispiel:**
```
2024-12-08 14:30:02 - alarm_mail.push_service - ERROR - Failed to push alarm to alarm-monitor: Connection refused
2024-12-08 14:30:03 - alarm_mail.push_service - INFO - Successfully pushed alarm to alarm-messenger
```

### Timeout-Konfiguration

Standard-Timeout: **10 Sekunden**

Kann im Code angepasst werden (`push_service.py`):

```python
response = requests.post(
    url,
    json=data,
    headers=headers,
    timeout=10,  # Sekunden
)
```

---

## Authentifizierung

### API-Key-Format

- Wird als HTTP-Header gesendet: `X-API-Key`
- Empfehlung: Mindestens 32 Zeichen
- Zufällig generiert

**API-Key generieren:**
```bash
# Linux/macOS
openssl rand -hex 32

# Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### API-Key-Konfiguration

**alarm-mail:**
```bash
ALARM_MAIL_ALARM_MONITOR_API_KEY=ihr-geheimer-key
ALARM_MAIL_ALARM_MESSENGER_API_KEY=ihr-anderer-key
```

**alarm-monitor:**
```bash
ALARM_DASHBOARD_API_KEY=ihr-geheimer-key
```

**alarm-messenger:**
```bash
API_SECRET_KEY=ihr-anderer-key
```

**Wichtig:** Die Keys müssen übereinstimmen!

---

## Rate Limiting

Aktuell kein Rate Limiting implementiert.

Bei Bedarf in den Zielsystemen implementieren:

```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@app.route("/api/alarm", methods=["POST"])
@limiter.limit("10 per minute")
def api_alarm():
    ...
```

---

## Beispiel-Requests

### cURL

**Health-Check:**
```bash
curl http://localhost:8000/health
```

**Service-Info:**
```bash
curl http://localhost:8000/
```

**Test-Push zu alarm-monitor:**
```bash
curl -X POST http://localhost:8000/api/alarm \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "incident_number": "TEST-001",
    "timestamp": "2024-12-08T14:30:00",
    "keyword": "TEST",
    "location": "Teststraße 1, Teststadt"
  }'
```

### Python

```python
import requests

# Health-Check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Push zu alarm-monitor simulieren
alarm_data = {
    "incident_number": "TEST-001",
    "timestamp": "2024-12-08T14:30:00",
    "keyword": "TEST",
    "location": "Teststraße 1, Teststadt"
}

response = requests.post(
    "http://alarm-monitor:8000/api/alarm",
    json=alarm_data,
    headers={"X-API-Key": "your-api-key"}
)
print(response.json())
```

---

## Weiterführende Links

- [README.md](../README.md) - Hauptdokumentation
- [QUICKSTART.md](../QUICKSTART.md) - Schnellstart
- [alarm-monitor Repository](https://github.com/TimUx/alarm-monitor)
- [alarm-messenger Repository](https://github.com/TimUx/alarm-messenger)
