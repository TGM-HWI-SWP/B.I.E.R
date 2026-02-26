# Changelog – B.I.E.R

Alle nennenswerten Änderungen am Projekt werden in dieser Datei dokumentiert.

---

## [v1.1] – 2026-02-26

### Implementiert

- **Neue 5-Seiten UI** mit modernem Dark-Theme:
  - `base.html` – Sticky Navigation, Flash-Messages, Modals, Bootstrap 5 + Bootstrap Icons
  - `page1_products.html` – Produktverwaltung mit Live-Suche, Autocomplete und Lager-Filter
  - `page2_product_edit.html` – Produkt erstellen/bearbeiten mit Pflichtfeldern (Name, Preis, Gewicht), Multi-Lager-Beständen und benutzerdefinierten Attributen
  - `page3_warehouse_list.html` – Lagerliste mit Inline-Bearbeitung, Kapazitätsbalken und automatischer Berechnung von Anzahl Produkten / Gesamtmenge
  - `page4_statistics.html` – Statistik-Dashboard mit Chart.js (Donut, Bar, Pie Charts, Gewichtshistogramm)
  - `page5_history.html` – Historien-Seite für alle Änderungen (Produkte, Lager, Inventar)

### Geschäftslogik & Datenmodell

- Multi-Lager-Unterstützung für Produkte:
  - Ein Produkt kann in mehreren Lagern mit unterschiedlichen Mengen geführt werden
  - Page 2 (Produkt bearbeiten) zeigt eine Zeile pro Lager mit eigener Mengen-Eingabe
  - Speichern synchronisiert alle Inventar-Einträge (`inventar`-Collection) pro Produkt (Anlegen, Aktualisieren, Entfernen)
- Produktverwaltung (Page 1):
  - Lager-Filter (`?lager_id=...`) zeigt nur Produkte mit Bestand im gewählten Lager
  - Die angezeigte Menge bezieht sich bei Filterung immer auf das gefilterte Lager
  - "Produkt verschieben"-Dialog verschiebt Bestand von einem Quelllager in ein Ziellager
- Historie:
  - Services schreiben Events in die neue `events`-Collection
  - `/ui/historie` rendert alle Events sortiert (neueste zuerst) mit lesbarem Zeitstempel
- Seed-Daten (`db/init/seed.py`):
  - Legt 5 Beispiel-Lager an (inkl. „Depot Innsbruck“)
  - Erzeugt ca. 150 Produkte mit realistischen Gewichten und Preisen (`preis` + `waehrung="EUR"`)
  - Befüllt alle Lager mit zufälligen Mengen pro Produkt

### UI Design-Merkmale

- Modernes Dark-Theme mit benutzerdefinierten CSS-Variablen
- Gerundete Ecken (`border-radius: 12px`)
- Sticky Navigation und Action Bars
- Autocomplete-Suche mit Tastaturnavigation
- Bessere Lesbarkeit der Autocomplete-Texte im Dark-Mode
- Modal-Dialoge für Bestätigungen (u. a. Produkt- und Lager-Löschbestätigungen)
- Responsive Layout

### Neue Flask-Routen

- `/ui/produkte` – Page 1: Produktverwaltung (inkl. Lager-Filter)
- `/ui/produkt/neu` – Page 2: Neues Produkt erstellen (inkl. initialer Lagerzuordnungen)
- `/ui/produkt/<id>/bearbeiten` – Page 2: Produkt bearbeiten (inkl. Multi-Lager-Beständen)
- `/ui/produkt/<id>/speichern` – Produkt speichern (POST, synchronisiert Inventar)
- `/ui/produkt/<id>/verschieben` – Produktbestand von einem Lager in ein anderes verschieben
- `/ui/produkt/<id>/loeschen` – Produkt und alle zugehörigen Bestände löschen
- `/ui/lager` – Page 3: Lagerliste
- `/ui/lager/neu` – Lager erstellen (POST)
- `/ui/lager/<id>/bearbeiten` – Lager aktualisieren (POST)
- `/ui/lager/<id>/loeschen` – Lager löschen (POST, inkl. Inventarbereinigung)
- `/ui/statistik` – Page 4: Statistik-Dashboard
- `/ui/historie` – Page 5: Historie aller Änderungen

### Tests erweitert

- `tests/integration/test_flask.py`: Zusätzliche Tests für die neue UI (`TestNewUIRoutes`)
  - Page 1–4 Route-Tests inkl. Chart-Canvas-Checks
  - Create/Update/Löschen-Workflows für Produkte und Lager
  - Grundlegende Tests für Page 2 (Produkt anlegen/ändern)
- Weitere Tests für Multi-Lager-Logik und Historie werden sukzessive ergänzt.

### Dokumentation aktualisiert

- `docs/architecture.md`: Neue Template-Struktur, Multi-Lager-Logik und Routen dokumentiert
- `docs/tests.md`: Test-Abdeckung für neue UI und Teststufen dokumentiert

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
