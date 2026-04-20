# B.I.E.R

B.I.E.R steht fuer Buero-Inventar- und Einkaufs-Register.

Eine moderne Warehouse- und Procurement-Webanwendung mit Flask, MongoDB und Docker.

## Hinweis Zum Branch

Dieser Branch ist eine KI-unterstuetzte Test-/Experimentier-Version und nicht die offizielle Bewertungs-/Produktionsquelle.

## Inhaltsverzeichnis

- [Warum B.I.E.R](#warum-bier)
- [Funktionsumfang](#funktionsumfang)
- [Architektur Kurzfassung](#architektur-kurzfassung)
- [Tech Stack](#tech-stack)
- [Projektstruktur](#projektstruktur)
- [Schnellstart Mit Docker](#schnellstart-mit-docker)
- [Lokale Entwicklung Ohne Docker](#lokale-entwicklung-ohne-docker)
- [Login Rollen Und Sicherheit](#login-rollen-und-sicherheit)
- [UI Settings Persistenz](#ui-settings-persistenz)
- [Reports Und Exporte](#reports-und-exporte)
- [Tests](#tests)
- [Dokumentation](#dokumentation)
- [Roadmap](#roadmap)
- [Lizenz](#lizenz)

## Warum B.I.E.R

B.I.E.R kombiniert Lagerverwaltung, Beschaffung und Nachvollziehbarkeit in einer Anwendung:

- zentrale Verwaltung von Produkten, Lagern und Bestaenden
- Beschaffungs- und Freigabeprozesse fuer Bestellungen
- Kommissionierung inkl. Druckansicht
- rollenbasierte Bedienung fuer Manager und Clerk
- nachvollziehbare Aenderungshistorie inkl. User-Admin-Audit-Events

## Funktionsumfang

### Lager Und Inventar

- Produkte erstellen, bearbeiten, verschieben und loeschen
- Multi-Lager-Bestaende pro Produkt
- Lagerverwaltung mit Kapazitaets-/Auslastungsanzeige
- Statistik-Dashboard mit Kennzahlen und Charts
- Historie aller relevanten Events

### Beschaffung Und Kommissionierung

- Lieferanten- und Abteilungsdaten
- Bestellvorschlaege und Bestell-Workflow
- Freigaben fuer manager-relevante Schritte
- Picklisten und Druckansicht fuer operative Prozesse

### Authentifizierung Und Userverwaltung

- Login/Logout mit Session-basiertem Auth-Flow
- Rollen: `manager`, `clerk`
- Manager-UI fuer Benutzerverwaltung:
  - Benutzer anlegen
  - Rolle aendern
  - aktiv/deaktiviert setzen
  - Passwort zuruecksetzen
- Sicherheitsregeln:
  - kein Self-Demotion auf `clerk`
  - keine Self-Deaktivierung
  - mindestens ein aktiver Manager bleibt erhalten

### Auditbarkeit

User-Admin-Aenderungen werden als Audit-Events gespeichert:

- `entity_type = user_admin`
- `action = create | update_role | update_status | reset_password`
- inkl. `performed_by`, Zeitstempel, Ziel-User und Aenderungsdetails

## Architektur Kurzfassung

Das Projekt folgt einer Ports-and-Adapters-Struktur (hexagonaler Ansatz):

1. Frontend (Flask + Jinja Templates)
2. Service-Layer (Businesslogik)
3. Contracts (abstrakte Ports)
4. DB-Adapter (MongoDB)

Mehr Details: [docs/architecture.md](docs/architecture.md)

## Tech Stack

- Python 3.10+
- Flask
- MongoDB
- Docker / Docker Compose
- pytest
- Bootstrap + Jinja Templates

## Projektstruktur

```text
src/
  bierapp/
    backend/        # Services und Domain-Logik
    contracts/      # Port-Interfaces
    db/             # MongoDB Adapter + Init/Seed
    frontend/flask/ # Flask-Routen + UI-Glue
    reports/        # CLI Reports
  resources/
    templates/      # Jinja-Templates (Page 1-9)
    pictures/
tests/
  unit/
  integration/
```

## Schnellstart Mit Docker

### Voraussetzungen

- Docker Desktop

### Start

```bash
docker compose up -d --build
```

### Erreichbare Services

- App: http://localhost:5000
- Mongo Express: http://localhost:8081

## Lokale Entwicklung Ohne Docker

### Voraussetzungen

- Python 3.10+

### Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

### Starten

```bash
python -m bierapp.frontend.flask.gui
```

## Login Rollen Und Sicherheit

Wenn `AUTH_REQUIRED=1` aktiv ist:

- Manager Default: `admin` / `admin`
- Clerk Default: `lager` / `lager`

Die Default-User werden bei Bedarf in MongoDB angelegt und koennen anschliessend in der User-Admin gepflegt werden.

Wichtige Umgebungsvariablen:

- `AUTH_REQUIRED` (Standard: `1`)
- `FLASK_SECRET`
- `MONGO_HOST`
- `MONGO_PORT`
- `MONGO_DB`
- `MONGO_USER`
- `MONGO_PASS`

## UI Settings Persistenz

Personalisierung ist DB-basiert:

- benutzerspezifische Profile in `user_settings`
- globale Rollenpolicy (Clerk Defaults/Locks) in `app_settings`
- Theme/Settings Import/Export als JSON
- Bootstrap-API fuer initiales Laden der Profile

## Reports Und Exporte

### CLI Reports

```bash
python -m bierapp.reports.statistics_report
python -m bierapp.reports.inventory_report
python -m bierapp.reports.inventory_report <lager_id>
```

Ausgabeordner:

- [src/bierapp/reports/output](src/bierapp/reports/output)

### UI Exporte

- Historie als TXT
- PDF Exporte fuer Inventar/Statistik/Historie

## Tests

Alle Tests:

```bash
.venv\Scripts\python -m pytest -q .
```

Stand: 104/104 Tests erfolgreich.

Gezielt ausfuehren:

```bash
pytest tests/unit/ -v
pytest tests/integration/ -v
```

Mehr Details: [docs/tests.md](docs/tests.md)

## Dokumentation

- [docs/architecture.md](docs/architecture.md)
- [docs/contracts.md](docs/contracts.md)
- [docs/style_guide.md](docs/style_guide.md)
- [docs/tests.md](docs/tests.md)

## Roadmap

- Audit-Log Filter (User, Aktion, Zeitraum)
- Optionale serverseitige Team-Profile fuer UI-Einstellungen
- Weitere Härtung von Security Policies und Monitoring

## Lizenz

MIT. Siehe [LICENSE](LICENSE).
