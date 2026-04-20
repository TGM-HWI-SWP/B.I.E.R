# Schnittstellen-Dokumentation (Contracts)

## Übersicht

Diese Datei dokumentiert alle abstrakten Ports des Projekts (`src/bierapp/contracts/`).
Jeder Port ist in einer eigenen Datei definiert; `contracts/__init__.py` re-exportiert alle für bequeme Imports.
Sie wird bei jeder Änderung aktualisiert.

---

## 1. DatabasePort

**Klasse:** `DatabasePort(ABC)`  
**Datei:** `contracts/database_port.py`  
**Schicht:** MongoDB-Adapter-Schicht

### Beschreibung
Abstrakte Schnittstelle für alle direkten MongoDB-Operationen. Jeder konkrete Datenbankadapter muss diese Methoden implementieren.

### Methoden

#### `connect() -> None`
Baut die Verbindung zur MongoDB-Instanz auf.

**Exceptions:**
- `ConnectionError`: Wenn die Verbindung nicht hergestellt werden kann.

---

#### `insert(collection: str, data: Dict) -> str`
Fügt ein Dokument in eine Collection ein.

**Parameter:**
- `collection (str)`: Name der Ziel-Collection.
- `data (Dict)`: Das einzufügende Dokument.

**Return:**
- `str`: ID des eingefügten Dokuments.

---

#### `find_by_id(collection: str, document_id: str) -> Optional[Dict]`
Ruft ein einzelnes Dokument anhand seiner ID ab.

**Parameter:**
- `collection (str)`: Name der Collection.
- `document_id (str)`: Eindeutiger Dokumentbezeichner.

**Return:**
- `Optional[Dict]`: Dokument wenn gefunden, sonst `None`.

---

#### `find_all(collection: str) -> List[Dict]`
Ruft alle Dokumente einer Collection ab.

**Parameter:**
- `collection (str)`: Name der Collection.

**Return:**
- `List[Dict]`: Liste aller Dokumente.

---

#### `update(collection: str, document_id: str, data: Dict) -> bool`
Aktualisiert ein Dokument in einer Collection.

**Parameter:**
- `collection (str)`: Name der Collection.
- `document_id (str)`: Dokumentbezeichner.
- `data (Dict)`: Zu aktualisierende Felder.

**Return:**
- `bool`: `True` wenn das Update erfolgreich war.

---

#### `delete(collection: str, document_id: str) -> bool`
Löscht ein Dokument aus einer Collection.

**Parameter:**
- `collection (str)`: Name der Collection.
- `document_id (str)`: Dokumentbezeichner.

**Return:**
- `bool`: `True` wenn das Löschen erfolgreich war.

---

## 2. ProductServicePort

**Klasse:** `ProductServicePort(ABC)`  
**Datei:** `contracts/product_port.py`  
**Schicht:** Service-Schicht (Businesslogik)

### Beschreibung
Abstrakte Schnittstelle für produktbezogene Geschäftslogik.

### Methoden

#### `create_product(name: str, description: str, weight: float) -> Dict`
Erstellt ein neues Produkt und persistiert es.

**Parameter:**
- `name (str)`: Lesbarer Produktname.
- `description (str)`: Kurzbeschreibung des Produkts.
- `weight (float)`: Gewicht des Produkts in Kilogramm.

**Return:**
- `Dict`: Repräsentation des neu erstellten Produkts.

**Exceptions:**
- `ValueError`: Wenn ein Argument die Domänenvalidierung nicht besteht.

---

#### `get_product(produkt_id: str) -> Optional[Dict]`
Ruft ein einzelnes Produkt anhand seiner ID ab.

**Parameter:**
- `produkt_id (str)`: Eindeutiger Produktbezeichner.

**Return:**
- `Optional[Dict]`: Produktdaten wenn gefunden, sonst `None`.

---

#### `list_products() -> List[Dict]`
Gibt alle bekannten Produkte zurück.

**Return:**
- `List[Dict]`: Liste aller Produktrepräsentationen.

---

#### `update_product(produkt_id: str, data: Dict) -> Dict`
Aktualisiert Felder eines bestehenden Produkts.

