"""Product and Inventory Services - Core business logic for product and inventory management."""

import json
from typing import Dict, List, Optional
from ...contracts import DatabasePort, ProductServicePort, InventoryServicePort


class ProductService(ProductServicePort):
    """Service for managing products in the inventory system."""

    COLLECTION = "products"

    def __init__(self, db: DatabasePort):
        """Initialize the product service with a database connection.

        Args:
            db (DatabasePort): Database service instance.
        """
        self.db = db

    def _normalize_attribute(self, attribute) -> Optional[Dict[str, str]]:
        if isinstance(attribute, str):
            text = attribute.strip()
            if not text:
                return None
            if "=" in text:
                name, value = text.split("=", 1)
                return {"name": name.strip(), "value": value.strip()}
            return {"name": text, "value": ""}

        if isinstance(attribute, dict):
            name = str(attribute.get("name") or attribute.get("label") or attribute.get("attribute") or "").strip()
            value = str(attribute.get("value") or attribute.get("wert") or attribute.get("text") or "").strip()
            if not name and not value:
                return None
            return {"name": name, "value": value}

        return None

    def _normalize_attributes(self, attributes) -> List[Dict[str, str]]:
        if attributes is None:
            return []
        if isinstance(attributes, str):
            try:
                attributes = json.loads(attributes)
            except Exception:
                return []
        if isinstance(attributes, dict):
            attributes = [attributes]
        if not isinstance(attributes, list):
            return []

        normalized: List[Dict[str, str]] = []
        for attribute in attributes:
            item = self._normalize_attribute(attribute)
            if item:
                normalized.append(item)
        return normalized

    def _normalize_product(self, product: Optional[Dict]) -> Optional[Dict]:
        if product is None:
            return None
        normalized = dict(product)
        normalized["attributes"] = self._normalize_attributes(normalized.get("attributes"))
        return normalized

    def create_product(self, name: str, beschreibung: str, gewicht: float, preis: float = 0.0, waehrung: str = "EUR", lieferant: str = "", einheit: str = "Stk", attributes=None) -> Dict:
        """Create a new product and store it in the database.

        Args:
            name (str): The name of the product.
            beschreibung (str): A description of the product.
            gewicht (float): The weight of the product.
            preis (float): The price per unit.
            waehrung (str): The currency for the price.
            lieferant (str): Supplier name of the product.
            einheit (str): Unit of the product amount.

        Returns:
            Dict: The created product including its generated ID.

        Raises:
            ValueError: If weight is not positive.
        """
        if gewicht <= 0:
            raise ValueError("gewicht must be positive")
        if preis < 0:
            raise ValueError("preis cannot be negative")
        data = {
            "name": name,
            "beschreibung": beschreibung,
            "gewicht": gewicht,
            "preis": preis,
            "waehrung": waehrung or "EUR",
            "lieferant": lieferant or "",
            "einheit": einheit or "Stk",
            "attributes": self._normalize_attributes(attributes),
        }
        product_id = self.db.insert(self.COLLECTION, data)
        data["id"] = product_id
        return data

    def get_product(self, produkt_id: str) -> Optional[Dict]:
        """Retrieve a product by its ID.

        Args:
            produkt_id (str): The unique identifier of the product.

        Returns:
            Optional[Dict]: The product if found, otherwise None.
        """
        return self._normalize_product(self.db.find_by_id(self.COLLECTION, produkt_id))

    def list_products(self) -> List[Dict]:
        """Retrieve all products.

        Returns:
            List[Dict]: A list containing all products.
        """
        return [product for product in (self._normalize_product(product) for product in self.db.find_all(self.COLLECTION)) if product is not None]

    def update_product(self, produkt_id: str, data: Dict) -> Dict:
        """Update an existing product.

        Args:
            produkt_id (str): The ID of the product to update.
            data (Dict): The updated product fields.

        Returns:
            Dict: The updated product.

        Raises:
            KeyError: If product not found.
        """
        payload = dict(data)
        if "attributes" in payload:
            payload["attributes"] = self._normalize_attributes(payload.get("attributes"))

        success = self.db.update(self.COLLECTION, produkt_id, payload)
        if not success:
            raise KeyError("Product not found")
        product = self.db.find_by_id(self.COLLECTION, produkt_id)
        return self._normalize_product(product) or {}

    def delete_product(self, produkt_id: str) -> None:
        """Delete a product from the database.

        Args:
            produkt_id (str): The ID of the product to delete.

        Raises:
            KeyError: If product not found.
        """
        success = self.db.delete(self.COLLECTION, produkt_id)
        if not success:
            raise KeyError("Product not found")


