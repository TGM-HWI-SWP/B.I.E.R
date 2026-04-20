"""Product service – business logic for the produkte collection."""

from typing import Dict, List, Optional

from bierapp.backend.models import Event, Product
from bierapp.backend.utils import get_current_timestamp
from bierapp.contracts.product_port import ProductServicePort
from bierapp.db.mongodb import COLLECTION_EVENTS, COLLECTION_PRODUKTE, MongoDBAdapter

class ProductService(ProductServicePort):
    """Business logic for creating, reading, updating and deleting products."""

    def __init__(self, db: MongoDBAdapter) -> None:
        """Initialise the service with an already-connected MongoDBAdapter.

        Args:
            db: Connected database adapter used for all persistence operations.
        """
        self._db = db

    def create_product(
        self,
        name: str,
        description: str,
        weight: float,
        price: float = 0.0,
        performed_by: str = "system",
    ) -> Dict:
        """Validate inputs and persist a new product document.

        Args:
            name: Human-readable product name. Must not be empty.
            description: Short description of the product.
            weight: Weight of the product in kilograms. Must be >= 0.
            price: Unit price of the product. Must be >= 0. Defaults to 0.0.
            performed_by: Name or identifier of the user performing the action.

        Returns:
            The newly created product document including its generated _id.

        Raises:
            ValueError: If name is empty, weight is negative, or price is negative.
        """
        product = Product(name=name, description=description, weight=weight, price=price)

        product_doc = product.to_doc()
        product_id = self._db.insert(COLLECTION_PRODUKTE, product_doc)
        product_doc["_id"] = product_id

        event = Event(
            timestamp=get_current_timestamp(),
            entity_type="produkt",
            action="create",
            entity_id=product_id,
            summary=f"Produkt '{product.name}' angelegt.",
            performed_by=performed_by,
        )
        self._db.insert(COLLECTION_EVENTS, event.to_doc())

        return product_doc

    def get_product(self, product_id: str) -> Optional[Dict]:
        """Retrieve a single product by its ID.

        Args:
            product_id: Unique product identifier.

        Returns:
            Product data if found, otherwise None.
        """
        return self._db.find_by_id(COLLECTION_PRODUKTE, product_id)

    def list_products(self) -> List[Dict]:
        """Return all products stored in the database.

        Returns:
            A list of all product documents.
        """
        return self._db.find_all(COLLECTION_PRODUKTE)

    def update_product(self, product_id: str, data: Dict, performed_by: str = "system") -> Dict:
        """Apply a partial update to an existing product.

        Only known and valid fields are applied. Unrecognised keys are stored
        as-is to support custom attributes added via the UI.

        Args:
            product_id: Unique product identifier.
            data: Fields to update.
            performed_by: Name or identifier of the user performing the action.

        Returns:
            The updated product document.

        Raises:
            KeyError: If no product with product_id exists.
            ValueError: If any standard field fails validation.
        """
        existing = self._db.find_by_id(COLLECTION_PRODUKTE, product_id)
        if not existing:
            raise KeyError(f"Produkt '{product_id}' nicht gefunden.")

        validated_update = {}

        if "name" in data:
            new_name = data["name"].strip()
            if not new_name:
                raise ValueError("Produktname darf nicht leer sein.")
            validated_update["name"] = new_name

        if "beschreibung" in data:
            validated_update["beschreibung"] = data["beschreibung"].strip()

        if "gewicht" in data:
            new_weight = float(data["gewicht"])
            if new_weight < 0:
                raise ValueError("Gewicht muss >= 0 sein.")
            validated_update["gewicht"] = new_weight

        # Pass through all other fields without special validation
        for key, value in data.items():
            if key not in ("name", "beschreibung", "gewicht"):
                validated_update[key] = value

        self._db.update(COLLECTION_PRODUKTE, product_id, validated_update)
        updated_product = self._db.find_by_id(COLLECTION_PRODUKTE, product_id) or {}

        event = Event(
            timestamp=get_current_timestamp(),
            entity_type="produkt",
            action="update",
            entity_id=product_id,
            summary=f"Produkt '{updated_product.get('name', product_id)}' aktualisiert.",
            performed_by=performed_by,
        )
        self._db.insert(COLLECTION_EVENTS, event.to_doc())

        return updated_product

    def delete_product(self, product_id: str, performed_by: str = "system") -> None:
        """Permanently delete a product from the database.

        Args:
            product_id: Unique product identifier.
            performed_by: Name or identifier of the user performing the action.

        Raises:
            KeyError: If no product with product_id exists.
        """
        existing = self._db.find_by_id(COLLECTION_PRODUKTE, product_id)
        if not existing:
            raise KeyError(f"Produkt '{product_id}' nicht gefunden.")

        self._db.delete(COLLECTION_PRODUKTE, product_id)

        event = Event(
            timestamp=get_current_timestamp(),
            entity_type="produkt",
            action="delete",
            entity_id=product_id,
            summary=f"Produkt '{existing.get('name', product_id)}' gelöscht.",
            performed_by=performed_by,
        )
        self._db.insert(COLLECTION_EVENTS, event.to_doc())
