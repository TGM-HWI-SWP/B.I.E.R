"""Abstract base class (port) for warehouse-related business logic."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class WarehouseServicePort(ABC):
    """Abstract interface for warehouse-related business logic."""

    @abstractmethod
    def create_warehouse(self, warehouse_name: str, address: str, max_slots: int) -> Dict:
        """Create a new warehouse and persist it.

        Args:
            warehouse_name: Human-readable warehouse name.
            address: Physical address of the warehouse.
            max_slots: Maximum number of storage slots. Must be > 0.

        Returns:
            A dictionary representing the newly created warehouse.

        Raises:
            ValueError: If max_slots is not a positive integer.
        """
        ...

    @abstractmethod
    def get_warehouse(self, warehouse_id: str) -> Optional[Dict]:
        """Retrieve a single warehouse by its unique identifier.

        Args:
            warehouse_id: Unique warehouse identifier.

        Returns:
            Warehouse data if found, otherwise None.
        """
        ...

    @abstractmethod
    def list_warehouses(self) -> List[Dict]:
        """Return all known warehouses.

        Returns:
            A list of all warehouse representations.
        """
        ...

    @abstractmethod
    def update_warehouse(self, warehouse_id: str, data: Dict) -> Dict:
        """Update fields of an existing warehouse.

        Args:
            warehouse_id: Unique warehouse identifier.
            data: Dictionary of fields to update.

        Returns:
            The updated warehouse representation.

        Raises:
            KeyError: If no warehouse with the given ID exists.
            ValueError: If any updated field fails domain validation.
        """
        ...

    @abstractmethod
    def delete_warehouse(self, warehouse_id: str) -> None:
        """Permanently delete a warehouse.

        Args:
            warehouse_id: Unique warehouse identifier.

        Raises:
            KeyError: If no warehouse with the given ID exists.
        """
        ...
