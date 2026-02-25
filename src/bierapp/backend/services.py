"""Concrete service implementations for B.I.E.R business logic.

Each service class implements the corresponding abstract port defined in
bierapp.contracts and delegates all persistence to a MongoDBAdapter
instance that must be injected at construction time.
"""

from typing import Dict, List, Optional

from bierapp.contracts import InventoryServicePort, ProductServicePort, WarehouseServicePort
from bierapp.db.mongodb import (
    COLLECTION_INVENTAR,
    COLLECTION_LAGER,
    COLLECTION_PRODUKTE,
    MongoDBAdapter,
)


class ProductService(ProductServicePort):
    """Business logic for the produkte collection."""

    def __init__(self, db: MongoDBAdapter) -> None:
        """Initialise the service with an already-connected MongoDBAdapter.

        Args:
            db (MongoDBAdapter): Connected database adapter used for persistence.
        """
        self._db = db

    def create_product(self, name: str, beschreibung: str, gewicht: float) -> Dict:
        """Validate inputs and persist a new product document.

        Args:
            name (str): Human-readable product name. Must not be empty.
            beschreibung (str): Short description of the product.
            gewicht (float): Weight of the product in kilograms. Must be >= 0.

        Returns:
            Dict: Representation of the newly created product including its _id.

        Raises:
            ValueError: If name is empty or gewicht is negative.
        """
        name = name.strip()
        beschreibung = beschreibung.strip()
        if not name:
            raise ValueError("Produktname darf nicht leer sein.")
        if gewicht < 0:
            raise ValueError("Gewicht muss >= 0 sein.")

        doc = {"name": name, "beschreibung": beschreibung, "gewicht": float(gewicht)}
        doc_id = self._db.insert(COLLECTION_PRODUKTE, doc)
        doc["_id"] = doc_id
        return doc

    def get_product(self, produkt_id: str) -> Optional[Dict]:
        """Retrieve a single product by its ID.

        Args:
            produkt_id (str): Unique product identifier.

        Returns:
            Optional[Dict]: Product data if found, otherwise None.
        """
        return self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id)

    def list_products(self) -> List[Dict]:
        """Return all products stored in the database.

        Returns:
            List[Dict]: List of all product documents.
        """
        return self._db.find_all(COLLECTION_PRODUKTE)

    def update_product(self, produkt_id: str, data: Dict) -> Dict:
        """Apply a partial update to an existing product.

        Args:
            produkt_id (str): Unique product identifier.
            data (Dict): Fields to update. Accepted keys: name, beschreibung, gewicht.

        Returns:
            Dict: Updated product document.

        Raises:
            KeyError: If no product with produkt_id exists.
            ValueError: If any updated field fails validation.
        """
        existing = self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id)
        if not existing:
            raise KeyError(f"Produkt '{produkt_id}' nicht gefunden.")

        allowed = {}
        if "name" in data:
            name = data["name"].strip()
            if not name:
                raise ValueError("Produktname darf nicht leer sein.")
            allowed["name"] = name
        if "beschreibung" in data:
            allowed["beschreibung"] = data["beschreibung"].strip()
        if "gewicht" in data:
            gewicht = float(data["gewicht"])
            if gewicht < 0:
                raise ValueError("Gewicht muss >= 0 sein.")
            allowed["gewicht"] = gewicht

        self._db.update(COLLECTION_PRODUKTE, produkt_id, allowed)
        updated = self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id)
        return updated or {}

    def delete_product(self, produkt_id: str) -> None:
        """Permanently delete a product from the database.

        Args:
            produkt_id (str): Unique product identifier.

        Raises:
            KeyError: If no product with produkt_id exists.
        """
        existing = self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id)
        if not existing:
            raise KeyError(f"Produkt '{produkt_id}' nicht gefunden.")
        self._db.delete(COLLECTION_PRODUKTE, produkt_id)


