[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/Pc_A4vY0)
[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=22780739&assignment_repo_type=AssignmentRepo)
# Lagerverwaltungssystem - Projektvorlage

Vollständige Projektvorlage für ein professionelles Softwareentwicklungs- und Projektmanagement-Projekt. Dieses Projekt dient als Basis für die Entwicklung einer Lagerverwaltungs- oder Produktverwaltungssoftware mit professionellen Vorgaben.

## Projektüberblick

- **Projektdauer:** 8 Wochen
- **Unterricht:** 2 UE pro Woche
- **Gruppengröße:** 3er- und 4er-Gruppen (Standard: 4er)
- **Ziel:** Professionelle Softwareentwicklung und Projektmanagement

## Projektstruktur

```
B.I.E.R/
├── src/                              # Quellcode
│   ├── bierapp/                      # Haupt-Package der Anwendung
│   │   ├── __init__.py
│   │   ├── backend/                  # Backend-Logik
│   │   │   └── __init__.py
│   │   ├── db/                       # Datenbankanbindung (MongoDB)
│   │   │   └── __init__.py
│   │   └── frontend/                 # Frontend-Layer
│   │       ├── __init__.py
│   │       └── flask/                # Flask Web-UI
│   │           ├── __init__.py
│   │           └── gui.py            # Flask-Routen & GUI-Logik
│   ├── reports/                      # Report-Generierung
│   │   └── __init__.py
│   ├── resources/                    # Statische Ressourcen
│   │   └── pictures/                 # Bilder & Icons
│   │       ├── BIER_ICON_COMPRESSED.png
│   │       ├── BIER_LOGO_SCHWARZ_COMPRESSED.png
│   │       └── BIER_LOGO_WEISS_COMPRESSED.png
│   └── templates/                    # HTML-Templates (Jinja2)
│       └── index.html
├── tests/                            # Tests
│   ├── conftest.py                   # Pytest-Konfiguration
│   ├── integration/                  # Integrationstests
│   │   ├── test_flask.py             # Flask-Tests
│   │   ├── test_integration.py       # Allgemeine Integrationstests
│   │   └── test_mongodb.py           # MongoDB-Tests
│   └── unit/                         # Unit Tests
│       └── test_domain.py            # Tests für Domain-Modelle
├── docs/                             # Dokumentation
│   ├── architecture.md               # Architektur-Dokumentation
│   ├── changelog.md                  # Changelog
│   ├── contracts.md                  # Schnittstellen-Dokumentation
│   ├── known_issues.md               # Bekannte Probleme
│   ├── retrospective.md              # Retrospektive
│   ├── style_guide.md                # Code-Style-Vorgaben
│   └── tests.md                      # Test-Dokumentation
├── docker-compose.yml                # Docker Compose Konfiguration
├── Dockerfile                        # Docker Image Definition
├── pyproject.toml                    # Python-Projektdefinition & Dependencies
└── README.md                         # Projekt-Dokumentation
```

## Installation & Setup

### Voraussetzungen
- Python 3.10+
- pip oder Poetry

### Entwicklungsumgebung aufbauen

```bash
# 1. Repository klonen
git clone <repository-url>
cd projekt

# 2. Virtuelle Umgebung erstellen (optional, aber empfohlen)
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Dependencies installieren
pip install -e .
pip install -e ".[dev]"

# 4. Tests ausführen
pytest

# 5. GUI starten
python -m src.ui
```

## Architektur

Das Projekt folgt der **Port-Adapter-Architektur** (auch Hexagonal Architecture genannt):

- **Domain Layer:** Geschäftslogik und Entities (unabhängig von technischen Details)
- **Ports:** Schnittstellen für externe Abhängigkeiten (abstrakt)
- **Adapters:** Konkrete Implementierungen (z.B. In-Memory Repository, Dateisystem, Datenbank)
- **Services:** Geschäftsvorgänge und Use Cases
- **UI:** Benutzeroberfläche

Diese Architektur ermöglicht:
- **Testbarkeit:** Mock-Implementierungen können einfach bereitgestellt werden
- **Austauschbarkeit:** Adapters können leicht ausgetauscht werden
- **Wartbarkeit:** Klare Trennung der Concerns

## Rollenvergabe (4er-Gruppe)

### Rolle 1: Projektverantwortung & Schnittstellen (Contract Owner)
- Projektkoordination & Kommunikation
- Zentrale Verantwortung für alle Schnittstellen
- Dokumentation: `docs/contracts.md`
- Release- & Versionsverantwortung
- Unterstützung bei Mergekonflikten

