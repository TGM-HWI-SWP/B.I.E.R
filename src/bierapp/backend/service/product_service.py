from typing import Dict, List, Optional
from ...db.postgress import PostgresRepository
from ...contracts import (
    DatabasePort,
    ProductServicePort,
    WarehouseServicePort,
    InventoryServicePort,
    ReportPort,
    HttpResponsePort,
)

class ProductService(ProductServicePort):
    """Service for managing products in the inventory system."""

    COLLECTION = "products"

    def __init__(self, db: DatabasePort):
        self.db = db

    def create_product(self, name: str, beschreibung: str, gewicht: float) -> Dict:
        """
        Create a new product and store it in the database.

        Args:
            name (str): The name of the product.
            beschreibung (str): A description of the product.
            gewicht (float): The weight of the product.

        Returns:
            Dict: The created product including its generated ID.
        """
        if gewicht <= 0:
            raise ValueError("gewicht must be positive")

        data = {
            "name": name,
            "beschreibung": beschreibung,
            "gewicht": gewicht
        }

        product_id = self.db.insert(self.COLLECTION, data)
        data["id"] = product_id
        return data

    def get_product(self, produkt_id: str) -> Optional[Dict]:
        """
        Retrieve a product by its ID.

        Args:
            produkt_id (str): The unique identifier of the product.

        Returns:
            Optional[Dict]: The product if found, otherwise None.
        """
        return self.db.find_by_id(self.COLLECTION, produkt_id)

    def list_products(self) -> List[Dict]:
        """
        Retrieve all products.

        Returns:
            List[Dict]: A list containing all products.
        """
        return self.db.find_all(self.COLLECTION)

    def update_product(self, produkt_id: str, data: Dict) -> Dict:
        """
        Update an existing product.

        Args:
            produkt_id (str): The ID of the product to update.
            data (Dict): The updated product fields.

        Returns:
            Dict: The updated product.
        """
        success = self.db.update(self.COLLECTION, produkt_id, data)

        if not success:
            raise KeyError("Product not found")

        product = self.db.find_by_id(self.COLLECTION, produkt_id)
        return product

    def delete_product(self, produkt_id: str) -> None:
        """
        Delete a product from the database.

        Args:
            produkt_id (str): The ID of the product to delete.

        Returns:
            None: No return value.
        """
        success = self.db.delete(self.COLLECTION, produkt_id)

        if not success:
            raise KeyError("Product not found")

class InventoryService(InventoryServicePort):
    """Service for managing inventory entries in the system."""

    COLLECTION = "inventory"

    def __init__(self, db: DatabasePort):
        self.db = db

    def add_product(self, lager_id: str, produkt_id: str, menge: int) -> None:
        """
        Add a product to a warehouse inventory.

        Args:
            lager_id (str): The ID of the warehouse.
            produkt_id (str): The ID of the product.
            menge (int): The quantity to add.

        Returns:
            None: No return value.
        """
        if menge <= 0:
            raise ValueError("menge must be positive")

        data = {
            "lager_id": lager_id,
            "produkt_id": produkt_id,
            "menge": menge
        }

        self.db.insert(self.COLLECTION, data)

    def update_quantity(self, lager_id: str, produkt_id: str, menge: int) -> None:
        """
        Update the quantity of a product in a warehouse.

        Args:
            lager_id (str): The ID of the warehouse.
            produkt_id (str): The ID of the product.
            menge (int): The new quantity.

        Returns:
            None: No return value.
        """
        if menge < 0:
            raise ValueError("menge cannot be negative")

        inventory = self.db.find_all(self.COLLECTION)

        for item in inventory:
            if item["lager_id"] == lager_id and item["produkt_id"] == produkt_id:
                self.db.update(self.COLLECTION, item["id"], {"menge": menge})
                return

        raise KeyError("Inventory entry not found")

    def remove_product(self, lager_id: str, produkt_id: str) -> None:
        """
        Remove a product from a warehouse inventory.

        Args:
            lager_id (str): The ID of the warehouse.
            produkt_id (str): The ID of the product.

        Returns:
            None: No return value.
        """
        inventory = self.db.find_all(self.COLLECTION)

        for item in inventory:
            if item["lager_id"] == lager_id and item["produkt_id"] == produkt_id:
                self.db.delete(self.COLLECTION, item["id"])
                return

        raise KeyError("Inventory entry not found")

    def list_inventory(self, lager_id: str) -> List[Dict]:
        """
        Retrieve all inventory entries for a warehouse.

        Args:
            lager_id (str): The ID of the warehouse.

        Returns:
            List[Dict]: A list of inventory entries.
        """
        inventory = self.db.find_all(self.COLLECTION)
        return [item for item in inventory if item["lager_id"] == lager_id]
    
class ReportService(ReportPort):
    """Service for generating various reports based on the inventory data."""

    def __init__(self, db: DatabasePort):
        self.db = db

    def inventory_report(self, lager_id: str) -> List[Dict]:
        """
        Generate an inventory report for a warehouse.

        Args:
            lager_id (str): The ID of the warehouse.

        Returns:
            List[Dict]: A list of inventory entries for the warehouse.
        """
        inventory = self.db.find_all("inventory")

        return [item for item in inventory if item["lager_id"] == lager_id]

    def statistics_report(self) -> Dict:
        """
        Generate global statistics about products, warehouses and stock.

        Returns:
            Dict: Aggregated statistics across the system.
        """
        products = self.db.find_all("products")
        warehouses = self.db.find_all("warehouses")
        inventory = self.db.find_all("inventory")

        total_stock = sum(item["menge"] for item in inventory)

        return {
            "total_products": len(products),
            "total_warehouses": len(warehouses),
            "total_stock_units": total_stock
        }
    
class HttpResponseService(HttpResponsePort):
    """Service for creating standardized HTTP responses."""

    def success(self, data: Dict, status: int = 200) -> tuple[Dict, int]:
        """
        Create a successful HTTP response.

        Args:
            data (Dict): The response payload.
            status (int): The HTTP status code.

        Returns:
            tuple[Dict, int]: The response body and status code.
        """
        return {"data": data}, status

    def error(self, message: str, status: int = 400) -> tuple[Dict, int]:
        """
        Create an error HTTP response.

        Args:
            message (str): The error message.
            status (int): The HTTP status code.

        Returns:
            tuple[Dict, int]: The error response and status code.
        """
        return {"error": message}, status
    