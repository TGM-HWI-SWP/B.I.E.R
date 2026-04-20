# Architektur-Dokumentation

## Übersicht

B.I.E.R folgt der **Hexagonalen Architektur** (Ports & Adapters). Jede Schicht kommuniziert ausschließlich über abstrakte Schnittstellen (`contracts/`), was Testbarkeit, Austauschbarkeit und klare Verantwortlichkeiten garantiert.

---

## Schichten-Modell

```
┌──────────────────────────────────────────────────────────────┐
│                  Frontend (Flask / Jinja2)                   │
│   gui.py  ·  base.html  ·  page1-9 templates               │
└─────────────────────────┬────────────────────────────────────┘
                          │  ruft auf
┌─────────────────────────▼────────────────────────────────────┐
│                  Backend (Service-Layer)                     │
│      ProductService  ·  WarehouseService  ·  InventoryService│
└─────────────────────────┬────────────────────────────────────┘
                          │  nutzt Port
┌─────────────────────────▼────────────────────────────────────┐
│               Contracts (Abstrakte Ports)                    │
│  DatabasePort  ·  ProductServicePort  ·  WarehouseServicePort│
│  InventoryServicePort                                        │
└─────────────────────────┬────────────────────────────────────┘
                          │  implementiert
┌─────────────────────────▼────────────────────────────────────┐
│               DB-Adapter (MongoDB)                           │
│  MongoDBAdapter  ·  db/init/setup.py                         │
└──────────────────────────────────────────────────────────────┘
                          │
                 ┌────────▼───────┐
                 │   MongoDB      │
                 │ (Docker / lokal│
                 └────────────────┘
```

---

## Paketstruktur

```
src/bierapp/
├── contracts/
│   ├── __init__.py           # Re-exportiert alle 6 Ports
│   ├── database_port.py      # DatabasePort (ABC)
│   ├── product_port.py       # ProductServicePort (ABC)
│   ├── warehouse_port.py     # WarehouseServicePort (ABC)
│   ├── inventory_port.py     # InventoryServicePort (ABC)
│   ├── report_port.py        # ReportPort (ABC)
│   └── http_port.py          # HttpResponsePort (ABC)
├── backend/
│   ├── models.py             # Domain-Dataclasses: Product, Warehouse, InventoryEntry, Event
│   ├── utils.py              # get_current_timestamp() – gemeinsame Hilfsfunktion
│   ├── product_service.py    # ProductService
│   ├── warehouse_service.py  # WarehouseService
│   ├── inventory_service.py  # InventoryService
│   └── services.py           # Aggregator-Modul (re-exportiert alle drei Services)
├── db/
│   ├── mongodb.py            # MongoDBAdapter (implementiert DatabasePort)
│   └── init/
│       ├── setup.py          # Idempotentes DB-Setup-Script
│       └── seed.py           # Seed-Testdaten
└── frontend/
    └── flask/
        ├── gui.py            # Flask-App, Routen, Template-Rendering
        ├── helpers.py        # Statistik- und Anreicherungsberechnungen
        └── http_adapter.py   # FlaskHttpAdapter (implementiert HttpResponsePort)

src/resources/
├── pictures/                 # Statische Bilddateien (BIER ICONS, Logos)
└── templates/
    ├── base.html             # Bootstrap-5-Basis-Template mit Dark-Theme
    ├── page1_products.html   # Produktverwaltung (Liste, Suche, Lager-Filter)
    ├── page2_product_edit.html  # Produkt bearbeiten/erstellen (Multi-Lager)
    ├── page3_warehouse_list.html # Lagerliste
    ├── page4_statistics.html # Statistik-Dashboard
    ├── page5_history.html    # Änderungen-/Historienseite
    ├── page6_procurement.html # Beschaffung / Bestellvorschläge
    ├── page7_picking.html    # Kommissionierung
    ├── page7_pick_print.html # Druckansicht Kommissionierliste
    ├── page8_settings.html   # UI-Settings / Theme Profiles
    └── page9_user_admin.html # User-Administration mit Audit-Log

tests/
├── conftest.py               # Shared Fixtures (mock_db, Services, Flask-Client)
├── unit/
│   └── test_domain.py        # Unit-Tests für alle Services
└── integration/
    ├── test_flask.py         # Flask-Routen via Test-Client
    ├── test_integration.py   # Service-Interaktionstests
    └── test_mongodb.py       # Live-Connectivity (überspringt ohne Docker)
```