class WarehouseService(WarehouseServicePort):
    """Business logic for the lager collection."""

    def __init__(self, db: MongoDBAdapter) -> None:
        """Initialise the service with an already-connected MongoDBAdapter.

        Args:
            db (MongoDBAdapter): Connected database adapter used for persistence.
        """
        self._db = db

    def create_warehouse(self, lagername: str, adresse: str, max_plaetze: int) -> Dict:
        """Validate inputs and persist a new warehouse document.

        Args:
            lagername (str): Human-readable warehouse name. Must not be empty.
            adresse (str): Physical address of the warehouse.
            max_plaetze (int): Maximum number of storage slots. Must be > 0.

        Returns:
            Dict: Representation of the newly created warehouse including its _id.

        Raises:
            ValueError: If lagername is empty or max_plaetze is not a positive integer.
        """
        lagername = lagername.strip()
        adresse = adresse.strip()
        if not lagername:
            raise ValueError("Lagername darf nicht leer sein.")
        if not isinstance(max_plaetze, int) or max_plaetze <= 0:
            raise ValueError("max_plaetze muss eine positive ganze Zahl sein.")

        doc = {"lagername": lagername, "adresse": adresse, "max_plaetze": max_plaetze}
        doc_id = self._db.insert(COLLECTION_LAGER, doc)
        doc["_id"] = doc_id
        return doc

    def get_warehouse(self, lager_id: str) -> Optional[Dict]:
        """Retrieve a single warehouse by its ID.

        Args:
            lager_id (str): Unique warehouse identifier.

        Returns:
            Optional[Dict]: Warehouse data if found, otherwise None.
        """
        return self._db.find_by_id(COLLECTION_LAGER, lager_id)

    def list_warehouses(self) -> List[Dict]:
        """Return all warehouses stored in the database.

        Returns:
            List[Dict]: List of all warehouse documents.
        """
        return self._db.find_all(COLLECTION_LAGER)

    def update_warehouse(self, lager_id: str, data: Dict) -> Dict:
        """Apply a partial update to an existing warehouse.

        Args:
            lager_id (str): Unique warehouse identifier.
            data (Dict): Fields to update. Accepted keys: lagername, adresse, max_plaetze.

        Returns:
            Dict: Updated warehouse document.

        Raises:
            KeyError: If no warehouse with lager_id exists.
            ValueError: If any updated field fails validation.
        """
        existing = self._db.find_by_id(COLLECTION_LAGER, lager_id)
        if not existing:
            raise KeyError(f"Lager '{lager_id}' nicht gefunden.")

        allowed = {}
        if "lagername" in data:
            name = data["lagername"].strip()
            if not name:
                raise ValueError("Lagername darf nicht leer sein.")
            allowed["lagername"] = name
        if "adresse" in data:
            allowed["adresse"] = data["adresse"].strip()
        if "max_plaetze" in data:
            mp = int(data["max_plaetze"])
            if mp <= 0:
                raise ValueError("max_plaetze muss eine positive ganze Zahl sein.")
            allowed["max_plaetze"] = mp

        self._db.update(COLLECTION_LAGER, lager_id, allowed)
        updated = self._db.find_by_id(COLLECTION_LAGER, lager_id)
        return updated or {}

    def delete_warehouse(self, lager_id: str) -> None:
        """Permanently delete a warehouse from the database.

        Args:
            lager_id (str): Unique warehouse identifier.

        Raises:
            KeyError: If no warehouse with lager_id exists.
        """
        existing = self._db.find_by_id(COLLECTION_LAGER, lager_id)
        if not existing:
            raise KeyError(f"Lager '{lager_id}' nicht gefunden.")
        self._db.delete(COLLECTION_LAGER, lager_id)


