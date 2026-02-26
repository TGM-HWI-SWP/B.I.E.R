"""MongoDB adapter – concrete implementation of DatabasePort."""

from os import environ
from typing import Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
import pymongo

from bierapp.contracts import DatabasePort

COLLECTION_PRODUKTE = "produkte"
COLLECTION_LAGER = "lager"
COLLECTION_INVENTAR = "inventar"
COLLECTION_EVENTS = "events"


class MongoDBAdapter(DatabasePort):
    """Concrete MongoDB adapter that implements DatabasePort.

    Connection parameters are read from environment variables so the same
    code works in Docker Compose and in local development without changes.
    Supported environment variables: MONGO_HOST, MONGO_PORT, MONGO_DB,
    MONGO_USER, MONGO_PASS.
    """

    def __init__(self) -> None:
        """Read connection settings from environment variables."""
        self._client: Optional[pymongo.MongoClient] = None
        self._db = None
        self._host = environ.get("MONGO_HOST", "localhost")
        self._port = int(environ.get("MONGO_PORT", 27017))
        self._db_name = environ.get("MONGO_DB", "bierapp")
        self._user = environ.get("MONGO_USER", "admin")
        self._password = environ.get("MONGO_PASS", "secret")

    def connect(self) -> None:
        """Establish a connection to MongoDB and select the target database.

        Raises:
            ConnectionError: If the MongoDB server is not reachable within 5 s.
        """
        uri = f"mongodb://{self._user}:{self._password}@{self._host}:{self._port}/"
        self._client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5_000)
        self._client.admin.command("ping")
        self._db = self._client[self._db_name]

    def insert(self, collection: str, data: Dict) -> str:
        """Insert a document into a collection.

        Args:
            collection (str): Target collection name.
            data (Dict): Document to insert.

        Returns:
            str: String representation of the inserted document's ObjectId.
        """
        self._require_connection()
        result = self._db[collection].insert_one(data)
        return str(result.inserted_id)

    def find_by_id(self, collection: str, document_id: str) -> Optional[Dict]:
        """Retrieve a single document by its ObjectId string.

        Args:
            collection (str): Collection name.
            document_id (str): String form of the MongoDB ObjectId.

        Returns:
            Optional[Dict]: Serialised document if found, otherwise None.
        """
        self._require_connection()
        try:
            oid = ObjectId(document_id)
        except InvalidId:
            return None
        doc = self._db[collection].find_one({"_id": oid})
        return self._serialize(doc) if doc else None

    def find_all(self, collection: str) -> List[Dict]:
        """Retrieve all documents from a collection.

        Args:
            collection (str): Collection name.

        Returns:
            List[Dict]: List of all serialised documents.
        """
        self._require_connection()
        return [self._serialize(doc) for doc in self._db[collection].find()]

    def update(self, collection: str, document_id: str, data: Dict) -> bool:
        """Apply a partial update ($set) to a document.

        Args:
            collection (str): Collection name.
            document_id (str): String form of the MongoDB ObjectId.
            data (Dict): Fields to set on the matching document.

        Returns:
            bool: True if a document was matched and updated.
        """
        self._require_connection()
        try:
            oid = ObjectId(document_id)
        except InvalidId:
            return False
        result = self._db[collection].update_one({"_id": oid}, {"$set": data})
        return result.matched_count > 0

    def delete(self, collection: str, document_id: str) -> bool:
        """Delete a document from a collection.

        Args:
            collection (str): Collection name.
            document_id (str): String form of the MongoDB ObjectId.

        Returns:
            bool: True if a document was deleted.
        """
        self._require_connection()
        try:
            oid = ObjectId(document_id)
        except InvalidId:
            return False
        result = self._db[collection].delete_one({"_id": oid})
        return result.deleted_count > 0

    def find_inventar_by_lager(self, lager_id: str) -> List[Dict]:
        """Return all inventar documents for a specific warehouse.

        Args:
            lager_id (str): String form of the warehouse ObjectId.

        Returns:
            List[Dict]: All inventory entries belonging to that warehouse.
        """
        self._require_connection()
        cursor = self._db[COLLECTION_INVENTAR].find({"lager_id": lager_id})
        return [self._serialize(doc) for doc in cursor]

    def find_inventar_entry(self, lager_id: str, produkt_id: str) -> Optional[Dict]:
        """Return a single inventar entry matching a warehouse/product pair.

        Args:
            lager_id (str): String form of the warehouse ObjectId.
            produkt_id (str): String form of the product ObjectId.

        Returns:
            Optional[Dict]: The matching inventory document, or None.
        """
        self._require_connection()
        doc = self._db[COLLECTION_INVENTAR].find_one(
            {"lager_id": lager_id, "produkt_id": produkt_id}
        )
        return self._serialize(doc) if doc else None

    def _require_connection(self) -> None:
        """Raise RuntimeError if connect() has not been called yet.

        Raises:
            RuntimeError: If the adapter has no active database connection.
        """
        if self._db is None:
            raise RuntimeError("MongoDBAdapter is not connected. Call connect() first.")

    @staticmethod
    def _serialize(doc: Dict) -> Dict:
        """Convert ObjectId values in a document to plain strings.

        Args:
            doc (Dict): Raw MongoDB document.

        Returns:
            Dict: Document with all ObjectId values replaced by their string forms.
        """
        if doc is None:
            return {}
        result = {}
        for key, value in doc.items():
            result[key] = str(value) if isinstance(value, ObjectId) else value
        return result

    def __enter__(self) -> "MongoDBAdapter":
        """Connect and return self when used as a context manager.

        Returns:
            MongoDBAdapter: This adapter instance after connecting.
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close the MongoDB connection when leaving the context manager.

        Args:
            exc_type: Exception type, if any.
            exc_val: Exception value, if any.
            exc_tb: Exception traceback, if any.
        """
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