### Rolle 2: Businesslogik & Report A
- Implementierung der Kern-Use-Cases
- Umsetzung von Report A (z.B. Lagerstandsreport)
- Zugehörige Tests
- Beispiel: Lagerbewirtschaftung, Bestandsverwaltung

### Rolle 3: Report B & Qualität
- Umsetzung von Report B (z.B. Bewegungsprotokoll, Statistik)
- Erweiterte Tests (Rand- & Fehlerfälle)
- Dummy-Daten erstellen
- Test-Coverage erhöhen

### Rolle 4: GUI & Interaktion
- Konzeption & Umsetzung der GUI
- Anbindung an die Businesslogik
- GUI-Tests oder Testbeschreibung

## Entwicklungsablauf

### Versionsmeilensteine

- **v0.1** – Projektstart, Rollen, erste Contracts
- **v0.2** – Architektur & Walking Skeleton
- **v0.3** – Kernlogik & GUI-Minimum
- **v0.4** – erste Reports
- **v0.5** – Tests & Stabilisierung
- **v1.0** – fertige, stabile Version

### Git-Workflow

```bash
# Feature-Branch erstellen
git checkout -b feature/<rollenname>/<feature>

# Commits mit aussagekräftigen Meldungen
git commit -m "Feat: Beschreibung"
git commit -m "Fix: Bugfix-Beschreibung"
git commit -m "Docs: Dokumentation"
git commit -m "Test: Testcode"

# Merge mit Dokumentation
git push origin feature/...
# Pull Request erstellen → Review → Merge
```

### Dokumentation der Versionen

Jedes Gruppen mitglied führt: `docs/changelog_<name>.md`

Beispiel-Format:
```markdown
## [0.2] - 2025-02-06

### Implementiert
- Warehouse Service erstellt
- Produktklasse mit Validierung

### Tests
- test_product_creation
- test_update_quantity

### Commits
- abc1234 Feat: Warehouse Service
- def5678 Test: Product Tests
```

## Testing

### Unit Tests ausführen

```bash
pytest tests/unit/ -v
```

### Integration Tests

```bash
pytest tests/integration/ -v
```

### Mit Coverage

```bash
pytest --cov=src tests/
```

## Reports

Reports sind eigenständige Komponenten, die:
- Auf gespeicherten Daten basieren
- Deterministisch und testbar sind
- Verschiedene Ausgabeformen unterstützen (Text, Tabelle, Grafik)

Beispiel Report A (Lagerbestandsbericht):
```
===============================================================
LAGERBESTANDSBERICHT
===============================================================

ID: LAPTOP-001
  Name: ProBook Laptop
  Kategorie: Elektronik
  Bestand: 6
  Preis: 1200.00 €
  Gesamtwert: 7200.00 €

Total: 7800.00 €
===============================================================
```

## Projektmanagement-Dokumente

Die folgenden PM-Dokumente sind als Word/Markdown zu erstellen:

1. **Projektcharta**
   - Ziel & Nicht-Ziele
   - Stakeholder
   - Risiken

2. **Vorgehensmodell**
   - Beschreibung (iterativ / Scrum-light)
   - Begründung

3. **Projektstrukturplan (PSP)**
   - Gliederung der Projektarbeit

4. **Gantt-Diagramm**
   - Zeitliche Planung über 8 Wochen

5. **Rollenverteilung**
   - Aufgaben pro Rolle

**Speichern unter:** `docs/projektmanagement.md` oder als separate PDF

## Versionierung

### Version Format
```
MAJOR.MINOR.PATCH
0.1.0
```

### Tags im Repository
```bash
git tag -a v0.1 -m "v0.1 - Projektstart"
git push origin v0.1
```

## Häufige Aufgaben

### Neues Produkt hinzufügen
```python
from src.services import WarehouseService
from src.adapters.repository import RepositoryFactory

repository = RepositoryFactory.create_repository("memory")
service = WarehouseService(repository)

product = service.create_product(
    product_id="P001",
    name="Laptop",
    description="High-End Laptop",
    price=1200.0,
    category="Elektronik",
    initial_quantity=5
)
```

### Bestand aktualisieren
```python
service.add_to_stock("P001", 3, reason="Neuer Einkauf", user="Max Mustermann")
service.remove_from_stock("P001", 2, reason="Verkauf", user="Anna Schmidt")
```

### Lagerbestandswert berechnen
```python
total_value = service.get_total_inventory_value()
print(f"Gesamtwert: {total_value:.2f} €")
```

## Known Issues

Siehe `docs/known_issues.md`

## Lizenz

Schulprojekt - TGM

## Kontakt

Projektverantwortung: [Rolle 1 Person]
