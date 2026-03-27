from typing import Dict, List, Optional
from ...db.postgress import PostgresRepository
from ...contracts import (
    DatabasePort,
)

class dbService(DatabasePort):
    """Service implementing Postgres database operations."""

    def __init__(self, repository: PostgresRepository):
        self.repo = repository

    def connect(self) -> None:
        """
        Establish a connection to the database through the repository.

        Returns:
            None: No return value.
        """
        self.repo.connect()

    def insert(self, collection: str, data: Dict) -> str:
        """
        Insert a new record into a collection.

        Args:
            collection (str): The name of the target database collection.
            data (Dict): The data to insert as key-value pairs.

        Returns:
            str: The ID of the inserted record.
        """
        return self.repo.insert(collection, data)

    def find_by_id(self, collection: str, document_id: str) -> Optional[Dict]:
        """
        Retrieve a record from a collection by its ID.

        Args:
            collection (str): The name of the database collection.
            document_id (str): The unique identifier of the record.

        Returns:
            Optional[Dict]: The record if found, otherwise None.
        """
        return self.repo.find_by_id(collection, document_id)

    def find_all(self, collection: str) -> List[Dict]:
        """
        Retrieve all records from a collection.

        Args:
            collection (str): The name of the database collection.

        Returns:
            List[Dict]: A list containing all records.
        """
        return self.repo.find_all(collection)

    def update(self, collection: str, document_id: str, data: Dict) -> bool:
        """
        Update a record in a collection.

        Args:
            collection (str): The name of the database collection.
            document_id (str): The ID of the record to update.
            data (Dict): The updated fields and values.

        Returns:
            bool: True if the update was successful, otherwise False.
        """
        return self.repo.update(collection, document_id, data)

    def delete(self, collection: str, document_id: str) -> bool:
        """
        Delete a record from a collection.

        Args:
            collection (str): The name of the database collection.
            document_id (str): The ID of the record to delete.

        Returns:
            bool: True if the deletion was successful, otherwise False.
        """
        return self.repo.delete(collection, document_id)