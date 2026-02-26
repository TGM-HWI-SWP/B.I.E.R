# Changelog – B.I.E.R

Alle nennenswerten Änderungen am Projekt werden in dieser Datei dokumentiert.

---

## [v1.1] – 2026-02-26

### Implementiert

- **Neue 4-Seiten UI** mit modernem Dark-Theme:
  - `base.html` – Sticky Navigation, Flash-Messages, Modals, Bootstrap 5 + Bootstrap Icons
  - `page1_products.html` – Produktverwaltung mit Live-Suche und Autocomplete
  - `page2_product_edit.html` – Produkt erstellen/bearbeiten mit Default- und benutzerdefinierten Attributen
  - `page3_warehouse_list.html` – Lagerliste mit Inline-Bearbeitung und Kapazitätsbalken
  - `page4_statistics.html` – Statistik-Dashboard mit Chart.js (Donut, Bar, Pie Charts)

### UI Design-Merkmale

- Modernes Dark-Theme mit benutzerdefinierten CSS-Variablen
- Gerundete Ecken (`border-radius: 12px`)
- Sticky Navigation und Action Bars
- Autocomplete-Suche mit Tastaturnavigation
- Modal-Dialoge für Bestätigungen
- Responsive Layout

### Neue Flask-Routen

- `/ui/produkte` – Page 1: Produktverwaltung
- `/ui/produkt/neu` – Page 2: Neues Produkt erstellen
- `/ui/produkt/<id>/bearbeiten` – Page 2: Produkt bearbeiten
- `/ui/produkt/<id>/speichern` – Produkt speichern (POST)
- `/ui/lager` – Page 3: Lagerliste
- `/ui/lager/neu` – Lager erstellen (POST)
- `/ui/lager/<id>/bearbeiten` – Lager aktualisieren (POST)
- `/ui/lager/<id>/loeschen` – Lager löschen (POST)
- `/ui/statistik` – Page 4: Statistik-Dashboard

### Tests erweitert

- `tests/integration/test_flask.py`: 10 neue Tests für die neue UI (`TestNewUIRoutes`)
  - Page 1-4 Route-Tests
  - Create/Update/DELETE Tests für Produkte und Lager
  - Chart-Canvas Element-Tests

### Dokumentation aktualisiert

- `docs/architecture.md`: Neue Template-Struktur und Routen dokumentiert
- `docs/tests.md`: Test-Abdeckung für neue UI dokumentiert

---

## [v1.0] – 2026-02-25

### Implementiert

- Vollständige Teststrategie: Unit-Tests (26), Flask-Integrationstests (19), Service-Integrationstests (5)
- Style-Guide-Konformität aller Python-Dateien (Google Docstrings, `from`-Imports, keine Trennzeilen)
- `tests/conftest.py` mit gemeinsamen Fixtures (`mock_db`, Services, Flask-Test-Client)
- `test_mongodb.py` überspringt automatisch bei fehlender Docker-Verbindung
- Alle Dokumentationsdateien auf aktuellen Stand gebracht

### Fixed

- `pyproject.toml`: `package-dir = {"" = "src"}` korrigiert → `bierapp` korrekt importierbar
- `gui.py`: `import os` → `from os import environ, path`; Union-Typ → `Optional[MongoDBAdapter]`
- `setup.py`: `import os, sys` → `from os import environ`, `from sys import exit, stderr`

---

## [v0.3] – 2026-02-22

### Implementiert

- Flask-Web-UI vollständig: Dashboard, Produkte-, Lager-, Inventar-Seiten
- Alle CRUD-Routen mit Fehlerbehandlung und Flash-Messages
- Bootstrap-5-Templates: `layout.html`, `index.html`, `produkte.html`, `lager.html`, `inventar.html`
- Service-Layer: `ProductService`, `WarehouseService`, `InventoryService` mit vollständiger Validierung
- Google-Style Docstrings in allen Service-Methoden

### Commits

- PHinterbauer Feat: Flask GUI vollständig mit Templates und Business-Logik

---

## [v0.2] – 2026-02-21

### Implementiert

- `src/bierapp/db/mongodb.py` – `MongoDBAdapter` implementiert `DatabasePort`
- `src/bierapp/db/init/setup.py` – idempotentes DB-Setup mit Index-Erstellung
- `src/bierapp/db/init/__init__.py` – Package-Marker
- `pyproject.toml` mit `src.bierapp.db.init` ergänzt

### Tests geschrieben

- `tests/integration/test_mongodb.py` – Ping-Test gegen laufende MongoDB

### Commits

- PHinterbauer Feat: MongoDB-Adapter und DB-Initialisierung

---

## [v0.1] – 2026-02-20

### Implementiert

- Docker Compose Stack (MongoDB, Mongo Express, Flask-App)
- Projektstruktur mit Hexagonaler Architektur
- `contracts.py` mit abstrakten Ports (`DatabasePort`, `ProductServicePort`, `WarehouseServicePort`, `InventoryServicePort`)
- Grundlegende `gui.py`-Stub mit Flask-App

### Tests geschrieben

- `tests/integration/test_mongodb.py` (Basis-Ping)

### Commits

- PHinterbauer Feat: added docker, mongodb and flask scaffold

---

**Letzte Aktualisierung:** 2026-02-26
