# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Hinzugefügt
- Umfassende Überarbeitung der Dokumentation
- CONTRIBUTING.md für Entwickler-Richtlinien
- CHANGELOG.md für Versionshistorie
- Erweiterte README.md mit detaillierten Abschnitten:
  - Architektur-Diagramm
  - API-Dokumentation
  - E-Mail-Format-Spezifikation
  - Deployment-Szenarien
  - Sicherheits-Best-Practices
  - Umfassende Fehlerbehebungs-Sektion
- Überarbeitete QUICKSTART.md mit Schritt-für-Schritt-Anleitungen
- docs/ Verzeichnis für erweiterte Dokumentation
- docs/images/ für zukünftige Screenshots
- Prometheus-kompatibler `/metrics`-Endpunkt (`alarm_mail_messages_processed_total`, `alarm_mail_push_success_total`, `alarm_mail_push_failure_total`, `alarm_mail_last_poll_timestamp_seconds`)
- Retry-Mechanismus für fehlgeschlagene Pushes (exponentielles Backoff, 3 Versuche)
- Konfigurierbare Timeout-Werte (`ALARM_MAIL_HTTP_TIMEOUT`)
- Deduplizierung von Alarmen anhand der Einsatznummer (`ALARM_MAIL_DEDUP_TTL`, `ALARM_MAIL_DEDUP_DB` für SQLite-Persistenz)
- MIME-Attachments und XML in multipart-E-Mails werden erkannt und verarbeitet
- Exponentieller IMAP-Backoff bei Verbindungsfehlern
- SSL-Verifikation für Targets konfigurierbar (`ALARM_MONITOR_VERIFY_SSL`, `ALARM_MESSENGER_VERIFY_SSL`)
- Health-Check-Endpunkt zeigt jetzt detaillierten Polling-Status (`polling: running/stopped`)

### Geändert
- Dokumentationsstruktur komplett überarbeitet
- README.md folgt jetzt einem logischen roten Faden
- Konsistente Formatierung und Emoji-Verwendung
- Verbesserte Beispiele und Code-Snippets

## [1.0.0] - 2024-12-08

### Hinzugefügt
- Initiales Release des alarm-mail Service
- IMAP-Polling für automatisches Abrufen von E-Mails
- XML-Parser für INCIDENT-Format
- Extraktion aller relevanten Einsatzinformationen:
  - Einsatznummer und Zeitstempel
  - Stichwörter (Haupt- und Unterstichwort)
  - Diagnose und Bemerkungen
  - Einsatzort mit Koordinaten
  - Alarmierte Einheiten (AAO)
  - Einsatzmaßnahmen (TME-Codes)
- API-Integration mit alarm-monitor
- API-Integration mit alarm-messenger
- Format-Konvertierung für verschiedene Zielsysteme
- Docker und Docker Compose Support
- Systemd-Service-Integration
- Health-Check-Endpunkt
- Strukturiertes Logging
- Konfiguration über Umgebungsvariablen
- SSL/TLS-Unterstützung für IMAP
- API-Key-Authentifizierung
- Non-root Container-Betrieb
- Robuste Fehlerbehandlung
- Automatische Reconnect-Logik für IMAP

### Sicherheit
- Sichere XML-Verarbeitung mit defusedxml
- Keine Speicherung von E-Mail-Inhalten
- API-Key-basierte Authentifizierung
- Container läuft als non-root User

---

## Versionshistorie

### Version Format

Das Projekt verwendet [Semantic Versioning](https://semver.org/lang/de/):

```
MAJOR.MINOR.PATCH

- MAJOR: Inkompatible API-Änderungen
- MINOR: Neue Features (abwärtskompatibel)
- PATCH: Bugfixes (abwärtskompatibel)
```

### Kategorien

Änderungen werden in folgende Kategorien eingeteilt:

- **Hinzugefügt** - Neue Features
- **Geändert** - Änderungen an bestehenden Features
- **Veraltet** - Features die bald entfernt werden
- **Entfernt** - Entfernte Features
- **Behoben** - Bugfixes
- **Sicherheit** - Sicherheitsupdates

---

## Geplante Features

Mögliche zukünftige Erweiterungen (keine Garantie):

### v1.1.0 (geplant)
- [ ] Prometheus-Metriken-Export
- [ ] Erweiterte Logging-Optionen
- [ ] Retry-Mechanismus für fehlgeschlagene Pushes
- [ ] Webhook-Support als zusätzliches Target
- [ ] Health-Check mit detailliertem Status
- [ ] Konfiguration von Timeout-Werten
- [ ] Support für mehrere IMAP-Postfächer

### v1.2.0 (geplant)
- [ ] Web-UI für Konfiguration und Monitoring
- [ ] Test-E-Mail-Generator
- [ ] Alarm-Historie (optional)
- [ ] E-Mail-Archivierung (optional)
- [ ] Erweiterte Filter-Möglichkeiten
- [ ] Template-System für verschiedene XML-Formate

### v2.0.0 (geplant)
- [ ] Plugin-System für Custom-Parser
- [ ] Graphische Konfiguration
- [ ] Multi-Tenancy-Support
- [ ] Advanced Monitoring Dashboard
- [ ] REST-API für externe Steuerung

---

## Beitragen

Änderungen am Projekt sollten in diesem Changelog dokumentiert werden.

Beim Erstellen eines Pull Requests:

1. Fügen Sie Ihre Änderungen unter `[Unreleased]` hinzu
2. Ordnen Sie sie der richtigen Kategorie zu
3. Verwenden Sie das folgende Format:
   ```
   - Kurze Beschreibung der Änderung (#PR-Nummer)
   ```

Beispiel:
```markdown
### Hinzugefügt
- Support für alternatives XML-Format (#42)
- Health-Check zeigt jetzt IMAP-Status (#45)

### Behoben
- Zeitstempel-Parsing für Format ohne Sekunden (#43)
- IMAP-Reconnect bei Timeout (#44)
```

---

## Links

- [Repository](https://github.com/TimUx/alarm-mail)
- [Issues](https://github.com/TimUx/alarm-mail/issues)
- [Pull Requests](https://github.com/TimUx/alarm-mail/pulls)
- [Releases](https://github.com/TimUx/alarm-mail/releases)

---

[Unreleased]: https://github.com/TimUx/alarm-mail/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/TimUx/alarm-mail/releases/tag/v1.0.0
