# Architektur-Dokumentation

## Übersicht

B.I.E.R folgt der **Hexagonalen Architektur** (Ports & Adapters). Jede Schicht kommuniziert ausschließlich über abstrakte Schnittstellen (`contracts.py`), was Testbarkeit, Austauschbarkeit und klare Verantwortlichkeiten garantiert.

---

## Schichten-Modell

```
┌──────────────────────────────────────────────────────────────┐
│                  Frontend (Flask / Jinja2)                   │
│   gui.py  ·  layout.html  ·  produkte / lager / inventar    │
└─────────────────────────┬────────────────────────────────────┘
                          │  ruft auf
┌─────────────────────────▼────────────────────────────────────┐
│                  Backend (Service-Layer)                      │
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
├── pictures/                 # Statische Bilddateien
└── templates/
    ├── layout.html           # Bootstrap-5-Basis-Template
    ├── index.html            # Dashboard
    ├── produkte.html         # Produktverwaltung (CRUD)
    ├── lager.html            # Lagerverwaltung (CRUD)
    └── inventar.html         # Bestandsverwaltung

tests/
├── conftest.py               # Shared Fixtures (mock_db, Services, Flask-Client)
├── unit/
│   └── test_domain.py        # Unit-Tests für alle Services (26 Tests)
└── integration/
    ├── test_flask.py         # Flask-Routen via Test-Client (19 Tests)
    ├── test_integration.py   # Service-Interaktionstests (5 Tests)
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
- Collections: `produkte`, `lager`, `inventar`
- Spezialabfragen: `find_inventar_by_lager()`, `find_inventar_entry()`
- Kontext-Manager-Support (`__enter__` / `__exit__`)
- `_serialize()` konvertiert BSON `ObjectId` → `str`

**`db/init/setup.py`** – idempotentes Setup-Script:
- Erstellt Collections und Indizes beim ersten Start
- `produkte`: Index auf `name`
- `lager`: Unique Index auf `lagername`
- `inventar`: Compound Unique Index auf `(lager_id, produkt_id)`
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

```python
_db: Optional[MongoDBAdapter] = None

def get_db() -> MongoDBAdapter:      # erstellt Verbindung bei Bedarf
def get_product_service() -> ProductService:
def get_warehouse_service() -> WarehouseService:
def get_inventory_service() -> InventoryService:
```

**Routen-Übersicht:**

| Methode | Route | Beschreibung |
|---|---|---|
| GET | `/` | Dashboard (Statistik-Karten, Lagerliste) |
| GET | `/produkte` | Produktliste |
| POST | `/produkte/neu` | Produkt erstellen |
| POST | `/produkte/<id>/bearbeiten` | Produkt aktualisieren |
| POST | `/produkte/<id>/loeschen` | Produkt löschen |
| GET | `/lager` | Lagerliste |
| POST | `/lager/neu` | Lager erstellen |
| POST | `/lager/<id>/bearbeiten` | Lager aktualisieren |
| POST | `/lager/<id>/loeschen` | Lager löschen |
| GET | `/inventar` | Redirect zum ersten Lager |
| GET | `/inventar/<lager_id>` | Bestand eines Lagers |
| POST | `/inventar/<lager_id>/hinzufuegen` | Produkt einbuchen |
| POST | `/inventar/<lager_id>/<produkt_id>/aktualisieren` | Menge ändern |
| POST | `/inventar/<lager_id>/<produkt_id>/entfernen` | Produkt ausbuchen |

### 5. Templates (`src/resources/templates/`)

Alle Templates erben von `layout.html` (Bootstrap 5.3, Bootstrap Icons 1.11, Amber/Dark Theme).

| Template | Inhalt |
|---|---|
| `layout.html` | Navbar, Flash-Messages, Block-Struktur |
| `index.html` | Stat-Karten (Produkte, Lager, Gesamtmenge), Lagertabelle |
| `produkte.html` | Produkttabelle + Bootstrap-Modal (Erstellen / Bearbeiten / Löschen) |
| `lager.html` | Lagertabelle + Bootstrap-Modal |
| `inventar.html` | Sidebar (Lagerliste) + Bestandstabelle + Produkt-Hinzufügen-Modal |

---

## Datenfluss (Beispiel: Produkt erstellen)

```
1. Nutzer füllt Formular auf /produkte aus und klickt "Speichern"
2. Browser sendet POST /produkte/neu
3. gui.py: produkte_create() liest request.form
4. get_product_service() gibt ProductService(get_db()) zurück
5. ProductService.create_product() validiert Eingaben
6. MongoDBAdapter.insert("produkte", doc) schreibt in MongoDB
7. Redirect auf GET /produkte → Flash-Message "Erfolgreich"
```

---

## Dependency Injection

Services erhalten den DB-Adapter über den Konstruktor:

```python
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
**Version:** 1.0