class InventoryService(InventoryServicePort):
    """Business logic for the inventar junction collection."""

    def __init__(self, db: MongoDBAdapter) -> None:
        """Initialise the service with an already-connected MongoDBAdapter.

        Args:
            db (MongoDBAdapter): Connected database adapter used for persistence.
        """
        self._db = db

    def add_product(self, lager_id: str, produkt_id: str, menge: int) -> None:
        """Add a product to a warehouse inventory, merging quantities if it already exists.

        Args:
            lager_id (str): Unique warehouse identifier.
            produkt_id (str): Unique product identifier.
            menge (int): Quantity to add. Must be >= 0.

        Raises:
            ValueError: If menge is negative or not an integer.
            KeyError: If lager_id or produkt_id do not exist in the database.
        """
        if not isinstance(menge, int) or menge < 0:
            raise ValueError("Menge muss eine nicht-negative ganze Zahl sein.")

        lager = self._db.find_by_id(COLLECTION_LAGER, lager_id)
        if not lager:
            raise KeyError(f"Lager '{lager_id}' nicht gefunden.")
        produkt = self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id)
        if not produkt:
            raise KeyError(f"Produkt '{produkt_id}' nicht gefunden.")

        existing = self._db.find_inventar_entry(lager_id, produkt_id)
        if existing:
            new_menge = existing.get("menge", 0) + menge
            self._db.update(COLLECTION_INVENTAR, existing["_id"], {"menge": new_menge})
        else:
            self._db.insert(
                COLLECTION_INVENTAR,
                {"lager_id": lager_id, "produkt_id": produkt_id, "menge": menge},
            )

    def update_quantity(self, lager_id: str, produkt_id: str, menge: int) -> None:
        """Set the absolute stock quantity for a product in a warehouse.

        Args:
            lager_id (str): Unique warehouse identifier.
            produkt_id (str): Unique product identifier.
            menge (int): New absolute quantity. Must be >= 0.

        Raises:
            ValueError: If menge is negative.
            KeyError: If no inventory entry exists for the given pair.
        """
        if menge < 0:
            raise ValueError("Menge darf nicht negativ sein.")
        entry = self._db.find_inventar_entry(lager_id, produkt_id)
        if not entry:
            raise KeyError(
                f"Kein Inventareintrag für Lager '{lager_id}' / Produkt '{produkt_id}'."
            )
        self._db.update(COLLECTION_INVENTAR, entry["_id"], {"menge": menge})

    def remove_product(self, lager_id: str, produkt_id: str) -> None:
        """Remove a product entry from a warehouse inventory.

        Args:
            lager_id (str): Unique warehouse identifier.
            produkt_id (str): Unique product identifier.

        Raises:
            KeyError: If no inventory entry exists for the given pair.
        """
        entry = self._db.find_inventar_entry(lager_id, produkt_id)
        if not entry:
            raise KeyError(
                f"Kein Inventareintrag für Lager '{lager_id}' / Produkt '{produkt_id}'."
            )
        self._db.delete(COLLECTION_INVENTAR, entry["_id"])

    def list_inventory(self, lager_id: str) -> List[Dict]:
        """List all inventory entries for a warehouse, enriched with product details.

        Args:
            lager_id (str): Unique warehouse identifier.

        Returns:
            List[Dict]: Inventory entries each containing _id, lager_id, produkt_id,
                produkt_name, produkt_beschreibung and menge.

        Raises:
            KeyError: If no warehouse with lager_id exists.
        """
        lager = self._db.find_by_id(COLLECTION_LAGER, lager_id)
        if not lager:
            raise KeyError(f"Lager '{lager_id}' nicht gefunden.")
        entries = self._db.find_inventar_by_lager(lager_id)
        result = []
        for e in entries:
            produkt = self._db.find_by_id(COLLECTION_PRODUKTE, e.get("produkt_id", ""))
            result.append(
                {
                    "_id": e.get("_id", ""),
                    "lager_id": lager_id,
                    "produkt_id": e.get("produkt_id", ""),
                    "produkt_name": produkt.get("name", "?") if produkt else "?",
                    "produkt_beschreibung": produkt.get("beschreibung", "") if produkt else "",
                    "menge": e.get("menge", 0),
                }
            )
        return result
