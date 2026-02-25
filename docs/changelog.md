# Changelog – B.I.E.R

Alle nennenswerten Änderungen am Projekt werden in dieser Datei dokumentiert.

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

**Letzte Aktualisierung:** 2026-02-25
