"""Service for managing warehouses in the inventory system."""

from typing import Dict, List, Optional


class WarehouseService:
    """Service for managing warehouse operations and inventory assignments."""

    COLLECTION = "warehouses"

    def __init__(self, db):
        """Initialize the warehouse service with a database connection.

        Args:
            db: Database service instance implementing DatabasePort.
        """
        self.db = db

    def create_warehouse(self, lagername: str, adresse: str, max_plaetze: int, firma_id: int) -> Dict:
        """Create a new warehouse in the system.

        Args:
            lagername (str): The name of the warehouse.
            adresse (str): The address of the warehouse.
            max_plaetze (int): The maximum number of storage positions.
            firma_id (int): The ID of the company owning the warehouse.

        Returns:
            Dict: The created warehouse record including its generated ID.
        """
        data = {"lagername": lagername, "adresse": adresse, "max_plaetze": max_plaetze, "firma_id": firma_id}
        warehouse_id = self.db.insert(self.COLLECTION, data)
        data["id"] = warehouse_id
        return data

    def list_warehouses(self) -> List[Dict]:
        """Retrieve all warehouses in the system.

        Returns:
            List[Dict]: A list of all warehouse records.
        """
        return self.db.find_all(self.COLLECTION)

    def get_warehouse(self, warehouse_id: str) -> Optional[Dict]:
        """Retrieve a specific warehouse by its ID.

        Args:
            warehouse_id (str): The unique identifier of the warehouse.

        Returns:
            Optional[Dict]: The warehouse record if found, otherwise None.
        """
        return self.db.find_by_id(self.COLLECTION, warehouse_id)

    def delete_warehouse(self, lager_id: str) -> None:
        """Delete a warehouse from the system.

        Args:
            lager_id (str): The ID of the warehouse to delete.

        Raises:
            KeyError: If the warehouse cannot be found or deletion fails.
        """
        success = self.db.delete(self.COLLECTION, lager_id)
        if not success:
            raise KeyError("Warehouse not found")

    def add_product_to_warehouse(self, lager_id: int, produkt_id: int, menge: int) -> None:
        """Assign a product to a warehouse inventory.

        Args:
            lager_id (int): The ID of the warehouse.
            produkt_id (int): The ID of the product.
            menge (int): The quantity of the product to add.

        Raises:
            ValueError: If the quantity is not positive.
        """
        if menge <= 0:
            raise ValueError("Quantity (menge) must be positive")
        inventory_data = {"lager_id": lager_id, "produkt_id": produkt_id, "menge": menge}
        self.db.insert("inventory", inventory_data)