**Parameter:**
- `produkt_id (str)`: Eindeutiger Produktbezeichner.
- `data (Dict)`: Dictionary der zu aktualisierenden Felder.

**Return:**
- `Dict`: Aktualisierte Produktrepräsentation.

**Exceptions:**
- `KeyError`: Wenn kein Produkt mit der angegebenen ID existiert.
- `ValueError`: Wenn ein aktualisiertes Feld die Domänenvalidierung nicht besteht.

---

#### `delete_product(produkt_id: str) -> None`
Löscht ein Produkt dauerhaft.

**Parameter:**
- `produkt_id (str)`: Eindeutiger Produktbezeichner.

**Exceptions:**
- `KeyError`: Wenn kein Produkt mit der angegebenen ID existiert.

---

## 3. WarehouseServicePort

**Klasse:** `WarehouseServicePort(ABC)`  
**Datei:** `contracts/warehouse_port.py`  
**Schicht:** Service-Schicht (Businesslogik)

### Beschreibung
Abstrakte Schnittstelle für lagerbezogene Geschäftslogik.

### Methoden

#### `create_warehouse(warehouse_name: str, address: str, max_slots: int) -> Dict`
Erstellt ein neues Lager und persistiert es.

**Parameter:**
- `warehouse_name (str)`: Lesbarer Lagername.
- `address (str)`: Physische Adresse des Lagers.
- `max_slots (int)`: Maximale Anzahl an Lagerplätzen.

**Return:**
- `Dict`: Repräsentation des neu erstellten Lagers.

**Exceptions:**
- `ValueError`: Wenn `max_plaetze` keine positive ganze Zahl ist.

---

#### `get_warehouse(lager_id: str) -> Optional[Dict]`
Ruft ein einzelnes Lager anhand seiner ID ab.

**Parameter:**
- `lager_id (str)`: Eindeutiger Lagerbezeichner.

**Return:**
- `Optional[Dict]`: Lagerdaten wenn gefunden, sonst `None`.

---

#### `list_warehouses() -> List[Dict]`
Gibt alle bekannten Lager zurück.

**Return:**
- `List[Dict]`: Liste aller Lagerrepräsentationen.

---

#### `update_warehouse(lager_id: str, data: Dict) -> Dict`
Aktualisiert Felder eines bestehenden Lagers.

**Parameter:**
- `lager_id (str)`: Eindeutiger Lagerbezeichner.
- `data (Dict)`: Dictionary der zu aktualisierenden Felder.

**Return:**
- `Dict`: Aktualisierte Lagerrepräsentation.

**Exceptions:**
- `KeyError`: Wenn kein Lager mit der angegebenen ID existiert.
- `ValueError`: Wenn ein aktualisiertes Feld die Domänenvalidierung nicht besteht.

---

#### `delete_warehouse(lager_id: str) -> None`
Löscht ein Lager dauerhaft.

**Parameter:**
- `lager_id (str)`: Eindeutiger Lagerbezeichner.

**Exceptions:**
- `KeyError`: Wenn kein Lager mit der angegebenen ID existiert.

---

## 4. InventoryServicePort

**Klasse:** `InventoryServicePort(ABC)`  
**Datei:** `contracts/inventory_port.py`  
**Schicht:** Service-Schicht (Businesslogik)

### Beschreibung
Abstrakte Schnittstelle für die Verwaltung des Lagerbestands (welches Produkt liegt in welchem Lager mit welcher Menge).

### Methoden

#### `add_product(warehouse_id: str, product_id: str, quantity: int) -> None`
Fügt einen Produkteintrag zum Lagerbestand hinzu.

**Parameter:**
- `warehouse_id (str)`: Eindeutiger Lagerbezeichner.
- `product_id (str)`: Eindeutiger Produktbezeichner.
- `quantity (int)`: Anfängliche einzulagernde Menge.

**Exceptions:**
- `KeyError`: Wenn das Lager oder Produkt nicht existiert.
- `ValueError`: Wenn `quantity` keine positive ganze Zahl ist.

---

#### `update_quantity(warehouse_id: str, product_id: str, quantity: int) -> None`
Aktualisiert die gelagerte Menge eines Produkts in einem Lager.