class InventoryService(InventoryServicePort):
    """Service for managing inventory entries in the system."""

    COLLECTION = "inventory"

    def __init__(self, db: DatabasePort):
        """Initialize the inventory service with a database connection.

        Args:
            db (DatabasePort): Database service instance.
        """
        self.db = db

    def _normalize_id(self, value) -> int:
        return int(value)

    def _find_inventory_item(self, lager_id, produkt_id) -> Optional[Dict]:
        """Find an inventory item by warehouse and product IDs.

        Args:
            lager_id (str): The ID of the warehouse.
            produkt_id (str): The ID of the product.

        Returns:
            Optional[Dict]: The inventory item if found, otherwise None.
        """
        lager_id = self._normalize_id(lager_id)
        produkt_id = self._normalize_id(produkt_id)
        inventory = self.db.find_all(self.COLLECTION)
        for item in inventory:
            if int(item["lager_id"]) == lager_id and int(item["produkt_id"]) == produkt_id:
                return item
        return None

    def add_product(self, lager_id, produkt_id, menge: int) -> None:
        """Add a product to a warehouse inventory.

        Args:
            lager_id (str): The ID of the warehouse.
            produkt_id (str): The ID of the product.
            menge (int): The quantity to add.

        Raises:
            ValueError: If quantity is not positive.
        """
        if menge <= 0:
            raise ValueError("menge must be positive")
        data = {"lager_id": self._normalize_id(lager_id), "produkt_id": self._normalize_id(produkt_id), "menge": menge}
        self.db.insert(self.COLLECTION, data)

    def update_quantity(self, lager_id, produkt_id, menge: int) -> None:
        """Update the quantity of a product in a warehouse.

        Args:
            lager_id (str): The ID of the warehouse.
            produkt_id (str): The ID of the product.
            menge (int): The new quantity.

        Raises:
            ValueError: If quantity is negative.
            KeyError: If inventory entry not found.
        """
        if menge < 0:
            raise ValueError("menge cannot be negative")
        item = self._find_inventory_item(lager_id, produkt_id)
        if item is None:
            raise KeyError("Inventory entry not found")
        self.db.update(self.COLLECTION, item["id"], {"menge": menge})

    def remove_product(self, lager_id, produkt_id) -> None:
        """Remove a product from a warehouse inventory.

        Args:
            lager_id (str): The ID of the warehouse.
            produkt_id (str): The ID of the product.

        Raises:
            KeyError: If inventory entry not found.
        """
        item = self._find_inventory_item(lager_id, produkt_id)
        if item is None:
            raise KeyError("Inventory entry not found")
        self.db.delete(self.COLLECTION, item["id"])

    def list_inventory(self, lager_id) -> List[Dict]:
        """Retrieve all inventory entries for a warehouse.

        Args:
            lager_id (str): The ID of the warehouse.

        Returns:
            List[Dict]: A list of inventory entries.
        """
        lager_id = self._normalize_id(lager_id)
        inventory = self.db.find_all(self.COLLECTION)
        return [item for item in inventory if int(item["lager_id"]) == lager_id]

    def set_quantity(self, lager_id, produkt_id, menge: int) -> None:
        """Set the quantity of a product in a warehouse.

        Creates the inventory entry if it does not exist and menge > 0.
        Removes the inventory entry if menge == 0.
        """

        if menge < 0:
            raise ValueError("menge cannot be negative")
        if menge == 0:
            try:
                self.remove_product(lager_id, produkt_id)
            except KeyError:
                return
            return

        item = self._find_inventory_item(lager_id, produkt_id)
        if item is None:
            self.add_product(lager_id, produkt_id, menge)
            return
        self.db.update(self.COLLECTION, item["id"], {"menge": menge})

    def statistics_report(self) -> Dict:
        """Generate global statistics about products, warehouses and stock.

        Returns:
            Dict: Aggregated statistics across the system.
        """
        products = self.db.find_all("products")
        warehouses = self.db.find_all("warehouses")
        inventory = self.db.find_all("inventory")
        total_stock = sum(item["menge"] for item in inventory)
        return {"total_products": len(products), "total_warehouses": len(warehouses), "total_stock_units": total_stock}
