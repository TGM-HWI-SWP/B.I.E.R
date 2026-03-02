"""Abstract base class (port) for MongoDB database operations."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

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
            collection: Target collection name.
            data: Document to insert.

        Returns:
            The ID of the inserted document as a string.
        """
        ...

    @abstractmethod
    def find_by_id(self, collection: str, document_id: str) -> Optional[Dict]:
        """Retrieve a single document by ID.

        Args:
            collection: Collection name.
            document_id: Unique document identifier.

        Returns:
            The document if found, otherwise None.
        """
        ...

    @abstractmethod
    def find_all(self, collection: str) -> List[Dict]:
        """Retrieve all documents from a collection.

        Args:
            collection: Collection name.

        Returns:
            A list of all documents in the collection.
        """
        ...

    @abstractmethod
    def update(self, collection: str, document_id: str, data: Dict) -> bool:
        """Update a document in a collection.

        Args:
            collection: Collection name.
            document_id: Document identifier.
            data: Fields to update.

        Returns:
            True if the update was successful.
        """
        ...

    @abstractmethod
    def delete(self, collection: str, document_id: str) -> bool:
        """Delete a document from a collection.

        Args:
            collection: Collection name.
            document_id: Document identifier.

        Returns:
            True if the deletion was successful.
        """
        ...

    @abstractmethod
    def find_inventory_by_warehouse(self, warehouse_id: str) -> List[Dict]:
        """Return all inventory documents for a specific warehouse.

        Args:
            warehouse_id: Unique warehouse identifier.

        Returns:
            All inventory entries belonging to that warehouse.
        """
        ...

    @abstractmethod
    def find_inventory_entry(self, warehouse_id: str, product_id: str) -> Optional[Dict]:
        """Return a single inventory entry matching a warehouse and product pair.

        Args:
            warehouse_id: Unique warehouse identifier.
            product_id: Unique product identifier.

        Returns:
            The matching inventory document, or None if not found.
        """
        ...