**Parameter:**
- `warehouse_id (str)`: Eindeutiger Lagerbezeichner.
- `product_id (str)`: Eindeutiger Produktbezeichner.
- `quantity (int)`: Neuer absoluter Mengenwert.

**Exceptions:**
- `KeyError`: Wenn der Inventar-Eintrag nicht existiert.
- `ValueError`: Wenn `quantity` negativ ist.

---

#### `remove_product(warehouse_id: str, product_id: str) -> None`
Entfernt einen Produkteintrag vollständig aus dem Lagerbestand.

**Parameter:**
- `warehouse_id (str)`: Eindeutiger Lagerbezeichner.
- `product_id (str)`: Eindeutiger Produktbezeichner.

**Exceptions:**
- `KeyError`: Wenn der Eintrag nicht existiert.

---

#### `remove_stock(warehouse_id: str, product_id: str, quantity: int) -> None`
Reduziert die Menge eines Produkts in einem Lager. Löscht den Eintrag wenn Menge auf 0 fällt.

**Parameter:**
- `warehouse_id (str)`: Eindeutiger Lagerbezeichner.
- `product_id (str)`: Eindeutiger Produktbezeichner.
- `quantity (int)`: Zu entnehmende Menge (muss positiv sein und ≤ Lagerbestand).

**Exceptions:**
- `KeyError`: Wenn der Eintrag nicht existiert.
- `ValueError`: Wenn `quantity` ≤ 0 oder größer als der Bestand ist.

---

#### `move_product(source_warehouse_id: str, target_warehouse_id: str, product_id: str, quantity: int) -> None`
Verschiebt eine Menge von einem Quelllager in ein Ziellager.

**Parameter:**
- `source_warehouse_id (str)`: Quell-Lager.
- `target_warehouse_id (str)`: Ziel-Lager.
- `product_id (str)`: Eindeutiger Produktbezeichner.
- `quantity (int)`: Zu verschiebende Menge.

**Exceptions:**
- `KeyError`: Wenn ein Lager oder der Quell-Eintrag nicht existiert.
- `ValueError`: Wenn `quantity` ≤ 0 oder größer als der Quellbestand ist.

---

#### `get_total_inventory_value(warehouse_id: str) -> float`
Berechnet den Gesamtwert (Preis × Menge) aller Bestände eines Lagers.

**Parameter:**
- `warehouse_id (str)`: Eindeutiger Lagerbezeichner.

**Return:**
- `float`: Summe aller (Preis × Menge)-Werte für das Lager.

---

#### `list_inventory(warehouse_id: str) -> List[Dict]`
Listet alle im Lager eingelagerten Produkteinträge auf.

**Parameter:**
- `warehouse_id (str)`: Eindeutiger Lagerbezeichner.

**Return:**
- `List[Dict]`: Liste der Bestandseinträge, angereichert mit Produktname und -beschreibung.

**Exceptions:**
- `KeyError`: Wenn kein Lager mit der angegebenen ID existiert.

---

## 5. ReportPort

**Klasse:** `ReportPort(ABC)`  
**Datei:** `contracts/report_port.py`  
**Schicht:** Report-Schicht

### Beschreibung
Abstrakte Schnittstelle für die Report-Generierung.

### Methoden

#### `inventory_report(lager_id: str) -> List[Dict]`
Generiert einen Bestandsbericht für ein bestimmtes Lager.

**Parameter:**
- `lager_id (str)`: Eindeutiger Lagerbezeichner.

**Return:**
- `List[Dict]`: Geordnete Liste der Bestandseinträge inklusive Produktdetails und aktuellem Bestand.

**Exceptions:**
- `KeyError`: Wenn kein Lager mit der angegebenen ID existiert.

---

#### `statistics_report() -> Dict`
Generiert globale Statistiken über alle Lager und Produkte hinweg.

**Return:**
- `Dict`: Aggregierte Statistiken wie Gesamtprodukte, Gesamtlager, Gesamtlagereinheiten und Gesamtkapazitätsauslastung.

---

## 6. HttpResponsePort