---

## Komponenten im Detail

### 1. Contracts (`src/bierapp/contracts/`)

Jeder Port ist in einer eigenen Datei definiert; `contracts/__init__.py` re-exportiert alle für bequeme Importe:

| Port | Datei | Zweck |
|---|---|---|
| `DatabasePort` | `database_port.py` | MongoDB-Operationen (CRUD + Suche) |
| `ProductServicePort` | `product_port.py` | Produkt-Geschäftslogik |
| `WarehouseServicePort` | `warehouse_port.py` | Lager-Geschäftslogik |
| `InventoryServicePort` | `inventory_port.py` | Bestandsverwaltungs-Logik |
| `ReportPort` | `report_port.py` | Report-Generierung |
| `HttpResponsePort` | `http_port.py` | Flask HTTP-Adapter |

Alle anderen Schichten importieren nur diese Interfaces — nie konkrete Klassen.

### 2. DB-Adapter (`src/bierapp/db/`)

**`MongoDBAdapter`** implementiert `DatabasePort`:
- Verbindungsaufbau über Umgebungsvariablen (`MONGO_HOST`, `MONGO_PORT`, `MONGO_USER`, `MONGO_PASS`, `MONGO_DB`)
- Collections: `produkte`, `lager`, `inventar`, `events`, `lieferanten`, `bestellungen`, `abteilungen`, `picklisten`, `users`, `user_settings`, `app_settings`
- Spezialabfragen: `find_inventar_by_lager()`, `find_inventar_entry()`
- Kontext-Manager-Support (`__enter__` / `__exit__`)
- `_serialize()` konvertiert BSON `ObjectId` → `str`

**`db/init/setup.py`** – idempotentes Setup-Script:
- Erstellt Collections und Indizes beim ersten Start
- `produkte`: Index auf `name`
- `lager`: Unique Index auf `lagername`
- `inventar`: Compound Unique Index auf `(lager_id, produkt_id)`
- `events`: Index auf `timestamp` (für sortierte Historie)

**`db/init/seed.py`** – Seed-Script für Testdaten:
- Legt 5 Beispiel-Lager an (u. a. „Depot Innsbruck“)
- Erzeugt ~150 Produkte mit realistischen Gewichten und Preisen (`preis` + `waehrung="EUR"`)
- Befüllt jedes Lager mit einem zufälligen Teil der Produkte und zufälligen Mengen
- Ausführbar als `python -m bierapp.db.init.setup`

### 3. Service-Layer (`src/bierapp/backend/`)

Jeder Service hat eine eigene Datei. `services.py` ist ein schlanker Aggregator, der alle drei re-exportiert.

**`backend/models.py`** – Domain-Dataclasses:
- `Product` – Felder: `name`, `description`, `weight`, `price`; validiert in `__post_init__`; `to_doc()` → MongoDB-Dict
- `Warehouse` – Felder: `name`, `address`, `max_slots`; validiert in `__post_init__`; `to_doc()` → MongoDB-Dict
- `InventoryEntry` – Felder: `warehouse_id`, `product_id`, `quantity`; validiert in `__post_init__`; `to_doc()` → MongoDB-Dict
- `Event` – Felder: `timestamp`, `entity_type`, `action`, `entity_id`, `summary`, `performed_by`; `to_doc()` → MongoDB-Dict

**`backend/utils.py`**:
- `get_current_timestamp() -> str` – aktueller UTC-Zeitstempel als ISO-8601-String (`...Z`)

**`product_service.py` → `ProductService`** implementiert `ProductServicePort`:
- `create_product(name, description, weight)` – Validiert: nicht-leerer Name, Gewicht ≥ 0
- `get_product(id)` – per `find_by_id`
- `list_products()` – per `find_all`
- `update_product(id, felder)` – `KeyError` wenn nicht vorhanden
- `delete_product(id)` – `KeyError` wenn nicht vorhanden

