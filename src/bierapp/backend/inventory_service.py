"""Inventory service – business logic for the inventar junction collection."""

from typing import Dict, List

from bierapp.backend.models import Event, InventoryEntry
from bierapp.backend.utils import get_current_timestamp
from bierapp.contracts.inventory_port import InventoryServicePort
from bierapp.db.mongodb import (
    COLLECTION_EVENTS,
    COLLECTION_INVENTAR,
    COLLECTION_LAGER,
    COLLECTION_PRODUKTE,
    MongoDBAdapter,
)

class InventoryService(InventoryServicePort):
    """Business logic for managing product stock across warehouses."""

    def __init__(self, db: MongoDBAdapter) -> None:
        """Initialise the service with an already-connected MongoDBAdapter.

        Args:
            db: Connected database adapter used for all persistence operations.
        """
        self._db = db

    def add_product(
        self,
        warehouse_id: str,
        product_id: str,
        quantity: int,
        performed_by: str = "system",
    ) -> None:
        """Add a product to a warehouse inventory.

        If an inventory entry already exists for the warehouse/product pair,
        the quantity is added to the existing amount. Otherwise a new entry
        is created.

        Args:
            warehouse_id: Unique warehouse identifier.
            product_id: Unique product identifier.
            quantity: Quantity to add. Must be a non-negative integer.
            performed_by: Name or identifier of the user performing the action.

        Raises:
            ValueError: If quantity is negative or not an integer.
            KeyError: If warehouse_id or product_id do not exist.
        """
        if not isinstance(quantity, int) or quantity < 0:
            raise ValueError("Menge muss eine nicht-negative ganze Zahl sein.")

        warehouse = self._db.find_by_id(COLLECTION_LAGER, warehouse_id)
        if not warehouse:
            raise KeyError(f"Lager '{warehouse_id}' nicht gefunden.")

        product = self._db.find_by_id(COLLECTION_PRODUKTE, product_id)
        if not product:
            raise KeyError(f"Produkt '{product_id}' nicht gefunden.")

        existing_entry = self._db.find_inventory_entry(warehouse_id, product_id)

        if existing_entry:
            # Merge quantities
            current_quantity = existing_entry.get("menge", 0)
            new_quantity = current_quantity + quantity
            self._db.update(COLLECTION_INVENTAR, existing_entry["_id"], {"menge": new_quantity})
        else:
            # Create a new inventory entry
            new_entry = InventoryEntry(
                warehouse_id=warehouse_id,
                product_id=product_id,
                quantity=quantity,
            )
            self._db.insert(COLLECTION_INVENTAR, new_entry.to_doc())

        warehouse_name = warehouse.get("lagername", warehouse_id)
        product_name = product.get("name", product_id)

        event = Event(
            timestamp=get_current_timestamp(),
            entity_type="inventar",
            action="stock_add",
            entity_id=f"{warehouse_id}:{product_id}",
            summary=f"Bestand: {quantity}x '{product_name}' zu Lager '{warehouse_name}' hinzugefügt.",
            performed_by=performed_by,
        )
        self._db.insert(COLLECTION_EVENTS, event.to_doc())

    def update_quantity(
        self,
        warehouse_id: str,
        product_id: str,
        quantity: int,
        performed_by: str = "system",
    ) -> None:
        """Set the absolute stock quantity for a product in a warehouse.

        Args:
            warehouse_id: Unique warehouse identifier.
            product_id: Unique product identifier.
            quantity: New absolute quantity. Must be >= 0.
            performed_by: Name or identifier of the user performing the action.

        Raises:
            ValueError: If quantity is negative.
            KeyError: If no inventory entry exists for the given warehouse/product pair.
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
        product_name = product.get("name", product_id)
        warehouse_name = warehouse.get("lagername", warehouse_id)

        event = Event(
            timestamp=get_current_timestamp(),
            entity_type="inventar",
            action="stock_update",
            entity_id=f"{warehouse_id}:{product_id}",
            summary=f"Bestand von '{product_name}' in Lager '{warehouse_name}' auf {quantity} gesetzt.",
            performed_by=performed_by,
        )
        self._db.insert(COLLECTION_EVENTS, event.to_doc())

    def remove_product(
        self,
        warehouse_id: str,
        product_id: str,
        performed_by: str = "system",
    ) -> None:
        """Remove a product entry from a warehouse inventory.

        Args:
            warehouse_id: Unique warehouse identifier.
            product_id: Unique product identifier.
            performed_by: Name or identifier of the user performing the action.

        Raises:
            KeyError: If no inventory entry exists for the given warehouse/product pair.
        """
        entry = self._db.find_inventory_entry(warehouse_id, product_id)
        if not entry:
            raise KeyError(
                f"Kein Inventareintrag für Lager '{warehouse_id}' / Produkt '{product_id}'."
            )

        self._db.delete(COLLECTION_INVENTAR, entry["_id"])

        product = self._db.find_by_id(COLLECTION_PRODUKTE, product_id) or {}
        warehouse = self._db.find_by_id(COLLECTION_LAGER, warehouse_id) or {}
        product_name = product.get("name", product_id)
        warehouse_name = warehouse.get("lagername", warehouse_id)

        event = Event(
            timestamp=get_current_timestamp(),
            entity_type="inventar",
            action="stock_remove",
            entity_id=f"{warehouse_id}:{product_id}",
            summary=f"Bestandseintrag von '{product_name}' in Lager '{warehouse_name}' entfernt.",
            performed_by=performed_by,
        )
        self._db.insert(COLLECTION_EVENTS, event.to_doc())

    def remove_stock(
        self,
        warehouse_id: str,
        product_id: str,
        quantity: int,
        performed_by: str = "system",
    ) -> None:
        """Reduce the stocked quantity by a given amount (stock-out booking).

        Unlike update_quantity which sets an absolute value, this method subtracts
        the given quantity from the current stock level. Raises ValueError if the
        resulting quantity would go below zero.

        Args:
            warehouse_id: Unique warehouse identifier.
            product_id: Unique product identifier.
            quantity: Number of units to remove. Must be > 0.
            performed_by: Name or identifier of the user performing the action.

        Raises:
            ValueError: If quantity <= 0 or greater than the current stock level.
            KeyError: If no inventory entry exists for the given warehouse/product pair.
        """
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Menge zum Entnehmen muss eine positive ganze Zahl sein.")

        entry = self._db.find_inventory_entry(warehouse_id, product_id)
        if not entry:
            raise KeyError(
                f"Kein Inventareintrag für Lager '{warehouse_id}' / Produkt '{product_id}'."
            )

        current_quantity = int(entry.get("menge", 0))
        if quantity > current_quantity:
            raise ValueError(
                f"Unzureichender Bestand. Verfügbar: {current_quantity}, Angefordert: {quantity}."
            )

        remaining_quantity = current_quantity - quantity
        self._db.update(COLLECTION_INVENTAR, entry["_id"], {"menge": remaining_quantity})

        product = self._db.find_by_id(COLLECTION_PRODUKTE, product_id) or {}
        warehouse = self._db.find_by_id(COLLECTION_LAGER, warehouse_id) or {}
        product_name = product.get("name", product_id)
        warehouse_name = warehouse.get("lagername", warehouse_id)

        event = Event(
            timestamp=get_current_timestamp(),
            entity_type="inventar",
            action="stock_out",
            entity_id=f"{warehouse_id}:{product_id}",
            summary=(
                f"{quantity}x '{product_name}' aus Lager '{warehouse_name}' entnommen "
                f"(Restbestand: {remaining_quantity})."
            ),
            performed_by=performed_by,
        )
        self._db.insert(COLLECTION_EVENTS, event.to_doc())

    def get_total_inventory_value(self) -> float:
        """Calculate the total monetary value of all stocked products across all warehouses.

        For each inventory entry, looks up the product price and multiplies it by the
        stocked quantity. Products without a price field contribute 0.0 to the total.

        Returns:
            The sum of (price × quantity) for every inventory entry.
        """
        all_inventory = self._db.find_all(COLLECTION_INVENTAR)
        total_value = 0.0

        for entry in all_inventory:
            product_id = entry.get("produkt_id", "")
            quantity = int(entry.get("menge", 0))

            product = self._db.find_by_id(COLLECTION_PRODUKTE, product_id) or {}
            price = float(product.get("preis", 0.0))

            entry_value = price * quantity
            total_value += entry_value

        return total_value

    def move_product(
        self,
        source_warehouse_id: str,
        target_warehouse_id: str,
        product_id: str,
        quantity: int,
    ) -> None:
        """Move a quantity of a product from one warehouse to another.

        Args:
            source_warehouse_id: ID of the warehouse to move stock from.
            target_warehouse_id: ID of the destination warehouse.
            product_id: Product identifier.
            quantity: Quantity to move. Must be > 0.

        Raises:
            ValueError: If quantity <= 0 or greater than available stock.
            KeyError: If source entry, warehouses or product do not exist.
        """
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Menge zum Verschieben muss eine positive ganze Zahl sein.")

        source_warehouse = self._db.find_by_id(COLLECTION_LAGER, source_warehouse_id)
        if not source_warehouse:
            raise KeyError(f"Quelllager '{source_warehouse_id}' nicht gefunden.")

        target_warehouse = self._db.find_by_id(COLLECTION_LAGER, target_warehouse_id)
        if not target_warehouse:
            raise KeyError(f"Ziellager '{target_warehouse_id}' nicht gefunden.")

        product = self._db.find_by_id(COLLECTION_PRODUKTE, product_id)
        if not product:
            raise KeyError(f"Produkt '{product_id}' nicht gefunden.")

        source_entry = self._db.find_inventory_entry(source_warehouse_id, product_id)
        if not source_entry:
            raise KeyError(
                f"Kein Inventareintrag für Lager '{source_warehouse_id}' / Produkt '{product_id}'."
            )

        current_quantity = int(source_entry.get("menge", 0))
        if quantity > current_quantity:
            raise ValueError(
                "Es können nicht mehr Einheiten verschoben werden als vorhanden sind."
            )

        # Reduce stock in source warehouse (or delete the entry if stock reaches zero)
        remaining_in_source = current_quantity - quantity
        if remaining_in_source > 0:
            self._db.update(
                COLLECTION_INVENTAR,
                source_entry["_id"],
                {"menge": remaining_in_source},
            )
        else:
            self._db.delete(COLLECTION_INVENTAR, source_entry["_id"])

        # Increase stock in target warehouse (or create a new entry)
        target_entry = self._db.find_inventory_entry(target_warehouse_id, product_id)
        if target_entry:
            existing_quantity = int(target_entry.get("menge", 0))
            new_quantity = existing_quantity + quantity
            self._db.update(
                COLLECTION_INVENTAR,
                target_entry["_id"],
                {"menge": new_quantity},
            )
        else:
            new_target_entry = InventoryEntry(
                warehouse_id=target_warehouse_id,
                product_id=product_id,
                quantity=quantity,
            )
            self._db.insert(COLLECTION_INVENTAR, new_target_entry.to_doc())

        source_name = source_warehouse.get("lagername", source_warehouse_id)
        target_name = target_warehouse.get("lagername", target_warehouse_id)
        product_name = product.get("name", product_id)

        event = Event(
            timestamp=get_current_timestamp(),
            entity_type="inventar",
            action="stock_move",
            entity_id=product_id,
            summary=(
                f"{quantity}x '{product_name}' von Lager '{source_name}' "
                f"nach '{target_name}' verschoben."
            ),
        )
        self._db.insert(COLLECTION_EVENTS, event.to_doc())

    def list_inventory(self, warehouse_id: str) -> List[Dict]:
        """List all inventory entries for a warehouse, enriched with product details.

        Args:
            warehouse_id: Unique warehouse identifier.

        Returns:
            A list of inventory entries. Each entry contains the fields:
            _id, lager_id, produkt_id, produkt_name, produkt_beschreibung, menge.

        Raises:
            KeyError: If no warehouse with warehouse_id exists.
        """
        warehouse = self._db.find_by_id(COLLECTION_LAGER, warehouse_id)
        if not warehouse:
            raise KeyError(f"Lager '{warehouse_id}' nicht gefunden.")

        raw_entries = self._db.find_inventory_by_warehouse(warehouse_id)
        enriched_entries = []

        for entry in raw_entries:
            product_id = entry.get("produkt_id", "")
            product = self._db.find_by_id(COLLECTION_PRODUKTE, product_id)

            if product:
                product_name = product.get("name", "?")
                product_description = product.get("beschreibung", "")
            else:
                product_name = "?"
                product_description = ""

            enriched_entry = {
                "_id": entry.get("_id", ""),
                "lager_id": warehouse_id,
                "produkt_id": product_id,
                "produkt_name": product_name,
                "produkt_beschreibung": product_description,
                "menge": entry.get("menge", 0),
            }
            enriched_entries.append(enriched_entry)

        return enriched_entries
