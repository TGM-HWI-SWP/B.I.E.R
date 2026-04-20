"""Abstract base class (port) for warehouse inventory management."""

from abc import ABC, abstractmethod
from typing import Dict, List

class InventoryServicePort(ABC):
    """Abstract interface for warehouse inventory management."""

    @abstractmethod
    def add_product(
        self,
        warehouse_id: str,
        product_id: str,
        quantity: int,
        performed_by: str = "system",
    ) -> None:
        """Add a product entry to a warehouse inventory.

        Args:
            warehouse_id: Unique warehouse identifier.
            product_id: Unique product identifier.
            quantity: Initial quantity to stock.
            performed_by: Name or identifier of the user performing the action.

        Raises:
            KeyError: If the warehouse or product does not exist.
            ValueError: If quantity is not a positive integer.
        """
        ...

    @abstractmethod
    def update_quantity(
        self,
        warehouse_id: str,
        product_id: str,
        quantity: int,
        performed_by: str = "system",
    ) -> None:
        """Update the stocked quantity of a product in a warehouse.

        Args:
            warehouse_id: Unique warehouse identifier.
            product_id: Unique product identifier.
            quantity: New absolute quantity value. Must be >= 0.
            performed_by: Name or identifier of the user performing the action.

        Raises:
            KeyError: If the warehouse or product entry does not exist.
            ValueError: If quantity is negative.
        """
        ...

    @abstractmethod
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
            KeyError: If the warehouse or the product entry does not exist.
        """
        ...

    @abstractmethod
    def remove_stock(
        self,
        warehouse_id: str,
        product_id: str,
        quantity: int,
        performed_by: str = "system",
    ) -> None:
        """Reduce the stocked quantity of a product by a relative amount.

        Args:
            warehouse_id: Unique warehouse identifier.
            product_id: Unique product identifier.
            quantity: Number of units to remove. Must be > 0.
            performed_by: Name or identifier of the user performing the action.

        Raises:
            KeyError: If no inventory entry exists for the given pair.
            ValueError: If quantity <= 0 or greater than the current stock level.
        """
        ...

    @abstractmethod
    def get_total_inventory_value(self) -> float:
        """Calculate the total monetary value of all inventory across all warehouses.

        Multiplies each product's price by its stocked quantity and sums the results.

        Returns:
            Total inventory value in the currency stored on the products.
        """
        ...

    @abstractmethod
    def list_inventory(self, warehouse_id: str) -> List[Dict]:
        """List all product entries stocked in a warehouse.

        Args:
            warehouse_id: Unique warehouse identifier.

        Returns:
            A list of inventory entries, each containing product_id and quantity.

        Raises:
            KeyError: If no warehouse with the given ID exists.
        """
        ...

    @abstractmethod
    def move_product(
        self,
        source_warehouse_id: str,
        target_warehouse_id: str,
        product_id: str,
        quantity: int,
        performed_by: str = "system",
    ) -> None:
        """Move a quantity of a product from one warehouse to another.

        Args:
            source_warehouse_id: ID of the warehouse to move stock from.
            target_warehouse_id: ID of the destination warehouse.
            product_id: Unique product identifier.
            quantity: Quantity to move. Must be > 0.
            performed_by: Name or identifier of the user performing the action.

        Raises:
            ValueError: If quantity <= 0 or greater than available stock.
            KeyError: If source entry, warehouses or product do not exist.
        """
        ...
