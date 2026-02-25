"""Define abstract base classes (ports) for the B.I.E.R application architecture."""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional

# ============================================================
# Database Port (MongoDB Layer)
# ============================================================

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

# ============================================================
# Product Service Port
# ============================================================

class ProductServicePort(ABC):
    """Abstract interface for product-related business logic."""

    @abstractmethod
    def create_product(self, name: str, beschreibung: str, gewicht: float) -> Dict:
        """Create a new product and persist it.

        Args:
            name (str): Human-readable product name.
            beschreibung (str): Short description of the product.
            gewicht (float): Weight of the product in kilograms.

        Returns:
            Dict: Representation of the newly created product.

        Raises:
            ValueError: If any argument fails domain validation.
        """
        ...

    @abstractmethod
    def get_product(self, produkt_id: str) -> Optional[Dict]:
        """Retrieve a single product by its unique identifier.

        Args:
            produkt_id (str): Unique product identifier.

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
    def update_product(self, produkt_id: str, data: Dict) -> Dict:
        """Update fields of an existing product.

        Args:
            produkt_id (str): Unique product identifier.
            data (Dict): Dictionary of fields to update.

        Returns:
            Dict: Updated product representation.

        Raises:
            KeyError: If no product with the given ID exists.
            ValueError: If any updated field fails domain validation.
        """
        ...

    @abstractmethod
    def delete_product(self, produkt_id: str) -> None:
        """Permanently delete a product.

        Args:
            produkt_id (str): Unique product identifier.

        Raises:
            KeyError: If no product with the given ID exists.
        """
        ...

# ============================================================
# Warehouse Service Port
# ============================================================

class WarehouseServicePort(ABC):
    """Abstract interface for warehouse-related business logic."""

    @abstractmethod
    def create_warehouse(self, lagername: str, adresse: str, max_plaetze: int) -> Dict:
        """Create a new warehouse and persist it.

        Args:
            lagername (str): Human-readable warehouse name.
            adresse (str): Physical address of the warehouse.
            max_plaetze (int): Maximum number of storage slots.

        Returns:
            Dict: Representation of the newly created warehouse.

        Raises:
            ValueError: If max_plaetze is not a positive integer.
        """
        ...

    @abstractmethod
    def get_warehouse(self, lager_id: str) -> Optional[Dict]:
        """Retrieve a single warehouse by its unique identifier.

        Args:
            lager_id (str): Unique warehouse identifier.

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
    def update_warehouse(self, lager_id: str, data: Dict) -> Dict:
        """Update fields of an existing warehouse.

        Args:
            lager_id (str): Unique warehouse identifier.
            data (Dict): Dictionary of fields to update.

        Returns:
            Dict: Updated warehouse representation.

        Raises:
            KeyError: If no warehouse with the given ID exists.
            ValueError: If any updated field fails domain validation.
        """
        ...

    @abstractmethod
    def delete_warehouse(self, lager_id: str) -> None:
        """Permanently delete a warehouse.

        Args:
            lager_id (str): Unique warehouse identifier.

        Raises:
            KeyError: If no warehouse with the given ID exists.
        """
        ...

# ============================================================
# Inventory Service Port
# ============================================================

class InventoryServicePort(ABC):
    """Abstract interface for warehouse inventory management."""

    @abstractmethod
    def add_product(self, lager_id: str, produkt_id: str, menge: int) -> None:
        """Add a product entry to a warehouse inventory.

        Args:
            lager_id (str): Unique warehouse identifier.
            produkt_id (str): Unique product identifier.
            menge (int): Initial quantity to stock.

        Raises:
            KeyError: If the warehouse or product does not exist.
            ValueError: If menge is not a positive integer.
        """
        ...

    @abstractmethod
    def update_quantity(self, lager_id: str, produkt_id: str, menge: int) -> None:
        """Update the stocked quantity of a product in a warehouse.

        Args:
            lager_id (str): Unique warehouse identifier.
            produkt_id (str): Unique product identifier.
            menge (int): New absolute quantity value.

        Raises:
            KeyError: If the warehouse or the product entry does not exist.
            ValueError: If menge is negative.
        """
        ...

    @abstractmethod
    def remove_product(self, lager_id: str, produkt_id: str) -> None:
        """Remove a product entry from a warehouse inventory.

        Args:
            lager_id (str): Unique warehouse identifier.
            produkt_id (str): Unique product identifier.

        Raises:
            KeyError: If the warehouse or the product entry does not exist.
        """
        ...

    @abstractmethod
    def list_inventory(self, lager_id: str) -> List[Dict]:
        """List all product entries stocked in a warehouse.

        Args:
            lager_id (str): Unique warehouse identifier.

        Returns:
            List[Dict]: List of inventory entries, each containing
                product_id and menge.

        Raises:
            KeyError: If no warehouse with the given ID exists.
        """
        ...

# ============================================================
# Report Port
# ============================================================

class ReportPort(ABC):
    """Abstract interface for report generation."""

    @abstractmethod
    def inventory_report(self, lager_id: str) -> List[Dict]:
        """Generate an inventory report for a specific warehouse.

        Args:
            lager_id (str): Unique warehouse identifier.

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

# ============================================================
# HTTP Response Port (Flask Adapter)
# ============================================================

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
