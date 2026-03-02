# Changelog – B.I.E.R

Alle nennenswerten Änderungen am Projekt werden in dieser Datei dokumentiert.

---

## [v1.3] – 2026-03-02

### Refactoring: Domain-Dataclasses eingeführt

- **`backend/models.py` (neu)** – zentrale Dataclass-Definitionen für alle Domainobjekte:
  - `Product` – Felder `name`, `description`, `weight`, `price`; Validierung in `__post_init__` (nicht-leerer Name, Gewicht ≥ 0, Preis ≥ 0); `to_doc()` liefert MongoDB-Dict
  - `Warehouse` – Felder `name`, `address`, `max_slots`; Validierung in `__post_init__` (nicht-leerer Name, `max_slots` > 0); `to_doc()` liefert MongoDB-Dict
  - `InventoryEntry` – Felder `warehouse_id`, `product_id`, `quantity`; Validierung in `__post_init__` (Menge ≥ 0); `to_doc()` liefert MongoDB-Dict
  - `Event` – Felder `timestamp`, `entity_type`, `action`, `entity_id`, `summary`, `performed_by`; `to_doc()` liefert MongoDB-Dict
- **`product_service.py`** – `create_product`, `update_product` und `delete_product` verwenden `Product`- bzw. `Event`-Dataclass statt roher Dicts
- **`warehouse_service.py`** – `create_warehouse`, `update_warehouse` und `delete_warehouse` verwenden `Warehouse`- bzw. `Event`-Dataclass statt roher Dicts
- **`inventory_service.py`** – `add_product`, `update_quantity`, `remove_product`, `remove_stock` und `move_product` verwenden `InventoryEntry`- und `Event`-Dataclass statt roher Dicts
- Validierungslogik aus allen Service-Methoden in die `__post_init__`-Methoden der Dataclasses verschoben (DRY-Prinzip)
- Alle 33 Unit-Tests weiterhin grün

---

## [v1.2] – 2026-03-02

### Refactoring: Codestruktur & Bereinigung

- **`contracts/` Package** – `contracts.py` durch ein Package ersetzt; jeder Port hat eine eigene Datei (`database_port.py`, `product_port.py`, `warehouse_port.py`, `inventory_port.py`, `report_port.py`, `http_port.py`); `contracts/__init__.py` re-exportiert alle Ports für nahtlose Rückwärtskompatibilität
- **Service-Schicht aufgeteilt** – `services.py` (615 Zeilen) aufgeteilt in:
  - `backend/product_service.py` – `ProductService`
  - `backend/warehouse_service.py` – `WarehouseService`
  - `backend/inventory_service.py` – `InventoryService`
  - `backend/utils.py` – `get_current_timestamp()` (timezone-aware UTC, kein `utcnow()`)
  - `backend/services.py` – schlanker Aggregator (re-exportiert alle drei Services)
- **Flask-Schicht aufgeteilt** – aus `gui.py` extrahiert:
  - `frontend/flask/helpers.py` – 8 Statistik- und Anreicherungsfunktionen
  - `frontend/flask/http_adapter.py` – `FlaskHttpAdapter(HttpResponsePort)`
- **`db/init/seed.py` vereinfacht** – `_gen_products()` aufgeteilt in 12 benannte Funktionen (eine pro Produktkategorie)
- **`db/mongodb.py`** – `_build_uri()` aus `connect()` extrahiert

### Legacy-Routen entfernt

- **Gelöscht:** `/produkte`, `/produkte/neu`, `/produkte/<id>/bearbeiten`, `/produkte/<id>/loeschen`
- **Gelöscht:** `/lager`, `/lager/neu`, `/lager/<id>/bearbeiten`, `/lager/<id>/loeschen`
- **Vereinfacht:** `/logo/<variant>` → `/logo` (Parameter entfernt)
- Alle Funktionalität ist vollständig über die `/ui/`-Routen erreichbar

### Code-Qualität

- Alle List-Comprehensions, Set-Comprehensions und `lambda`-Sorts durch explizite `for`-Schleifen ersetzt
- Maximal eine Leerzeile zwischen Code-Abschnitten (keine doppelten Leerzeilen)
- `datetime.utcnow()` (deprecated) durch `datetime.now(timezone.utc)` ersetzt

### Tests

- `TestProdukte` und `TestLager` auf `/ui/`-Routen umgestellt (kein Legacy mehr)
- `test_page5_history_returns_200` ergänzt
- **Ergebnis:** 80 passed, 2 skipped (vorher 59 passed)

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

**Letzte Aktualisierung:** 2026-03-02
