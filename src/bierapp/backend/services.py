"""Concrete service implementations for B.I.E.R business logic.

Each service class implements the corresponding abstract port defined in
bierapp.contracts and delegates all persistence to a MongoDBAdapter
instance that must be injected at construction time.
"""

from datetime import datetime
from typing import Dict, List, Optional

from bierapp.contracts import InventoryServicePort, ProductServicePort, WarehouseServicePort
from bierapp.db.mongodb import (
    COLLECTION_EVENTS,
    COLLECTION_INVENTAR,
    COLLECTION_LAGER,
    COLLECTION_PRODUKTE,
    MongoDBAdapter,
)


def _now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format with 'Z' suffix."""
    return datetime.utcnow().isoformat() + "Z"


class ProductService(ProductServicePort):
    """Business logic for the produkte collection."""

    def __init__(self, db: MongoDBAdapter) -> None:
        """Initialise the service with an already-connected MongoDBAdapter.

        Args:
            db (MongoDBAdapter): Connected database adapter used for persistence.
        """
        self._db = db

    def create_product(self, name: str, beschreibung: str, gewicht: float, preis: float = 0.0) -> Dict:
        """Validate inputs and persist a new product document.

        Args:
            name (str): Human-readable product name. Must not be empty.
            beschreibung (str): Short description of the product.
            gewicht (float): Weight of the product in kilograms. Must be >= 0.
            preis (float): Unit price of the product. Must be >= 0. Defaults to 0.0.

        Returns:
            Dict: Representation of the newly created product including its _id.

        Raises:
            ValueError: If name is empty, gewicht is negative, or preis is negative.
        """
        name = name.strip()
        beschreibung = beschreibung.strip()
        if not name:
            raise ValueError("Produktname darf nicht leer sein.")
        if gewicht < 0:
            raise ValueError("Gewicht muss >= 0 sein.")
        if preis < 0:
            raise ValueError("Preis muss >= 0 sein.")

        doc = {"name": name, "beschreibung": beschreibung, "gewicht": float(gewicht), "preis": float(preis)}
        doc_id = self._db.insert(COLLECTION_PRODUKTE, doc)
        doc["_id"] = doc_id

        # Historien-Event: Produkt angelegt
        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "produkt",
                "action": "create",
                "entity_id": doc_id,
                "summary": f"Produkt '{name}' angelegt.",
            },
        )
        return doc

    def get_product(self, produkt_id: str) -> Optional[Dict]:
        """Retrieve a single product by its ID.

        Args:
            produkt_id (str): Unique product identifier.

        Returns:
            Optional[Dict]: Product data if found, otherwise None.
        """
        return self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id)

    def list_products(self) -> List[Dict]:
        """Return all products stored in the database.

        Returns:
            List[Dict]: List of all product documents.
        """
        return self._db.find_all(COLLECTION_PRODUKTE)

    def update_product(self, produkt_id: str, data: Dict) -> Dict:
        """Apply a partial update to an existing product.

        Args:
            produkt_id (str): Unique product identifier.
            data (Dict): Fields to update. Accepted keys: name, beschreibung, gewicht.

        Returns:
            Dict: Updated product document.

        Raises:
            KeyError: If no product with produkt_id exists.
            ValueError: If any updated field fails validation.
        """
        existing = self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id)
        if not existing:
            raise KeyError(f"Produkt '{produkt_id}' nicht gefunden.")

        allowed = {}
        if "name" in data:
            name = data["name"].strip()
            if not name:
                raise ValueError("Produktname darf nicht leer sein.")
            allowed["name"] = name
        if "beschreibung" in data:
            allowed["beschreibung"] = data["beschreibung"].strip()
        if "gewicht" in data:
            gewicht = float(data["gewicht"])
            if gewicht < 0:
                raise ValueError("Gewicht muss >= 0 sein.")
            allowed["gewicht"] = gewicht

        self._db.update(COLLECTION_PRODUKTE, produkt_id, allowed)
        updated = self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id) or {}

        # Historien-Event: Produkt aktualisiert
        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "produkt",
                "action": "update",
                "entity_id": produkt_id,
                "summary": f"Produkt '{updated.get('name', produkt_id)}' aktualisiert.",
            },
        )
        return updated

    def delete_product(self, produkt_id: str) -> None:
        """Permanently delete a product from the database.

        Args:
            produkt_id (str): Unique product identifier.

        Raises:
            KeyError: If no product with produkt_id exists.
        """
        existing = self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id)
        if not existing:
            raise KeyError(f"Produkt '{produkt_id}' nicht gefunden.")
        self._db.delete(COLLECTION_PRODUKTE, produkt_id)

        # Historien-Event: Produkt gelöscht
        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "produkt",
                "action": "delete",
                "entity_id": produkt_id,
                "summary": f"Produkt '{existing.get('name', produkt_id)}' gelöscht.",
            },
        )


class WarehouseService(WarehouseServicePort):
    """Business logic for the lager collection."""

    def __init__(self, db: MongoDBAdapter) -> None:
        """Initialise the service with an already-connected MongoDBAdapter.

        Args:
            db (MongoDBAdapter): Connected database adapter used for persistence.
        """
        self._db = db

    def create_warehouse(self, lagername: str, adresse: str, max_plaetze: int) -> Dict:
        """Validate inputs and persist a new warehouse document.

        Args:
            lagername (str): Human-readable warehouse name. Must not be empty.
            adresse (str): Physical address of the warehouse.
            max_plaetze (int): Maximum number of storage slots. Must be > 0.

        Returns:
            Dict: Representation of the newly created warehouse including its _id.

        Raises:
            ValueError: If lagername is empty or max_plaetze is not a positive integer.
        """
        lagername = lagername.strip()
        adresse = adresse.strip()
        if not lagername:
            raise ValueError("Lagername darf nicht leer sein.")
        if not isinstance(max_plaetze, int) or max_plaetze <= 0:
            raise ValueError("max_plaetze muss eine positive ganze Zahl sein.")

        doc = {"lagername": lagername, "adresse": adresse, "max_plaetze": max_plaetze}
        doc_id = self._db.insert(COLLECTION_LAGER, doc)
        doc["_id"] = doc_id

        # Historien-Event: Lager angelegt
        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "lager",
                "action": "create",
                "entity_id": doc_id,
                "summary": f"Lager '{lagername}' angelegt.",
            },
        )
        return doc

    def get_warehouse(self, lager_id: str) -> Optional[Dict]:
        """Retrieve a single warehouse by its ID.

        Args:
            lager_id (str): Unique warehouse identifier.

        Returns:
            Optional[Dict]: Warehouse data if found, otherwise None.
        """
        return self._db.find_by_id(COLLECTION_LAGER, lager_id)

    def list_warehouses(self) -> List[Dict]:
        """Return all warehouses stored in the database.

        Returns:
            List[Dict]: List of all warehouse documents.
        """
        return self._db.find_all(COLLECTION_LAGER)

    def update_warehouse(self, lager_id: str, data: Dict) -> Dict:
        """Apply a partial update to an existing warehouse.

        Args:
            lager_id (str): Unique warehouse identifier.
            data (Dict): Fields to update. Accepted keys: lagername, adresse, max_plaetze.

        Returns:
            Dict: Updated warehouse document.

        Raises:
            KeyError: If no warehouse with lager_id exists.
            ValueError: If any updated field fails validation.
        """
        existing = self._db.find_by_id(COLLECTION_LAGER, lager_id)
        if not existing:
            raise KeyError(f"Lager '{lager_id}' nicht gefunden.")

        allowed = {}
        if "lagername" in data:
            name = data["lagername"].strip()
            if not name:
                raise ValueError("Lagername darf nicht leer sein.")
            allowed["lagername"] = name
        if "adresse" in data:
            allowed["adresse"] = data["adresse"].strip()
        if "max_plaetze" in data:
            mp = int(data["max_plaetze"])
            if mp <= 0:
                raise ValueError("max_plaetze muss eine positive ganze Zahl sein.")
            # Count distinct products currently stored in this warehouse
            inventory_entries = self._db.find_inventar_by_lager(lager_id)
            current_product_count = len({e.get("produkt_id") for e in inventory_entries if e.get("produkt_id")})
            if mp < current_product_count:
                raise ValueError(
                    f"Maximale Plätze ({mp}) darf nicht kleiner sein als die Anzahl der "
                    f"bereits eingelagerten Produkte ({current_product_count})."
                )
            allowed["max_plaetze"] = mp

        self._db.update(COLLECTION_LAGER, lager_id, allowed)
        updated = self._db.find_by_id(COLLECTION_LAGER, lager_id) or {}

        # Historien-Event: Lager aktualisiert
        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "lager",
                "action": "update",
                "entity_id": lager_id,
                "summary": f"Lager '{updated.get('lagername', lager_id)}' aktualisiert.",
            },
        )
        return updated

    def delete_warehouse(self, lager_id: str) -> None:
        """Permanently delete a warehouse from the database.

        Args:
            lager_id (str): Unique warehouse identifier.

        Raises:
            KeyError: If no warehouse with lager_id exists.
        """
        existing = self._db.find_by_id(COLLECTION_LAGER, lager_id)
        if not existing:
            raise KeyError(f"Lager '{lager_id}' nicht gefunden.")
        self._db.delete(COLLECTION_LAGER, lager_id)

        # Historien-Event: Lager gelöscht
        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "lager",
                "action": "delete",
                "entity_id": lager_id,
                "summary": f"Lager '{existing.get('lagername', lager_id)}' gelöscht.",
            },
        )


class InventoryService(InventoryServicePort):
    """Business logic for the inventar junction collection."""

    def __init__(self, db: MongoDBAdapter) -> None:
        """Initialise the service with an already-connected MongoDBAdapter.

        Args:
            db (MongoDBAdapter): Connected database adapter used for persistence.
        """
        self._db = db

    def add_product(self, lager_id: str, produkt_id: str, menge: int, performed_by: str = "system") -> None:
        """Add a product to a warehouse inventory, merging quantities if it already exists.

        Args:
            lager_id (str): Unique warehouse identifier.
            produkt_id (str): Unique product identifier.
            menge (int): Quantity to add. Must be >= 0.
            performed_by (str): Name or identifier of the user performing the action.

        Raises:
            ValueError: If menge is negative or not an integer.
            KeyError: If lager_id or produkt_id do not exist in the database.
        """
        if not isinstance(menge, int) or menge < 0:
            raise ValueError("Menge muss eine nicht-negative ganze Zahl sein.")

        lager = self._db.find_by_id(COLLECTION_LAGER, lager_id)
        if not lager:
            raise KeyError(f"Lager '{lager_id}' nicht gefunden.")
        produkt = self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id)
        if not produkt:
            raise KeyError(f"Produkt '{produkt_id}' nicht gefunden.")

        existing = self._db.find_inventar_entry(lager_id, produkt_id)
        if existing:
            new_menge = existing.get("menge", 0) + menge
            self._db.update(COLLECTION_INVENTAR, existing["_id"], {"menge": new_menge})
        else:
            self._db.insert(
                COLLECTION_INVENTAR,
                {"lager_id": lager_id, "produkt_id": produkt_id, "menge": menge},
            )

        # Historien-Event: Bestand hinzugefügt/erhöht
        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "inventar",
                "action": "stock_add",
                "entity_id": f"{lager_id}:{produkt_id}",
                "performed_by": performed_by,
                "summary": f"Bestand: {menge}x '{produkt.get('name', produkt_id)}' zu Lager '{lager.get('lagername', lager_id)}' hinzugefügt.",
            },
        )

    def update_quantity(self, lager_id: str, produkt_id: str, menge: int, performed_by: str = "system") -> None:
        """Set the absolute stock quantity for a product in a warehouse.

        Args:
            lager_id (str): Unique warehouse identifier.
            produkt_id (str): Unique product identifier.
            menge (int): New absolute quantity. Must be >= 0.
            performed_by (str): Name or identifier of the user performing the action.

        Raises:
            ValueError: If menge is negative.
            KeyError: If no inventory entry exists for the given pair.
        """
        if menge < 0:
            raise ValueError("Menge darf nicht negativ sein.")
        entry = self._db.find_inventar_entry(lager_id, produkt_id)
        if not entry:
            raise KeyError(
                f"Kein Inventareintrag für Lager '{lager_id}' / Produkt '{produkt_id}'."
            )
        self._db.update(COLLECTION_INVENTAR, entry["_id"], {"menge": menge})

        # Historien-Event: Bestand gesetzt
        produkt = self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id) or {}
        lager = self._db.find_by_id(COLLECTION_LAGER, lager_id) or {}
        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "inventar",
                "action": "stock_update",
                "entity_id": f"{lager_id}:{produkt_id}",
                "performed_by": performed_by,
                "summary": f"Bestand von '{produkt.get('name', produkt_id)}' in Lager '{lager.get('lagername', lager_id)}' auf {menge} gesetzt.",
            },
        )

    def remove_product(self, lager_id: str, produkt_id: str, performed_by: str = "system") -> None:
        """Remove a product entry from a warehouse inventory.

        Args:
            lager_id (str): Unique warehouse identifier.
            produkt_id (str): Unique product identifier.
            performed_by (str): Name or identifier of the user performing the action.

        Raises:
            KeyError: If no inventory entry exists for the given pair.
        """
        entry = self._db.find_inventar_entry(lager_id, produkt_id)
        if not entry:
            raise KeyError(
                f"Kein Inventareintrag für Lager '{lager_id}' / Produkt '{produkt_id}'."
            )
        self._db.delete(COLLECTION_INVENTAR, entry["_id"])

        # Historien-Event: Bestandseintrag entfernt
        produkt = self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id) or {}
        lager = self._db.find_by_id(COLLECTION_LAGER, lager_id) or {}
        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "inventar",
                "action": "stock_remove",
                "entity_id": f"{lager_id}:{produkt_id}",
                "performed_by": performed_by,
                "summary": f"Bestandseintrag von '{produkt.get('name', produkt_id)}' in Lager '{lager.get('lagername', lager_id)}' entfernt.",
            },
        )

    def remove_stock(self, lager_id: str, produkt_id: str, menge: int, performed_by: str = "system") -> None:
        """Reduce the stocked quantity by a relative delta (OUT-Buchung).

        Unlike :meth:`update_quantity` which sets an absolute value, this method
        subtracts *menge* from the current stock level. If the resulting quantity
        would be negative a :exc:`ValueError` is raised.

        Args:
            lager_id (str): Unique warehouse identifier.
            produkt_id (str): Unique product identifier.
            menge (int): Number of units to remove. Must be > 0.
            performed_by (str): Name or identifier of the user performing the action.

        Raises:
            ValueError: If menge <= 0 or greater than the current stock level
                (Unzureichender Bestand).
            KeyError: If no inventory entry exists for the given pair.
        """
        if not isinstance(menge, int) or menge <= 0:
            raise ValueError("Menge zum Entnehmen muss eine positive ganze Zahl sein.")

        entry = self._db.find_inventar_entry(lager_id, produkt_id)
        if not entry:
            raise KeyError(
                f"Kein Inventareintrag für Lager '{lager_id}' / Produkt '{produkt_id}'."
            )
        current = int(entry.get("menge", 0))
        if menge > current:
            raise ValueError(
                f"Unzureichender Bestand. Verfügbar: {current}, Angefordert: {menge}."
            )

        new_menge = current - menge
        self._db.update(COLLECTION_INVENTAR, entry["_id"], {"menge": new_menge})

        produkt = self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id) or {}
        lager = self._db.find_by_id(COLLECTION_LAGER, lager_id) or {}
        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "inventar",
                "action": "stock_out",
                "entity_id": f"{lager_id}:{produkt_id}",
                "performed_by": performed_by,
                "summary": (
                    f"{menge}x '{produkt.get('name', produkt_id)}' aus Lager "
                    f"'{lager.get('lagername', lager_id)}' entnommen "
                    f"(Restbestand: {new_menge})."
                ),
            },
        )

    def get_total_inventory_value(self) -> float:
        """Calculate the total monetary value of all stocked products across all warehouses.

        For each inventory entry, looks up the product's ``preis`` field and
        multiplies it by the stocked ``menge``. Products without a ``preis``
        field contribute 0.0 to the total.

        Returns:
            float: Sum of (preis × menge) for every inventory entry.
        """
        inventar = self._db.find_all(COLLECTION_INVENTAR)
        total = 0.0
        for entry in inventar:
            produkt_id = entry.get("produkt_id", "")
            menge = int(entry.get("menge", 0))
            produkt = self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id) or {}
            preis = float(produkt.get("preis", 0.0))
            total += preis * menge
        return total

    def move_product(self, source_lager_id: str, target_lager_id: str, produkt_id: str, menge: int) -> None:
        """Move a quantity of a product from one warehouse to another.

        Args:
            source_lager_id (str): ID of the warehouse to move stock from.
            target_lager_id (str): ID of the destination warehouse.
            produkt_id (str): Product identifier.
            menge (int): Quantity to move. Must be > 0.

        Raises:
            ValueError: If menge <= 0 or greater than available stock.
            KeyError: If source entry does not exist or warehouses/products invalid.
        """
        if not isinstance(menge, int) or menge <= 0:
            raise ValueError("Menge zum Verschieben muss eine positive ganze Zahl sein.")

        # Ensure both warehouses and product exist
        source = self._db.find_by_id(COLLECTION_LAGER, source_lager_id)
        target = self._db.find_by_id(COLLECTION_LAGER, target_lager_id)
        produkt = self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id)
        if not source:
            raise KeyError(f"Quelllager '{source_lager_id}' nicht gefunden.")
        if not target:
            raise KeyError(f"Ziellager '{target_lager_id}' nicht gefunden.")
        if not produkt:
            raise KeyError(f"Produkt '{produkt_id}' nicht gefunden.")

        entry = self._db.find_inventar_entry(source_lager_id, produkt_id)
        if not entry:
            raise KeyError(
                f"Kein Inventareintrag für Lager '{source_lager_id}' / Produkt '{produkt_id}'."
            )
        current = int(entry.get("menge", 0))
        if menge > current:
            raise ValueError("Es können nicht mehr Einheiten verschoben werden als vorhanden sind.")

        # Decrease in source
        remaining = current - menge
        if remaining > 0:
            self._db.update(COLLECTION_INVENTAR, entry["_id"], {"menge": remaining})
        else:
            self._db.delete(COLLECTION_INVENTAR, entry["_id"])

        # Increase or create in target
        target_entry = self._db.find_inventar_entry(target_lager_id, produkt_id)
        if target_entry:
            new_menge = int(target_entry.get("menge", 0)) + menge
            self._db.update(COLLECTION_INVENTAR, target_entry["_id"], {"menge": new_menge})
        else:
            self._db.insert(
                COLLECTION_INVENTAR,
                {"lager_id": target_lager_id, "produkt_id": produkt_id, "menge": menge},
            )

        # Historien-Event: Bestand verschoben
        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "inventar",
                "action": "stock_move",
                "entity_id": produkt_id,
                "performed_by": "system",
                "summary": (
                    f"{menge}x '{produkt.get('name', produkt_id)}' von Lager "
                    f"'{source.get('lagername', source_lager_id)}' nach "
                    f"'{target.get('lagername', target_lager_id)}' verschoben."
                ),
            },
        )

    def list_inventory(self, lager_id: str) -> List[Dict]:
        """List all inventory entries for a warehouse, enriched with product details.

        Args:
            lager_id (str): Unique warehouse identifier.

        Returns:
            List[Dict]: Inventory entries each containing _id, lager_id, produkt_id,
                produkt_name, produkt_beschreibung and menge.

        Raises:
            KeyError: If no warehouse with lager_id exists.
        """
        lager = self._db.find_by_id(COLLECTION_LAGER, lager_id)
        if not lager:
            raise KeyError(f"Lager '{lager_id}' nicht gefunden.")
        entries = self._db.find_inventar_by_lager(lager_id)
        result = []
        for e in entries:
            produkt = self._db.find_by_id(COLLECTION_PRODUKTE, e.get("produkt_id", ""))
            result.append(
                {
                    "_id": e.get("_id", ""),
                    "lager_id": lager_id,
                    "produkt_id": e.get("produkt_id", ""),
                    "produkt_name": produkt.get("name", "?") if produkt else "?",
                    "produkt_beschreibung": produkt.get("beschreibung", "") if produkt else "",
                    "menge": e.get("menge", 0),
                }
            )
        return result
