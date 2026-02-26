# Architektur-Dokumentation

## Übersicht

B.I.E.R folgt der **Hexagonalen Architektur** (Ports & Adapters). Jede Schicht kommuniziert ausschließlich über abstrakte Schnittstellen (`contracts.py`), was Testbarkeit, Austauschbarkeit und klare Verantwortlichkeiten garantiert.

---

## Schichten-Modell

```
┌──────────────────────────────────────────────────────────────┐
│                  Frontend (Flask / Jinja2)                   │
│   gui.py  ·  base.html  ·  page1-4 templates               │
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
├── contracts.py              # Abstrakte Ports (ABC-Klassen)
├── backend/
│   └── services.py           # ProductService, WarehouseService, InventoryService
├── db/
│   ├── mongodb.py            # MongoDBAdapter (implementiert DatabasePort)
│   └── init/
│       └── setup.py          # Idempotentes DB-Setup-Script
└── frontend/
    └── flask/
        └── gui.py            # Flask-App, Routen, Template-Rendering

src/resources/
├── pictures/                 # Statische Bilddateien (BIER ICONS, Logos)
└── templates/
    ├── base.html             # Bootstrap-5-Basis-Template mit Dark-Theme
    ├── page1_products.html   # Produktverwaltung (Liste, Suche, Lager-Filter)
    ├── page2_product_edit.html  # Produkt bearbeiten/erstellen (Multi-Lager)
    ├── page3_warehouse_list.html # Lagerliste
    ├── page4_statistics.html # Statistik-Dashboard
    └── page5_history.html    # Änderungen-/Historienseite

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

### 1. Contracts (`src/bierapp/contracts.py`)

Definiert vier abstrakte Ports (ABCs):

| Port | Zweck |
|---|---|
| `DatabasePort` | MongoDB-Operationen (CRUD + Suche) |
| `ProductServicePort` | Produkt-Geschäftslogik |
| `WarehouseServicePort` | Lager-Geschäftslogik |
| `InventoryServicePort` | Bestandsverwaltungs-Logik |

Alle anderen Schichten importieren nur diese Interfaces — nie konkrete Klassen.

### 2. DB-Adapter (`src/bierapp/db/`)

**`MongoDBAdapter`** implementiert `DatabasePort`:
- Verbindungsaufbau über Umgebungsvariablen (`MONGO_HOST`, `MONGO_PORT`, `MONGO_USER`, `MONGO_PASS`, `MONGO_DB`)
- Collections: `produkte`, `lager`, `inventar`, `events`
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

### 3. Service-Layer (`src/bierapp/backend/services.py`)

**`ProductService`** implementiert `ProductServicePort`:
- `create_product(name, beschreibung, gewicht)` – Validiert: nicht-leerer Name, Gewicht ≥ 0
- `get_product(id)` – per `find_by_id`
- `list_products()` – per `find_all`
- `update_product(id, felder)` – `KeyError` wenn nicht vorhanden
- `delete_product(id)` – `KeyError` wenn nicht vorhanden

**`WarehouseService`** implementiert `WarehouseServicePort`:
- `create_warehouse(lagername, adresse, max_plaetze)` – Validiert: nicht-leer, max_plaetze > 0
- `get_warehouse(id)` / `list_warehouses()` / `update_warehouse(id, felder)` / `delete_warehouse(id)`

**`InventoryService`** implementiert `InventoryServicePort`:
- `add_product(lager_id, produkt_id, menge)` – Bei vorhandenem Eintrag wird Menge addiert
- `update_quantity(lager_id, produkt_id, menge)` – `ValueError` bei negativer Menge
- `remove_product(lager_id, produkt_id)` – `KeyError` wenn kein Eintrag
- `list_inventory(lager_id)` – Reichert jeden Eintrag mit Produktname + Beschreibung an

### 4. Frontend (`src/bierapp/frontend/flask/gui.py`)

Flask-Anwendung mit Lazy-Singleton-Pattern für DB und Services:

```
python
_db: Optional[MongoDBAdapter] = None

def get_db() -> MongoDBAdapter:      # erstellt Verbindung bei Bedarf
def get_product_service() -> ProductService:
def get_warehouse_service() -> WarehouseService:
def get_inventory_service() -> InventoryService:
```

**Routen-Übersicht (Legacy):**

Die Legacy-Routen wurden so angepasst, dass sie intern die neuen Page-1–4-Templates
verwenden, aber nach außen kompatibel zu den bestehenden Tests bleiben.

| Methode | Route | Beschreibung |
|---|---|---|
| GET | `/` | Rendert Dashboard (Page 1 – Produktverwaltung) |
| GET | `/produkte` | Produktliste (nutzt Page 1 UI) |
| POST | `/produkte/neu` | Produkt erstellen |
| POST | `/produkte/<id>/bearbeiten` | Produkt aktualisieren |
| POST | `/produkte/<id>/loeschen` | Produkt löschen |
| GET | `/lager` | Lagerliste (nutzt Page 3 UI) |
| POST | `/lager/neu` | Lager erstellen |
| POST | `/lager/<id>/bearbeiten` | Lager aktualisieren |
| POST | `/lager/<id>/loeschen` | Lager löschen |
| GET | `/inventar` | Redirect zum ersten Lager (bei vorhandenen Lagern), sonst Dashboard |
| GET | `/inventar/<lager_id>` | Bestand eines Lagers (nutzt Statistik-Dashboard) |
| POST | `/inventar/<lager_id>/hinzufuegen` | Produkt einbuchen |
| POST | `/inventar/<lager_id>/<produkt_id>/aktualisieren` | Menge ändern |
| POST | `/inventar/<lager_id>/<produkt_id>/entfernen` | Produkt ausbuchen |
| GET | `/statistik` | Statistik (Legacy) |

**Routen-Übersicht (Neue UI – 4+1 Seiten):**

| Methode | Route | Beschreibung |
|---|---|---|
| GET | `/ui/produkte` | **Page 1** – Produktverwaltung (inkl. Lager-Filter) |
| GET | `/ui/produkt/neu` | **Page 2** – Neues Produkt erstellen |
| POST | `/ui/produkt/neu` | Produkt speichern (neu) inkl. Lagerzuordnungen |
| GET | `/ui/produkt/<id>/bearbeiten` | **Page 2** – Produkt bearbeiten |
| POST | `/ui/produkt/<id>/speichern` | Produkt speichern (Update; synchronisiert alle Lagerbestände) |
| POST | `/ui/produkt/<id>/verschieben` | Produktbestand von einem Lager in ein anderes verschieben |
| POST | `/ui/produkt/<id>/loeschen` | Produkt und zugehörige Bestände löschen |
| GET | `/ui/lager` | **Page 3** – Lagerliste |
| POST | `/ui/lager/neu` | Lager erstellen |
| POST | `/ui/lager/<id>/bearbeiten` | Lager aktualisieren |
| POST | `/ui/lager/<id>/loeschen` | Lager löschen (inkl. dazugehörigem Inventar) |
| GET | `/ui/statistik` | **Page 4** – Statistik-Dashboard |
| GET | `/ui/historie` | **Page 5** – Historie aller Änderungen (Events) |

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
| `page5_history.html` | 5 | Historie: Tabelle aller Events (Produkte, Lager, Inventar) |

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

**Letzte Aktualisierung:** 2026-02-25
**Version:** 1.1
