# Schnittstellen-Dokumentation (Contracts)

## Übersicht

Diese Datei dokumentiert alle abstrakten Ports des Projekts (`src/bierapp/contracts.py`).
Sie wird von Rolle 1 (Contract Owner) gepflegt und bei jeder Änderung aktualisiert.

---

## 1. DatabasePort

**Klasse:** `DatabasePort(ABC)`  
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
**Schicht:** Service-Schicht (Businesslogik)

### Beschreibung
Abstrakte Schnittstelle für produktbezogene Geschäftslogik.

### Methoden

#### `create_product(name: str, beschreibung: str, gewicht: float) -> Dict`
Erstellt ein neues Produkt und persistiert es.

**Parameter:**
- `name (str)`: Lesbarer Produktname.
- `beschreibung (str)`: Kurzbeschreibung des Produkts.
- `gewicht (float)`: Gewicht des Produkts in Kilogramm.

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
**Schicht:** Service-Schicht (Businesslogik)

### Beschreibung
Abstrakte Schnittstelle für lagerbezogene Geschäftslogik.

### Methoden

#### `create_warehouse(lagername: str, adresse: str, max_plaetze: int) -> Dict`
Erstellt ein neues Lager und persistiert es.

**Parameter:**
- `lagername (str)`: Lesbarer Lagername.
- `adresse (str)`: Physische Adresse des Lagers.
- `max_plaetze (int)`: Maximale Anzahl an Lagerplätzen.

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
**Schicht:** Service-Schicht (Businesslogik)

### Beschreibung
Abstrakte Schnittstelle für die Verwaltung des Lagerbestands (welches Produkt liegt in welchem Lager mit welcher Menge).

### Methoden

#### `add_product(lager_id: str, produkt_id: str, menge: int) -> None`
Fügt einen Produkteintrag zum Lagerbestand hinzu.

**Parameter:**
- `lager_id (str)`: Eindeutiger Lagerbezeichner.
- `produkt_id (str)`: Eindeutiger Produktbezeichner.
- `menge (int)`: Anfängliche einzulagernde Menge.

**Exceptions:**
- `KeyError`: Wenn das Lager oder Produkt nicht existiert.
- `ValueError`: Wenn `menge` keine positive ganze Zahl ist.

---

#### `update_quantity(lager_id: str, produkt_id: str, menge: int) -> None`
Aktualisiert die gelagerte Menge eines Produkts in einem Lager.

**Parameter:**
- `lager_id (str)`: Eindeutiger Lagerbezeichner.
- `produkt_id (str)`: Eindeutiger Produktbezeichner.
- `menge (int)`: Neuer absoluter Mengenwert.

**Exceptions:**
- `KeyError`: Wenn das Lager oder der Produkteintrag nicht existiert.
- `ValueError`: Wenn `menge` negativ ist.

---

#### `remove_product(lager_id: str, produkt_id: str) -> None`
Entfernt einen Produkteintrag aus dem Lagerbestand.

**Parameter:**
- `lager_id (str)`: Eindeutiger Lagerbezeichner.
- `produkt_id (str)`: Eindeutiger Produktbezeichner.

**Exceptions:**
- `KeyError`: Wenn das Lager oder der Produkteintrag nicht existiert.

---

#### `list_inventory(lager_id: str) -> List[Dict]`
Listet alle im Lager eingelagerten Produkteinträge auf.

**Parameter:**
- `lager_id (str)`: Eindeutiger Lagerbezeichner.

**Return:**
- `List[Dict]`: Liste der Bestandseinträge, jeweils mit `produkt_id` und `menge`.

**Exceptions:**
- `KeyError`: Wenn kein Lager mit der angegebenen ID existiert.

---

## 5. ReportPort

**Klasse:** `ReportPort(ABC)`  
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

## Versionshistorie der Contracts

### v0.1.1 (2026-02-25)
- `DatabasePort`: MongoDB CRUD-Operationen (connect, insert, find_by_id, find_all, update, delete)
- `ProductServicePort`: Produkt-Businesslogik (create, get, list, update, delete)
- `WarehouseServicePort`: Lager-Businesslogik (create, get, list, update, delete)
- `InventoryServicePort`: Bestandsverwaltung (add, update_quantity, remove, list)
- `ReportPort`: Report-Generierung (inventory_report, statistics_report)
- `HttpResponsePort`: Flask HTTP-Adapter (success, error)