**`warehouse_service.py` → `WarehouseService`** implementiert `WarehouseServicePort`:
- `create_warehouse(warehouse_name, address, max_slots)` – Validiert: nicht-leer, max_slots > 0
- `get_warehouse(id)` / `list_warehouses()` / `update_warehouse(id, felder)` / `delete_warehouse(id)`

**`inventory_service.py` → `InventoryService`** implementiert `InventoryServicePort`:
- `add_product(warehouse_id, product_id, quantity)` – Bei vorhandenem Eintrag wird Menge addiert
- `update_quantity(warehouse_id, product_id, quantity)` – `ValueError` bei negativer Menge
- `remove_product(warehouse_id, product_id)` – `KeyError` wenn kein Eintrag
- `remove_stock(warehouse_id, product_id, quantity)` – Reduziert Menge; löscht Eintrag bei 0
- `move_product(source_id, target_id, product_id, quantity)` – Bestand zwischen Lagern verschieben
- `get_total_inventory_value(warehouse_id)` – Gesamtwert (Preis × Menge) eines Lagers
- `list_inventory(lager_id)` – Reichert jeden Eintrag mit Produktname + Beschreibung an

### 4. Frontend (`src/bierapp/frontend/flask/`)

**`gui.py`** – Flask-Anwendung mit Lazy-Singleton-Pattern:

```python
_db: Optional[MongoDBAdapter] = None

def get_db() -> MongoDBAdapter:      # erstellt Verbindung bei Bedarf
def get_product_service() -> ProductServicePort:
def get_warehouse_service() -> WarehouseServicePort:
def get_inventory_service() -> InventoryServicePort:
```

**`helpers.py`** – alle Statistik- und Anreicherungsberechnungen aus `gui.py` extrahiert:
- `enrich_warehouses()` – hängt `menge` und `num_produkte` an jeden Lager-Dict
- `compute_warehouse_aggregates()`, `compute_warehouse_stats()`, `compute_utilisation()`
- `compute_category_counts()`, `compute_top10_products()`
- `compute_warehouse_top_products()`, `compute_warehouse_values()`

**`http_adapter.py`** – `FlaskHttpAdapter(HttpResponsePort)` mit `success()` und `error()`

**Routen-Übersicht:**

| Methode | Route | Beschreibung |
|---|---|---|
| GET | `/` | Rendert Dashboard (Page 1 – Produktverwaltung) |
| GET | `/favicon.ico` | Favicon |
| GET | `/logo` | Logo-Bild |
| GET | `/inventar` | Redirect zum ersten Lager oder leerer Statistikseite |
| GET | `/inventar/<lager_id>` | Bestand eines Lagers (delegiert an Statistik-Dashboard) |
| POST | `/inventar/<lager_id>/hinzufuegen` | Produkt einbuchen |
| POST | `/inventar/<lager_id>/<produkt_id>/aktualisieren` | Menge ändern |
| POST | `/inventar/<lager_id>/<produkt_id>/entfernen` | Produkt ausbuchen |

**UI-Routen (9 Seiten):**

