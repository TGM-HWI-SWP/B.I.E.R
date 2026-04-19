"""Product and Inventory Services - Core business logic for product and inventory management."""

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

    def create_product(self, name: str, beschreibung: str, gewicht: float, einheit: str = "Stk") -> Dict:
        """Create a new product and store it in the database.

        Args:
            name (str): The name of the product.
            beschreibung (str): A description of the product.
            gewicht (float): The weight of the product.
            einheit (str): Unit of the product amount.

        Returns:
            Dict: The created product including its generated ID.

        Raises:
            ValueError: If weight is not positive.
        """
        if gewicht <= 0:
            raise ValueError("gewicht must be positive")
        data = {"name": name, "beschreibung": beschreibung, "gewicht": gewicht, "einheit": einheit or "Stk"}
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
        return self.db.find_by_id(self.COLLECTION, produkt_id)

    def list_products(self) -> List[Dict]:
        """Retrieve all products.

        Returns:
            List[Dict]: A list containing all products.
        """
        return self.db.find_all(self.COLLECTION)

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
        success = self.db.update(self.COLLECTION, produkt_id, data)
        if not success:
            raise KeyError("Product not found")
        product = self.db.find_by_id(self.COLLECTION, produkt_id)
        return product

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