**Klasse:** `HttpResponsePort(ABC)`  
**Datei:** `contracts/http_port.py`  
**Schicht:** Flask-Adapter (Frontend-Grenze)

### Beschreibung
Abstrakte Schnittstelle für die HTTP-Antwortverarbeitung im Flask-Adapter.

### Methoden

#### `success(data: Dict, status: int = 200) -> tuple[Dict, int]`
Erstellt eine erfolgreiche HTTP-JSON-Antwort.

**Parameter:**
- `data (Dict)`: Nutzdaten, die unter dem `data`-Schlüssel eingefügt werden.
- `status (int)`: HTTP-Statuscode. Standard: `200`.

**Return:**
- `tuple[Dict, int]`: Tupel aus JSON-serialisierbarem Antwortkörper und HTTP-Statuscode.

---

#### `error(message: str, status: int = 400) -> tuple[Dict, int]`
Erstellt eine Fehler-HTTP-JSON-Antwort.

**Parameter:**
- `message (str)`: Menschenlesbare Fehlerbeschreibung.
- `status (int)`: HTTP-Statuscode. Standard: `400`.

**Return:**
- `tuple[Dict, int]`: Tupel aus JSON-serialisierbarem Antwortkörper mit Fehlermeldung und HTTP-Statuscode.

---

## 7. Operative Datenverträge (Mongo-Dokumente)

Diese Dokumente sind keine Python-ABCs, aber stabile Verträge zwischen UI, Flask-Routen und MongoDB.

### `users` Collection

Verwendung: Login und User-Administration.

Pflichtfelder:
- `username: str` (eindeutig)
- `password_hash: str`
- `role: "manager" | "clerk"`
- `display_name: str`
- `active: bool`

Typische Metadaten:
- `created_at: str` (ISO UTC)
- `updated_at: str` (ISO UTC)

### `user_settings` Collection

Verwendung: Benutzerspezifische UI-Profile pro Rolle.

Pflichtfelder:
- `owner_username: str`
- `profile_role: "manager" | "clerk"`
- `settings: Dict`

Metadaten:
- `updated_at: str` (ISO UTC)

### `app_settings` Collection

Verwendung: Globale Rollen-Policies für UI-Settings.

Aktueller Key:
- `key: "role_policy"`
- `value.clerk_defaults: Dict`
- `value.clerk_locked_keys: List[str]`
- `updated_at: str` (ISO UTC)

### `events` Collection – User-Admin Audit Events

Zusätzlich zu Produkt/Lager/Inventar-Events existieren strukturierte Audit-Events:

- `entity_type: "user_admin"`
- `action: "create" | "update_role" | "update_status" | "reset_password"`
- `performed_by: str`
- `timestamp: str` (ISO UTC)
- `entity_id: str` (betroffener User)
- `summary: str`
- `details.target_username: str`
- `details.changes: Dict`

---

## Versionshistorie der Contracts

### v0.3.0 (2026-04-20)
- Operative Datenverträge ergänzt: `users`, `user_settings`, `app_settings`
- Audit-Event-Vertrag für `events` mit `entity_type = user_admin` dokumentiert

### v0.2.0 (2026-03-02)
- Contracts in eigenes Package `contracts/` aufgeteilt (eine Datei pro Port)
- `InventoryServicePort`: `remove_stock()`, `move_product()`, `get_total_inventory_value()` ergänzt
- Parameternamen englischsprachig vereinheitlicht (`warehouse_id`, `product_id`, `quantity` usw.)
- `contracts/__init__.py` re-exportiert alle Ports für nahtlose Rückwärtskompatibilität

### v0.1.1 (2026-02-25)
- `DatabasePort`: MongoDB CRUD-Operationen (connect, insert, find_by_id, find_all, update, delete)
- `ProductServicePort`: Produkt-Businesslogik (create, get, list, update, delete)
- `WarehouseServicePort`: Lager-Businesslogik (create, get, list, update, delete)
- `InventoryServicePort`: Bestandsverwaltung (add, update_quantity, remove, list)
- `ReportPort`: Report-Generierung (inventory_report, statistics_report)
- `HttpResponsePort`: Flask HTTP-Adapter (success, error)

---

**Letzte Aktualisierung:** 2026-04-20