| Methode | Route | Beschreibung |
|---|---|---|
| GET | `/ui/produkte` | **Page 1** – Produktverwaltung (inkl. Lager-Filter) |
| GET | `/ui/produkt/neu` | **Page 2** – Neues Produkt erstellen |
| POST | `/ui/produkt/neu` | Produkt speichern (neu) inkl. Lagerzuordnungen |
| GET | `/ui/produkt/<id>/bearbeiten` | **Page 2** – Produkt bearbeiten |
| POST | `/ui/produkt/<id>/speichern` | Produkt speichern (Update; synchronisiert alle Lagerbestände) |
| POST | `/ui/produkt/<id>/verschieben` | Produktbestand von einem Lager in ein anderes verschieben |
| POST | `/ui/produkt/<id>/loeschen` | Produkt und alle zugehörigen Bestände löschen |
| GET | `/ui/lager` | **Page 3** – Lagerliste |
| POST | `/ui/lager/neu` | Lager erstellen |
| POST | `/ui/lager/<id>/bearbeiten` | Lager aktualisieren |
| POST | `/ui/lager/<id>/loeschen` | Lager löschen (inkl. Inventarbereinigung) |
| GET | `/ui/statistik` | **Page 4** – Statistik-Dashboard |
| GET | `/ui/historie` | **Page 5** – Historie aller Änderungen (Events) |
| GET | `/ui/bestellungen` | **Page 6** – Beschaffung / Bestellvorschläge |
| GET | `/ui/kommissionierung` | **Page 7** – Kommissionierung |
| GET | `/ui/einstellungen` | **Page 8** – Personalisierung / Themes / Profile |
| GET | `/ui/admin/benutzer` | **Page 9** – Manager-only User-Administration |
| POST | `/ui/historie/export` | Historie als TXT-Datei herunterladen |

**Auth- und Settings-APIs:**

| Methode | Route | Beschreibung |
|---|---|---|
| GET | `/login` | Login-Seite |
| POST | `/login` | Session-Login |
| POST | `/logout` | Session-Logout |
| GET | `/api/ui-settings/bootstrap` | Lädt DB-persistente UI-Profile + Rollenpolicy |
| PUT | `/api/ui-settings/profile/<role>` | Speichert UI-Profile pro Benutzer/Rolle |
| DELETE | `/api/ui-settings/profile/<role>` | Setzt UI-Profil auf Default zurück |
| GET/PUT | `/api/ui-settings/role-policy` | Lesen/Schreiben der Clerk-Defaults/Locks |

### 5. Templates (`src/resources/templates/`)

Alle Templates erben von `base.html` und verwenden Bootstrap 5.3, Bootstrap Icons 1.11, Chart.js 4.4 mit einem modernen Dark-Theme.

**Design-Merkmale:**
- Modernes Dark-Theme mit benutzerdefinierten CSS-Variablen
- Gerundete Ecken (`border-radius: 12px`)
- Sticky Navigation und Action Bars
- Autocomplete-Suche
- Modal-Dialoge für Bestätigungen
- Responsive Layout

| Template | Seite | Inhalt |
|---|---|---|
| `base.html` | — | Navigation, Flash-Messages, Modals, Block-Struktur |
| `page1_products.html` | 1 | Produktverwaltung: Liste, Suche mit Autocomplete, Lager-Filter, "Produkt verschieben"-Dialog, "+ Neues Produkt" Button |
| `page2_product_edit.html` | 2 | Produkt bearbeiten/erstellen: Pflichtfelder (Name, Preis, Gewicht), Bestände pro Lager (Multi-Lager), Default-Attribute + benutzerdefinierte Attribute, Sticky Action Bar, Delete-Modal |
| `page3_warehouse_list.html` | 3 | Lagerliste: Tabelle mit Inline-Bearbeitung, Kapazitätsbalken, Create/Delete Modals |
| `page4_statistics.html` | 4 | Statistik: KPI-Karten, Donut-Charts, Bar-Charts, Top-Produkte Liste |
| `page5_history.html` | 5 | Historie: Tabelle aller Events (inkl. User-Admin-Audits) |
| `page6_procurement.html` | 6 | Beschaffung: Lieferanten, Bestellvorschläge, Freigabe-Workflow |
| `page7_picking.html` | 7 | Kommissionierung: Picklisten und Abschluss-Workflow |
| `page7_pick_print.html` | 7 | Druckansicht für Picklisten |
| `page8_settings.html` | 8 | Benutzer-Settings: Theme, Dichte, Motion, Profile Import/Export |
| `page9_user_admin.html` | 9 | Manager-Userverwaltung + Audit-Log |

**Page 1 – Produktverwaltung:**
- Großer "+" Button zum Erstellen neuer Produkte
- Live-Suche mit Autocomplete-Vorschlägen (Tastaturnavigation, Dark-Mode-optimiert)
- Produktliste mit Klick zum Bearbeiten
- Lager-Filter (Dropdown); zeigt pro Produkt nur den Bestand in diesem Lager an
- "Produkt verschieben"-Dialog zum Umlagern von Beständen zwischen Lagern

