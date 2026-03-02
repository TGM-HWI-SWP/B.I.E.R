"""Warehouse service – business logic for the lager collection."""

from typing import Dict, List, Optional

from bierapp.backend.models import Event, Warehouse
from bierapp.backend.utils import get_current_timestamp
from bierapp.contracts.warehouse_port import WarehouseServicePort
from bierapp.db.mongodb import (
    COLLECTION_EVENTS,
    COLLECTION_INVENTAR,
    COLLECTION_LAGER,
    MongoDBAdapter,
)

class WarehouseService(WarehouseServicePort):
    """Business logic for creating, reading, updating and deleting warehouses."""

    def __init__(self, db: MongoDBAdapter) -> None:
        """Initialise the service with an already-connected MongoDBAdapter.

        Args:
            db: Connected database adapter used for all persistence operations.
        """
        self._db = db

    def create_warehouse(
        self,
        warehouse_name: str,
        address: str,
        max_slots: int,
    ) -> Dict:
        """Validate inputs and persist a new warehouse document.

        Args:
            warehouse_name: Human-readable warehouse name. Must not be empty.
            address: Physical address of the warehouse.
            max_slots: Maximum number of storage slots. Must be a positive integer.

        Returns:
            The newly created warehouse document including its generated _id.

        Raises:
            ValueError: If warehouse_name is empty or max_slots is not a positive integer.
        """
        warehouse = Warehouse(name=warehouse_name, address=address, max_slots=max_slots)

        warehouse_doc = warehouse.to_doc()
        warehouse_id = self._db.insert(COLLECTION_LAGER, warehouse_doc)
        warehouse_doc["_id"] = warehouse_id

        event = Event(
            timestamp=get_current_timestamp(),
            entity_type="lager",
            action="create",
            entity_id=warehouse_id,
            summary=f"Lager '{warehouse.name}' angelegt.",
        )
        self._db.insert(COLLECTION_EVENTS, event.to_doc())

        return warehouse_doc

    def get_warehouse(self, warehouse_id: str) -> Optional[Dict]:
        """Retrieve a single warehouse by its ID.

        Args:
            warehouse_id: Unique warehouse identifier.

        Returns:
            Warehouse data if found, otherwise None.
        """
        return self._db.find_by_id(COLLECTION_LAGER, warehouse_id)

    def list_warehouses(self) -> List[Dict]:
        """Return all warehouses stored in the database.

        Returns:
            A list of all warehouse documents.
        """
        return self._db.find_all(COLLECTION_LAGER)

    def update_warehouse(self, warehouse_id: str, data: Dict) -> Dict:
        """Apply a partial update to an existing warehouse.

        Accepted keys are lagername, adresse and max_plaetze. Attempting to
        reduce max_plaetze below the number of currently stocked product types
        raises a ValueError.

        Args:
            warehouse_id: Unique warehouse identifier.
            data: Fields to update.

        Returns:
            The updated warehouse document.

        Raises:
            KeyError: If no warehouse with warehouse_id exists.
            ValueError: If any updated field fails validation.
        """
        existing = self._db.find_by_id(COLLECTION_LAGER, warehouse_id)
        if not existing:
            raise KeyError(f"Lager '{warehouse_id}' nicht gefunden.")

        validated_update = {}

        if "lagername" in data:
            new_name = data["lagername"].strip()
            if not new_name:
                raise ValueError("Lagername darf nicht leer sein.")
            validated_update["lagername"] = new_name

        if "adresse" in data:
            validated_update["adresse"] = data["adresse"].strip()

        if "max_plaetze" in data:
            new_max = int(data["max_plaetze"])
            if new_max <= 0:
                raise ValueError("max_plaetze muss eine positive ganze Zahl sein.")

            # Count distinct products currently stored in this warehouse
            inventory_entries = self._db.find_inventory_by_warehouse(warehouse_id)
            distinct_product_ids = set()
            for entry in inventory_entries:
                product_id = entry.get("produkt_id")
                if product_id:
                    distinct_product_ids.add(product_id)
            current_product_count = len(distinct_product_ids)

            if new_max < current_product_count:
                raise ValueError(
                    f"Maximale Plätze ({new_max}) darf nicht kleiner sein als die Anzahl der "
                    f"bereits eingelagerten Produkte ({current_product_count})."
                )

            validated_update["max_plaetze"] = new_max

        self._db.update(COLLECTION_LAGER, warehouse_id, validated_update)
        updated_warehouse = self._db.find_by_id(COLLECTION_LAGER, warehouse_id) or {}

        event = Event(
            timestamp=get_current_timestamp(),
            entity_type="lager",
            action="update",
            entity_id=warehouse_id,
            summary=f"Lager '{updated_warehouse.get('lagername', warehouse_id)}' aktualisiert.",
        )
        self._db.insert(COLLECTION_EVENTS, event.to_doc())

        return updated_warehouse

    def delete_warehouse(self, warehouse_id: str) -> None:
        """Permanently delete a warehouse from the database.

        Args:
            warehouse_id: Unique warehouse identifier.

        Raises:
            KeyError: If no warehouse with warehouse_id exists.
        """
        existing = self._db.find_by_id(COLLECTION_LAGER, warehouse_id)
        if not existing:
            raise KeyError(f"Lager '{warehouse_id}' nicht gefunden.")

        self._db.delete(COLLECTION_LAGER, warehouse_id)

        event = Event(
            timestamp=get_current_timestamp(),
            entity_type="lager",
            action="delete",
            entity_id=warehouse_id,
            summary=f"Lager '{existing.get('lagername', warehouse_id)}' gelöscht.",
        )
        self._db.insert(COLLECTION_EVENTS, event.to_doc())
