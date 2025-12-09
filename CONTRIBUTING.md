# 🤝 Contributing zu alarm-mail

Vielen Dank für Ihr Interesse, zu alarm-mail beizutragen! Jeder Beitrag, ob groß oder klein, ist willkommen und wird geschätzt.

## 📋 Inhaltsverzeichnis

- [Code of Conduct](#code-of-conduct)
- [Wie kann ich beitragen?](#wie-kann-ich-beitragen)
- [Entwicklungsumgebung einrichten](#entwicklungsumgebung-einrichten)
- [Pull Request Prozess](#pull-request-prozess)
- [Coding Standards](#coding-standards)
- [Commit-Nachrichten](#commit-nachrichten)
- [Testing](#testing)
- [Dokumentation](#dokumentation)

---

## Code of Conduct

Dieses Projekt folgt einem Code of Conduct. Durch die Teilnahme verpflichten Sie sich, diesen zu respektieren:

- **Respektvoll sein:** Behandeln Sie alle Teilnehmer mit Respekt
- **Konstruktiv sein:** Geben Sie konstruktives Feedback
- **Inklusiv sein:** Willkommen heißen von Beitragenden aller Hintergründe
- **Professionell bleiben:** Fokus auf technische Themen

---

## Wie kann ich beitragen?

### 🐛 Bugs melden

Wenn Sie einen Bug finden:

1. **Prüfen Sie** ob der Bug bereits gemeldet wurde ([Issues](https://github.com/TimUx/alarm-mail/issues))
2. **Erstellen Sie** ein neues Issue mit:
   - Klarer, beschreibender Titel
   - Detaillierte Beschreibung des Problems
   - Schritte zur Reproduktion
   - Erwartetes vs. tatsächliches Verhalten
   - Environment-Details (OS, Python-Version, Docker-Version)
   - Logs (Passwörter und API-Keys entfernen!)

**Bug-Report-Template:**
```markdown
## Bug-Beschreibung
[Kurze Beschreibung des Problems]

## Schritte zur Reproduktion
1. [Erster Schritt]
2. [Zweiter Schritt]
3. [...]

## Erwartetes Verhalten
[Was sollte passieren?]

## Tatsächliches Verhalten
[Was passiert stattdessen?]

## Environment
- OS: [z.B. Ubuntu 22.04]
- Python-Version: [z.B. 3.11.5]
- Docker-Version: [z.B. 24.0.6]
- alarm-mail Version: [z.B. v1.0.0]

## Logs
```
[Relevante Logs hier einfügen - Secrets entfernen!]
```
```

### 💡 Features vorschlagen

Feature-Requests sind willkommen!

1. **Prüfen Sie** ob das Feature bereits vorgeschlagen wurde
2. **Erstellen Sie** ein Issue mit:
   - Klarer Titel: "Feature: [Kurzbeschreibung]"
   - Detaillierte Beschreibung des Features
   - Use Case / Problem das gelöst wird
   - Vorgeschlagene Implementierung (optional)

### 📖 Dokumentation verbessern

Verbesserungen der Dokumentation sind sehr willkommen:

- Rechtschreibfehler korrigieren
- Fehlende Informationen ergänzen
- Beispiele hinzufügen
- Klarstellungen vornehmen
- Übersetzungen beitragen

### 💻 Code beitragen

Pull Requests für Bugfixes und Features sind willkommen!

---

## Entwicklungsumgebung einrichten

### Voraussetzungen

- Python 3.11 oder höher
- Git
- Docker (optional, für Tests)

### Setup

```bash
# Repository forken und klonen
git clone https://github.com/YOUR-USERNAME/alarm-mail.git
cd alarm-mail

# Virtual Environment erstellen
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Dependencies installieren
pip install -r requirements.txt

# Development Dependencies installieren
pip install pytest pytest-cov black flake8 mypy

# Konfiguration erstellen
cp .env.example .env
# .env mit Test-Zugangsdaten füllen
```

### Service lokal starten

```bash
# Development Server
flask --app alarm_mail.app run --host 0.0.0.0 --port 8000 --reload

# Oder mit Python direkt
python -m alarm_mail.app
```

---

## Pull Request Prozess

### 1. Branch erstellen

```bash
# Upstream Repository hinzufügen
git remote add upstream https://github.com/TimUx/alarm-mail.git

# Lokalen main aktualisieren
git checkout main
git pull upstream main

# Feature-Branch erstellen
git checkout -b feature/amazing-feature
# oder
git checkout -b fix/bug-description
```

**Branch-Naming-Konventionen:**
- `feature/` - Neue Features
- `fix/` - Bugfixes
- `docs/` - Dokumentations-Änderungen
- `refactor/` - Code-Refactoring
- `test/` - Test-Ergänzungen

### 2. Änderungen machen

```bash
# Code ändern
# ...

# Testen
pytest

# Code-Qualität prüfen
black alarm_mail/
flake8 alarm_mail/
mypy alarm_mail/

# Änderungen committen
git add .
git commit -m "feat: Add support for new XML field"
```

### 3. Push und Pull Request

```bash
# Branch pushen
git push origin feature/amazing-feature
```

Gehen Sie zu GitHub und erstellen Sie einen Pull Request mit:

- **Titel:** Klare, kurze Beschreibung
- **Beschreibung:**
  - Was wurde geändert?
  - Warum wurde es geändert?
  - Wie wurde es getestet?
  - Welche Issues werden geschlossen? (`Closes #123`)
- **Screenshots:** Wenn UI betroffen (falls zutreffend)

### 4. Review-Prozess

- Maintainer werden Ihren PR reviewen
- Möglicherweise werden Änderungen angefragt
- Nach Approval wird der PR gemerged
- Branch kann danach gelöscht werden

---

## Coding Standards

### Python Style Guide

Wir folgen [PEP 8](https://pep8.org/) mit einigen Anpassungen:

**Formatierung:**
- Verwenden Sie **black** für automatische Formatierung
- Zeilenlänge: 88 Zeichen (black default)
- 4 Spaces für Einrückung (keine Tabs)

```bash
# Alle Dateien formatieren
black alarm_mail/

# Einzelne Datei formatieren
black alarm_mail/parser.py
```

**Linting:**
- Verwenden Sie **flake8** für Linting
- Beheben Sie alle Warnungen

```bash
flake8 alarm_mail/
```

**Type Hints:**
- Verwenden Sie Type Hints für alle Funktionen
- Prüfen Sie mit **mypy**

```python
from typing import Dict, Any, Optional

def parse_alarm(raw_email: bytes) -> Optional[Dict[str, Any]]:
    """Parse alarm from raw email."""
    ...
```

### Code-Struktur

**Imports sortieren:**
```python
# Standard Library
import os
import sys
from typing import Dict

# Third-Party
import requests
from flask import Flask

# Local
from .config import AppConfig
from .parser import parse_alarm
```

**Docstrings:**
```python
def parse_timestamp(value: Optional[str]) -> Dict[str, Optional[str]]:
    """Parse timestamp string into ISO and display format.
    
    Args:
        value: Timestamp string in format "DD.MM.YYYY HH:MM:SS"
        
    Returns:
        Dictionary with 'timestamp' (ISO format) and 'timestamp_display'
        
    Examples:
        >>> parse_timestamp("08.12.2024 14:30:00")
        {'timestamp': '2024-12-08T14:30:00', 'timestamp_display': '08.12.2024 14:30:00'}
    """
    ...
```

### Logging

```python
import logging

LOGGER = logging.getLogger(__name__)

# Logging-Levels verwenden
LOGGER.debug("Detailed debug information")
LOGGER.info("Normal operational message")
LOGGER.warning("Warning message")
LOGGER.error("Error occurred: %s", error)
LOGGER.exception("Exception with traceback")
```

**Wichtig:** Niemals Secrets loggen (Passwörter, API-Keys)!

---

## Commit-Nachrichten

Wir verwenden [Conventional Commits](https://www.conventionalcommits.org/):

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - Neues Feature
- `fix` - Bugfix
- `docs` - Dokumentation
- `style` - Formatierung (keine Code-Änderung)
- `refactor` - Code-Refactoring
- `test` - Tests hinzufügen/ändern
- `chore` - Build-Prozess, Dependencies

**Beispiele:**

```bash
# Feature
git commit -m "feat(parser): Add support for ORTSZUSATZ field"

# Bugfix
git commit -m "fix(mail_checker): Handle connection timeout gracefully"

# Dokumentation
git commit -m "docs: Update installation instructions for Docker"

# Breaking Change
git commit -m "feat(api)!: Change alarm data format

BREAKING CHANGE: The alarm API now returns ISO 8601 timestamps instead of German format."
```

**Regeln:**
- Verwenden Sie Präsens ("Add feature" nicht "Added feature")
- Beginnen Sie mit Kleinbuchstaben
- Kein Punkt am Ende der ersten Zeile
- Body erklärt "was" und "warum" (nicht "wie")

---

## Testing

### Unit Tests

```bash
# Alle Tests ausführen
pytest

# Mit Coverage
pytest --cov=alarm_mail --cov-report=html

# Spezifischer Test
pytest tests/test_parser.py::test_parse_timestamp -v
```

### Test schreiben

```python
# tests/test_parser.py
import pytest
from alarm_mail.parser import parse_timestamp

def test_parse_timestamp_valid():
    """Test parsing of valid timestamp."""
    result = parse_timestamp("08.12.2024 14:30:00")
    assert result["timestamp"] == "2024-12-08T14:30:00"
    assert result["timestamp_display"] == "08.12.2024 14:30:00"

def test_parse_timestamp_none():
    """Test parsing of None timestamp."""
    result = parse_timestamp(None)
    assert result["timestamp"] is None
    assert result["timestamp_display"] is None
```

### Integration Tests

```bash
# Mit Docker Compose
docker compose -f docker-compose.test.yaml up --abort-on-container-exit
```

---

## Dokumentation

### README.md aktualisieren

Bei Änderungen an:
- Features
- Konfiguration
- API
- Installation

bitte auch die README.md aktualisieren.

### Code-Dokumentation

- Docstrings für alle öffentlichen Funktionen/Klassen
- Inline-Kommentare für komplexe Logik
- Type Hints für bessere IDE-Unterstützung

### Beispiele hinzufügen

Beispiele sind sehr hilfreich! Fügen Sie hinzu zu:
- `docs/examples/` - Beispiel-Konfigurationen
- Code-Docstrings - Verwendungsbeispiele
- README.md - Anwendungsfälle

---

## Fragen?

Bei Fragen:

- Öffnen Sie ein [Discussion](https://github.com/TimUx/alarm-mail/discussions)
- Kommentieren Sie in relevanten Issues
- Kontaktieren Sie die Maintainer

---

## Danke! 🙏

Vielen Dank für Ihren Beitrag zu alarm-mail! Ihre Zeit und Mühe werden sehr geschätzt.

**Happy Coding!** 🚀
