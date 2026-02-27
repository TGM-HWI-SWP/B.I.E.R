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

    def create_product(self, name: str, description: str, weight: float, price: float = 0.0) -> Dict:
        """Validate inputs and persist a new product document.

        Args:
            name (str): Human-readable product name. Must not be empty.
            description (str): Short description of the product.
            weight (float): Weight of the product in kilograms. Must be >= 0.
            price (float): Unit price of the product. Must be >= 0. Defaults to 0.0.

        Returns:
            Dict: Representation of the newly created product including its _id.

        Raises:
            ValueError: If name is empty, weight is negative, or price is negative.
        """
        name = name.strip()
        description = description.strip()
        if not name:
            raise ValueError("Produktname darf nicht leer sein.")
        if weight < 0:
            raise ValueError("Gewicht muss >= 0 sein.")
        if price < 0:
            raise ValueError("Preis muss >= 0 sein.")

        doc = {"name": name, "beschreibung": description, "gewicht": float(weight), "preis": float(price)}
        doc_id = self._db.insert(COLLECTION_PRODUKTE, doc)
        doc["_id"] = doc_id

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

    def get_product(self, product_id: str) -> Optional[Dict]:
        """Retrieve a single product by its ID.

        Args:
            product_id (str): Unique product identifier.

        Returns:
            Optional[Dict]: Product data if found, otherwise None.
        """
        return self._db.find_by_id(COLLECTION_PRODUKTE, product_id)

    def list_products(self) -> List[Dict]:
        """Return all products stored in the database.

        Returns:
            List[Dict]: List of all product documents.
        """
        return self._db.find_all(COLLECTION_PRODUKTE)

    def update_product(self, product_id: str, data: Dict) -> Dict:
        """Apply a partial update to an existing product.

        Args:
            product_id (str): Unique product identifier.
            data (Dict): Fields to update. Accepted keys: name, beschreibung, gewicht.

        Returns:
            Dict: Updated product document.

        Raises:
            KeyError: If no product with product_id exists.
            ValueError: If any updated field fails validation.
        """
        existing = self._db.find_by_id(COLLECTION_PRODUKTE, product_id)
        if not existing:
            raise KeyError(f"Produkt '{product_id}' nicht gefunden.")

        allowed = {}
        if "name" in data:
            name = data["name"].strip()
            if not name:
                raise ValueError("Produktname darf nicht leer sein.")
            allowed["name"] = name
        if "beschreibung" in data:
            allowed["beschreibung"] = data["beschreibung"].strip()
        if "gewicht" in data:
            weight = float(data["gewicht"])
            if weight < 0:
                raise ValueError("Gewicht muss >= 0 sein.")
            allowed["gewicht"] = weight

        self._db.update(COLLECTION_PRODUKTE, product_id, allowed)
        updated = self._db.find_by_id(COLLECTION_PRODUKTE, product_id) or {}

        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "produkt",
                "action": "update",
                "entity_id": product_id,
                "summary": f"Produkt '{updated.get('name', product_id)}' aktualisiert.",
            },
        )
        return updated

    def delete_product(self, product_id: str) -> None:
        """Permanently delete a product from the database.

        Args:
            product_id (str): Unique product identifier.

        Raises:
            KeyError: If no product with product_id exists.
        """
        existing = self._db.find_by_id(COLLECTION_PRODUKTE, product_id)
        if not existing:
            raise KeyError(f"Produkt '{product_id}' nicht gefunden.")
        self._db.delete(COLLECTION_PRODUKTE, product_id)

        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "produkt",
                "action": "delete",
                "entity_id": product_id,
                "summary": f"Produkt '{existing.get('name', product_id)}' gelöscht.",
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

    def create_warehouse(self, warehouse_name: str, address: str, max_slots: int) -> Dict:
        """Validate inputs and persist a new warehouse document.

        Args:
            warehouse_name (str): Human-readable warehouse name. Must not be empty.
            address (str): Physical address of the warehouse.
            max_slots (int): Maximum number of storage slots. Must be > 0.

        Returns:
            Dict: Representation of the newly created warehouse including its _id.

        Raises:
            ValueError: If warehouse_name is empty or max_slots is not a positive integer.
        """
        warehouse_name = warehouse_name.strip()
        address = address.strip()
        if not warehouse_name:
            raise ValueError("Lagername darf nicht leer sein.")
        if not isinstance(max_slots, int) or max_slots <= 0:
            raise ValueError("max_plaetze muss eine positive ganze Zahl sein.")

        doc = {"lagername": warehouse_name, "adresse": address, "max_plaetze": max_slots}
        doc_id = self._db.insert(COLLECTION_LAGER, doc)
        doc["_id"] = doc_id

        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "lager",
                "action": "create",
                "entity_id": doc_id,
                "summary": f"Lager '{warehouse_name}' angelegt.",
            },
        )
        return doc

    def get_warehouse(self, warehouse_id: str) -> Optional[Dict]:
        """Retrieve a single warehouse by its ID.

        Args:
            warehouse_id (str): Unique warehouse identifier.

        Returns:
            Optional[Dict]: Warehouse data if found, otherwise None.
        """
        return self._db.find_by_id(COLLECTION_LAGER, warehouse_id)

    def list_warehouses(self) -> List[Dict]:
        """Return all warehouses stored in the database.

        Returns:
            List[Dict]: List of all warehouse documents.
        """
        return self._db.find_all(COLLECTION_LAGER)

    def update_warehouse(self, warehouse_id: str, data: Dict) -> Dict:
        """Apply a partial update to an existing warehouse.

        Args:
            warehouse_id (str): Unique warehouse identifier.
            data (Dict): Fields to update. Accepted keys: lagername, adresse, max_plaetze.

        Returns:
            Dict: Updated warehouse document.

        Raises:
            KeyError: If no warehouse with warehouse_id exists.
            ValueError: If any updated field fails validation.
        """
        existing = self._db.find_by_id(COLLECTION_LAGER, warehouse_id)
        if not existing:
            raise KeyError(f"Lager '{warehouse_id}' nicht gefunden.")

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
            inventory_entries = self._db.find_inventory_by_warehouse(warehouse_id)
            current_product_count = len({e.get("produkt_id") for e in inventory_entries if e.get("produkt_id")})
            if mp < current_product_count:
                raise ValueError(
                    f"Maximale Plätze ({mp}) darf nicht kleiner sein als die Anzahl der "
                    f"bereits eingelagerten Produkte ({current_product_count})."
                )
            allowed["max_plaetze"] = mp

        self._db.update(COLLECTION_LAGER, warehouse_id, allowed)
        updated = self._db.find_by_id(COLLECTION_LAGER, warehouse_id) or {}

        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "lager",
                "action": "update",
                "entity_id": warehouse_id,
                "summary": f"Lager '{updated.get('lagername', warehouse_id)}' aktualisiert.",
            },
        )
        return updated

    def delete_warehouse(self, warehouse_id: str) -> None:
        """Permanently delete a warehouse from the database.

        Args:
            warehouse_id (str): Unique warehouse identifier.

        Raises:
            KeyError: If no warehouse with warehouse_id exists.
        """
        existing = self._db.find_by_id(COLLECTION_LAGER, warehouse_id)
        if not existing:
            raise KeyError(f"Lager '{warehouse_id}' nicht gefunden.")
        self._db.delete(COLLECTION_LAGER, warehouse_id)

        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "lager",
                "action": "delete",
                "entity_id": warehouse_id,
                "summary": f"Lager '{existing.get('lagername', warehouse_id)}' gelöscht.",
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

    def add_product(self, warehouse_id: str, product_id: str, quantity: int, performed_by: str = "system") -> None:
        """Add a product to a warehouse inventory, merging quantities if it already exists.

        Args:
            warehouse_id (str): Unique warehouse identifier.
            product_id (str): Unique product identifier.
            quantity (int): Quantity to add. Must be >= 0.
            performed_by (str): Name or identifier of the user performing the action.

        Raises:
            ValueError: If quantity is negative or not an integer.
            KeyError: If warehouse_id or product_id do not exist in the database.
        """
        if not isinstance(quantity, int) or quantity < 0:
            raise ValueError("Menge muss eine nicht-negative ganze Zahl sein.")

        warehouse = self._db.find_by_id(COLLECTION_LAGER, warehouse_id)
        if not warehouse:
            raise KeyError(f"Lager '{warehouse_id}' nicht gefunden.")
        product = self._db.find_by_id(COLLECTION_PRODUKTE, product_id)
        if not product:
            raise KeyError(f"Produkt '{product_id}' nicht gefunden.")

        existing = self._db.find_inventory_entry(warehouse_id, product_id)
        if existing:
            new_quantity = existing.get("menge", 0) + quantity
            self._db.update(COLLECTION_INVENTAR, existing["_id"], {"menge": new_quantity})
        else:
            self._db.insert(
                COLLECTION_INVENTAR,
                {"lager_id": warehouse_id, "produkt_id": product_id, "menge": quantity},
            )

        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "inventar",
                "action": "stock_add",
                "entity_id": f"{warehouse_id}:{product_id}",
                "performed_by": performed_by,
                "summary": f"Bestand: {quantity}x '{product.get('name', product_id)}' zu Lager '{warehouse.get('lagername', warehouse_id)}' hinzugefügt.",
            },
        )

    def update_quantity(self, warehouse_id: str, product_id: str, quantity: int, performed_by: str = "system") -> None:
        """Set the absolute stock quantity for a product in a warehouse.

        Args:
            warehouse_id (str): Unique warehouse identifier.
            product_id (str): Unique product identifier.
            quantity (int): New absolute quantity. Must be >= 0.
            performed_by (str): Name or identifier of the user performing the action.

        Raises:
            ValueError: If quantity is negative.
            KeyError: If no inventory entry exists for the given pair.
        """
        if quantity < 0:
            raise ValueError("Menge darf nicht negativ sein.")
        entry = self._db.find_inventory_entry(warehouse_id, product_id)
        if not entry:
            raise KeyError(
                f"Kein Inventareintrag für Lager '{warehouse_id}' / Produkt '{product_id}'."
            )
        self._db.update(COLLECTION_INVENTAR, entry["_id"], {"menge": quantity})

        product = self._db.find_by_id(COLLECTION_PRODUKTE, product_id) or {}
        warehouse = self._db.find_by_id(COLLECTION_LAGER, warehouse_id) or {}
        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "inventar",
                "action": "stock_update",
                "entity_id": f"{warehouse_id}:{product_id}",
                "performed_by": performed_by,
                "summary": f"Bestand von '{product.get('name', product_id)}' in Lager '{warehouse.get('lagername', warehouse_id)}' auf {quantity} gesetzt.",
            },
        )

    def remove_product(self, warehouse_id: str, product_id: str, performed_by: str = "system") -> None:
        """Remove a product entry from a warehouse inventory.

        Args:
            warehouse_id (str): Unique warehouse identifier.
            product_id (str): Unique product identifier.
            performed_by (str): Name or identifier of the user performing the action.

        Raises:
            KeyError: If no inventory entry exists for the given pair.
        """
        entry = self._db.find_inventory_entry(warehouse_id, product_id)
        if not entry:
            raise KeyError(
                f"Kein Inventareintrag für Lager '{warehouse_id}' / Produkt '{product_id}'."
            )
        self._db.delete(COLLECTION_INVENTAR, entry["_id"])

        product = self._db.find_by_id(COLLECTION_PRODUKTE, product_id) or {}
        warehouse = self._db.find_by_id(COLLECTION_LAGER, warehouse_id) or {}
        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "inventar",
                "action": "stock_remove",
                "entity_id": f"{warehouse_id}:{product_id}",
                "performed_by": performed_by,
                "summary": f"Bestandseintrag von '{product.get('name', product_id)}' in Lager '{warehouse.get('lagername', warehouse_id)}' entfernt.",
            },
        )

    def remove_stock(self, warehouse_id: str, product_id: str, quantity: int, performed_by: str = "system") -> None:
        """Reduce the stocked quantity by a relative delta (OUT-Buchung).

        Unlike :meth:`update_quantity` which sets an absolute value, this method
        subtracts *quantity* from the current stock level. If the resulting quantity
        would be negative a :exc:`ValueError` is raised.

        Args:
            warehouse_id (str): Unique warehouse identifier.
            product_id (str): Unique product identifier.
            quantity (int): Number of units to remove. Must be > 0.
            performed_by (str): Name or identifier of the user performing the action.

        Raises:
            ValueError: If quantity <= 0 or greater than the current stock level
                (Unzureichender Bestand).
            KeyError: If no inventory entry exists for the given pair.
        """
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Menge zum Entnehmen muss eine positive ganze Zahl sein.")

        entry = self._db.find_inventory_entry(warehouse_id, product_id)
        if not entry:
            raise KeyError(
                f"Kein Inventareintrag für Lager '{warehouse_id}' / Produkt '{product_id}'."
            )
        current = int(entry.get("menge", 0))
        if quantity > current:
            raise ValueError(
                f"Unzureichender Bestand. Verfügbar: {current}, Angefordert: {quantity}."
            )

        remaining_quantity = current - quantity
        self._db.update(COLLECTION_INVENTAR, entry["_id"], {"menge": remaining_quantity})

        product = self._db.find_by_id(COLLECTION_PRODUKTE, product_id) or {}
        warehouse = self._db.find_by_id(COLLECTION_LAGER, warehouse_id) or {}
        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "inventar",
                "action": "stock_out",
                "entity_id": f"{warehouse_id}:{product_id}",
                "performed_by": performed_by,
                "summary": (
                    f"{quantity}x '{product.get('name', product_id)}' aus Lager "
                    f"'{warehouse.get('lagername', warehouse_id)}' entnommen "
                    f"(Restbestand: {remaining_quantity})."
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
        inventory = self._db.find_all(COLLECTION_INVENTAR)
        total = 0.0
        for entry in inventory:
            product_id = entry.get("produkt_id", "")
            quantity = int(entry.get("menge", 0))
            product = self._db.find_by_id(COLLECTION_PRODUKTE, product_id) or {}
            price = float(product.get("preis", 0.0))
            total += price * quantity
        return total

    def move_product(self, source_warehouse_id: str, target_warehouse_id: str, product_id: str, quantity: int) -> None:
        """Move a quantity of a product from one warehouse to another.

        Args:
            source_warehouse_id (str): ID of the warehouse to move stock from.
            target_warehouse_id (str): ID of the destination warehouse.
            product_id (str): Product identifier.
            quantity (int): Quantity to move. Must be > 0.

        Raises:
            ValueError: If quantity <= 0 or greater than available stock.
            KeyError: If source entry does not exist or warehouses/products invalid.
        """
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Menge zum Verschieben muss eine positive ganze Zahl sein.")

        # Ensure both warehouses and product exist
        source_warehouse = self._db.find_by_id(COLLECTION_LAGER, source_warehouse_id)
        target_warehouse = self._db.find_by_id(COLLECTION_LAGER, target_warehouse_id)
        product = self._db.find_by_id(COLLECTION_PRODUKTE, product_id)
        if not source_warehouse:
            raise KeyError(f"Quelllager '{source_warehouse_id}' nicht gefunden.")
        if not target_warehouse:
            raise KeyError(f"Ziellager '{target_warehouse_id}' nicht gefunden.")
        if not product:
            raise KeyError(f"Produkt '{product_id}' nicht gefunden.")

        entry = self._db.find_inventory_entry(source_warehouse_id, product_id)
        if not entry:
            raise KeyError(
                f"Kein Inventareintrag für Lager '{source_warehouse_id}' / Produkt '{product_id}'."
            )
        current = int(entry.get("menge", 0))
        if quantity > current:
            raise ValueError("Es können nicht mehr Einheiten verschoben werden als vorhanden sind.")

        # Decrease in source
        remaining = current - quantity
        if remaining > 0:
            self._db.update(COLLECTION_INVENTAR, entry["_id"], {"menge": remaining})
        else:
            self._db.delete(COLLECTION_INVENTAR, entry["_id"])

        # Increase or create in target
        target_entry = self._db.find_inventory_entry(target_warehouse_id, product_id)
        if target_entry:
            new_quantity = int(target_entry.get("menge", 0)) + quantity
            self._db.update(COLLECTION_INVENTAR, target_entry["_id"], {"menge": new_quantity})
        else:
            self._db.insert(
                COLLECTION_INVENTAR,
                {"lager_id": target_warehouse_id, "produkt_id": product_id, "menge": quantity},
            )

        self._db.insert(
            COLLECTION_EVENTS,
            {
                "timestamp": _now_iso(),
                "entity_type": "inventar",
                "action": "stock_move",
                "entity_id": product_id,
                "performed_by": "system",
                "summary": (
                    f"{quantity}x '{product.get('name', product_id)}' von Lager "
                    f"'{source_warehouse.get('lagername', source_warehouse_id)}' nach "
                    f"'{target_warehouse.get('lagername', target_warehouse_id)}' verschoben."
                ),
            },
        )

    def list_inventory(self, warehouse_id: str) -> List[Dict]:
        """List all inventory entries for a warehouse, enriched with product details.

        Args:
            warehouse_id (str): Unique warehouse identifier.

        Returns:
            List[Dict]: Inventory entries each containing _id, lager_id, produkt_id,
                produkt_name, produkt_beschreibung and menge.

        Raises:
            KeyError: If no warehouse with warehouse_id exists.
        """
        warehouse = self._db.find_by_id(COLLECTION_LAGER, warehouse_id)
        if not warehouse:
            raise KeyError(f"Lager '{warehouse_id}' nicht gefunden.")
        entries = self._db.find_inventory_by_warehouse(warehouse_id)
        result = []
        for e in entries:
            product = self._db.find_by_id(COLLECTION_PRODUKTE, e.get("produkt_id", ""))
            result.append(
                {
                    "_id": e.get("_id", ""),
                    "lager_id": warehouse_id,
                    "produkt_id": e.get("produkt_id", ""),
                    "produkt_name": product.get("name", "?") if product else "?",
                    "produkt_beschreibung": product.get("beschreibung", "") if product else "",
                    "menge": e.get("menge", 0),
                }
            )
        return result
