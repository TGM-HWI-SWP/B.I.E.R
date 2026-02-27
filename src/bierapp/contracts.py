"""Define abstract base classes (ports) for the B.I.E.R application architecture."""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class DatabasePort(ABC):
    """Abstract interface for MongoDB database operations."""

    @abstractmethod
    def connect(self) -> None:
        """Establish a connection to the MongoDB instance.

        Raises:
            ConnectionError: If the connection cannot be established.
        """
        ...

    @abstractmethod
    def insert(self, collection: str, data: Dict) -> str:
        """Insert a document into a collection.

        Args:
            collection (str): Target collection name.
            data (Dict): Document to insert.

        Returns:
            str: ID of the inserted document.
        """
        ...

    @abstractmethod
    def find_by_id(self, collection: str, document_id: str) -> Optional[Dict]:
        """Retrieve a single document by ID.

        Args:
            collection (str): Collection name.
            document_id (str): Unique document identifier.

        Returns:
            Optional[Dict]: Document if found, otherwise None.
        """
        ...

    @abstractmethod
    def find_all(self, collection: str) -> List[Dict]:
        """Retrieve all documents from a collection.

        Args:
            collection (str): Collection name.

        Returns:
            List[Dict]: List of documents.
        """
        ...

    @abstractmethod
    def update(self, collection: str, document_id: str, data: Dict) -> bool:
        """Update a document in a collection.

        Args:
            collection (str): Collection name.
            document_id (str): Document identifier.
            data (Dict): Fields to update.

        Returns:
            bool: True if update was successful.
        """
        ...

    @abstractmethod
    def delete(self, collection: str, document_id: str) -> bool:
        """Delete a document from a collection.

        Args:
            collection (str): Collection name.
            document_id (str): Document identifier.

        Returns:
            bool: True if deletion was successful.
        """
        ...

    @abstractmethod
    def find_inventory_by_warehouse(self, warehouse_id: str) -> List[Dict]:
        """Return all inventory documents for a specific warehouse.

        Args:
            warehouse_id (str): Unique warehouse identifier.

        Returns:
            List[Dict]: All inventory entries belonging to that warehouse.
        """
        ...

    @abstractmethod
    def find_inventory_entry(self, warehouse_id: str, product_id: str) -> Optional[Dict]:
        """Return a single inventory entry matching a warehouse/product pair.

        Args:
            warehouse_id (str): Unique warehouse identifier.
            product_id (str): Unique product identifier.

        Returns:
            Optional[Dict]: The matching inventory document, or None.
        """
        ...


class ProductServicePort(ABC):
    """Abstract interface for product-related business logic."""

    @abstractmethod
    def create_product(self, name: str, description: str, weight: float, price: float = 0.0) -> Dict:
        """Create a new product and persist it.

        Args:
            name (str): Human-readable product name.
            description (str): Short description of the product.
            weight (float): Weight of the product in kilograms.
            price (float): Unit price of the product in the configured currency. Must be >= 0.

        Returns:
            Dict: Representation of the newly created product.

        Raises:
            ValueError: If any argument fails domain validation.
        """
        ...

    @abstractmethod
    def get_product(self, product_id: str) -> Optional[Dict]:
        """Retrieve a single product by its unique identifier.

        Args:
            product_id (str): Unique product identifier.

        Returns:
            Optional[Dict]: Product data if found, otherwise None.
        """
        ...

    @abstractmethod
    def list_products(self) -> List[Dict]:
        """Return all known products.

        Returns:
            List[Dict]: List of all product representations.
        """
        ...

    @abstractmethod
    def update_product(self, product_id: str, data: Dict) -> Dict:
        """Update fields of an existing product.

        Args:
            product_id (str): Unique product identifier.
            data (Dict): Dictionary of fields to update.

        Returns:
            Dict: Updated product representation.

        Raises:
            KeyError: If no product with the given ID exists.
            ValueError: If any updated field fails domain validation.
        """
        ...

    @abstractmethod
    def delete_product(self, product_id: str) -> None:
        """Permanently delete a product.

        Args:
            product_id (str): Unique product identifier.

        Raises:
            KeyError: If no product with the given ID exists.
        """
        ...


class WarehouseServicePort(ABC):
    """Abstract interface for warehouse-related business logic."""

    @abstractmethod
    def create_warehouse(self, warehouse_name: str, address: str, max_slots: int) -> Dict:
        """Create a new warehouse and persist it.

        Args:
            warehouse_name (str): Human-readable warehouse name.
            address (str): Physical address of the warehouse.
            max_slots (int): Maximum number of storage slots.

        Returns:
            Dict: Representation of the newly created warehouse.

        Raises:
            ValueError: If max_slots is not a positive integer.
        """
        ...

    @abstractmethod
    def get_warehouse(self, warehouse_id: str) -> Optional[Dict]:
        """Retrieve a single warehouse by its unique identifier.

        Args:
            warehouse_id (str): Unique warehouse identifier.

        Returns:
            Optional[Dict]: Warehouse data if found, otherwise None.
        """
        ...

    @abstractmethod
    def list_warehouses(self) -> List[Dict]:
        """Return all known warehouses.

        Returns:
            List[Dict]: List of all warehouse representations.
        """
        ...

    @abstractmethod
    def update_warehouse(self, warehouse_id: str, data: Dict) -> Dict:
        """Update fields of an existing warehouse.

        Args:
            warehouse_id (str): Unique warehouse identifier.
            data (Dict): Dictionary of fields to update.

        Returns:
            Dict: Updated warehouse representation.

        Raises:
            KeyError: If no warehouse with the given ID exists.
            ValueError: If any updated field fails domain validation.
        """
        ...

    @abstractmethod
    def delete_warehouse(self, warehouse_id: str) -> None:
        """Permanently delete a warehouse.

        Args:
            warehouse_id (str): Unique warehouse identifier.

        Raises:
            KeyError: If no warehouse with the given ID exists.
        """
        ...