**Page 2 – Produktbearbeitung:**
- Großer BACK-Button
- Produktname mit ID in Klammern (bei bestehenden Produkten)
- Pflichtfelder: Name, Preis, Gewicht (Preis + Gewicht werden serverseitig validiert)
- Bestände in allen Lagern: eine Zeile pro Lager mit eigener Mengen-Eingabe (Multi-Lager-Unterstützung)
- Default-Attribute (nicht löschbar): Preis, Währung, Gewicht, Lieferant, Beschreibung
- Benutzerdefinierte Attribute (dynamisch hinzufügbar/löschbar)
- Sticky Bottom Action Bar: Speichern, Verwerfen, Zurücksetzen, Attribut hinzufügen/löschen
- Bestätigungs-Modal für das Löschen eines Produkts (inkl. aller Lagerbestände)

**Page 3 – Lagerliste:**
- Lagername, Adresse, Max. Plätze, Belegung (%)
- Kapazitätsbalken mit Farbcodierung
- Inline-Bearbeitung
- Lösch-Warnung (alle Produkte werden gelöscht)

**Page 4 – Statistik:**
- KPI-Karten: Produkte gesamt, Lager gesamt, Einheiten gesamt, Höchster Einzelbestand
- Donut-Chart: Produktverteilung je Lager
- Bar-Chart: Top-Produkte nach Bestand
- Bar-Chart: Lagerauslastung (%)
- Pie-Chart: Kategorieverteilung
- Top-Produkte Liste mit Rang und Fortschrittsbalken

---

## Datenfluss (Beispiel: Produkt erstellen - Neue UI)

```
1. Nutzer klickt "+ Neues Produkt" auf Page 1
2. Browser ruft GET /ui/produkt/neu auf
3. gui.py: page2_product_edit() rendert page2_product_edit.html
4. Nutzer füllt Formular aus und klickt "Speichern"
5. Browser sendet POST /ui/produkt/neu
6. gui.py: page2_create_product() liest request.form
7. get_product_service() gibt ProductService(get_db()) zurück
8. ProductService.create_product() validiert Eingaben und erstellt Produkt
9. MongoDBAdapter.insert("produkte", doc) schreibt in MongoDB
10. Redirect auf GET /ui/produkte → Flash-Message "Erfolgreich"
```

---

## Dependency Injection

Services erhalten den DB-Adapter über den Konstruktor:

```
python
# Produktion
service = ProductService(MongoDBAdapter())

# Test (Mocking)
mock_db = MagicMock()
service = ProductService(mock_db)
```

Dadurch sind alle Services ohne echte Datenbankverbindung vollständig testbar.

---

## Infrastruktur & Docker

`docker-compose.yml` startet drei Services:

| Service | Port | Beschreibung |
|---|---|---|
| `mongodb` | 27017 | MongoDB 7 mit Auth |
| `mongo-express` | 8081 | Web-UI für MongoDB |
| `app` | 5000 | Flask-Anwendung |

Umgebungsvariablen (konfigurierbar über `.env` oder Docker Compose):

| Variable | Standard |
|---|---|
| `MONGO_HOST` | `mongodb` |
| `MONGO_PORT` | `27017` |
| `MONGO_DB` | `bierapp` |
| `MONGO_USER` | `admin` |
| `MONGO_PASS` | `secret` |
| `FLASK_HOST` | `0.0.0.0` |
| `FLASK_PORT` | `5000` |
| `FLASK_SECRET` | `bier-dev-secret` |

---

## Aktueller Delta-Stand (2026-04-20)

- Auth und benutzerspezifische Einstellungen liegen vollständig in MongoDB.
- User-Admin-Mutationen erzeugen Audit-Events in `events` mit `entity_type = user_admin`.
- Settings sind rollenabhängig (`manager`/`clerk`) und über Manager-Policy steuerbar (Defaults + Locks für Clerks).

**Letzte Aktualisierung:** 2026-04-20
**Version:** 1.4