class InventoryServicePort(ABC):
    """Abstract interface for warehouse inventory management."""

    @abstractmethod
    def add_product(self, warehouse_id: str, product_id: str, quantity: int, performed_by: str = "system") -> None:
        """Add a product entry to a warehouse inventory.

        Args:
            warehouse_id (str): Unique warehouse identifier.
            product_id (str): Unique product identifier.
            quantity (int): Initial quantity to stock.
            performed_by (str): Name or identifier of the user performing the action.

        Raises:
            KeyError: If the warehouse or product does not exist.
            ValueError: If quantity is not a positive integer.
        """
        ...

    @abstractmethod
    def update_quantity(self, warehouse_id: str, product_id: str, quantity: int, performed_by: str = "system") -> None:
        """Update the stocked quantity of a product in a warehouse.

        Args:
            warehouse_id (str): Unique warehouse identifier.
            product_id (str): Unique product identifier.
            quantity (int): New absolute quantity value.
            performed_by (str): Name or identifier of the user performing the action.

        Raises:
            KeyError: If the warehouse or the product entry does not exist.
            ValueError: If quantity is negative.
        """
        ...

    @abstractmethod
    def remove_product(self, warehouse_id: str, product_id: str, performed_by: str = "system") -> None:
        """Remove a product entry from a warehouse inventory.

        Args:
            warehouse_id (str): Unique warehouse identifier.
            product_id (str): Unique product identifier.
            performed_by (str): Name or identifier of the user performing the action.

        Raises:
            KeyError: If the warehouse or the product entry does not exist.
        """
        ...

    @abstractmethod
    def remove_stock(self, warehouse_id: str, product_id: str, quantity: int, performed_by: str = "system") -> None:
        """Reduce the stocked quantity of a product in a warehouse by a relative delta.

        Args:
            warehouse_id (str): Unique warehouse identifier.
            product_id (str): Unique product identifier.
            quantity (int): Number of units to remove. Must be > 0.
            performed_by (str): Name or identifier of the user performing the action.

        Raises:
            KeyError: If no inventory entry exists for the given pair.
            ValueError: If quantity <= 0 or greater than the current stock level.
        """
        ...

    @abstractmethod
    def get_total_inventory_value(self) -> float:
        """Calculate the total monetary value of all inventory across all warehouses.

        Multiplies each product's preis by its stocked menge and sums the results.

        Returns:
            float: Total inventory value in the currency stored on the products.
        """
        ...

    @abstractmethod
    def list_inventory(self, warehouse_id: str) -> List[Dict]:
        """List all product entries stocked in a warehouse.

        Args:
            warehouse_id (str): Unique warehouse identifier.

        Returns:
            List[Dict]: List of inventory entries, each containing
                product_id and quantity.

        Raises:
            KeyError: If no warehouse with the given ID exists.
        """
        ...

    @abstractmethod
    def move_product(self, source_warehouse_id: str, target_warehouse_id: str, product_id: str, quantity: int) -> None:
        """Move a quantity of a product from one warehouse to another.

        Args:
            source_warehouse_id (str): ID of the warehouse to move stock from.
            target_warehouse_id (str): ID of the destination warehouse.
            product_id (str): Unique product identifier.
            quantity (int): Quantity to move. Must be > 0.

        Raises:
            ValueError: If quantity <= 0 or greater than available stock.
            KeyError: If source entry, warehouses or product do not exist.
        """
        ...


class ReportPort(ABC):
    """Abstract interface for report generation."""

    @abstractmethod
    def inventory_report(self, warehouse_id: str) -> List[Dict]:
        """Generate an inventory report for a specific warehouse.

        Args:
            warehouse_id (str): Unique warehouse identifier.

        Returns:
            List[Dict]: Ordered list of inventory entries including product
                details and current stock levels.

        Raises:
            KeyError: If no warehouse with the given ID exists.
        """
        ...

    @abstractmethod
    def statistics_report(self) -> Dict:
        """Generate global statistics across all warehouses and products.

        Returns:
            Dict: Aggregated statistics such as total products, total
                warehouses, total stock units and overall capacity usage.
        """
        ...


class HttpResponsePort(ABC):
    """Abstract interface for HTTP response handling (Flask adapter)."""

    @abstractmethod
    def success(self, data: Dict, status: int = 200) -> tuple[Dict, int]:
        """Build a successful HTTP JSON response.

        Args:
            data (Dict): Payload to include under the ``data`` key.
            status (int): HTTP status code. Defaults to 200.

        Returns:
            tuple[Dict, int]: A tuple of the JSON-serialisable response body
                and the HTTP status code.
        """
        ...

    @abstractmethod
    def error(self, message: str, status: int = 400) -> tuple[Dict, int]:
        """Build an error HTTP JSON response.

        Args:
            message (str): Human-readable error description.
            status (int): HTTP status code. Defaults to 400.

        Returns:
            tuple[Dict, int]: A tuple of the JSON-serialisable response body
                containing the error message and the HTTP status code.
        """
        ...
