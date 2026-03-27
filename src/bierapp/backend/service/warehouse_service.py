class WarehouseService:

    COLLECTION = "warehouses"

    def __init__(self, db):
        self.db = db

    # =========================
    # CREATE WAREHOUSE
    # =========================
    def create_warehouse(self, lagername, adresse, max_plaetze, firma_id):
        data = {
            "lagername": lagername,
            "adresse": adresse,
            "max_plaetze": max_plaetze,
            "firma_id": firma_id
        }

        warehouse_id = self.db.insert(self.COLLECTION, data)
        data["id"] = warehouse_id
        return data

    # =========================
    # GET ALL WAREHOUSES
    # =========================
    def list_warehouses(self):
        return self.db.find_all(self.COLLECTION)

    # =========================
    # DELETE WAREHOUSE
    # =========================
    def delete_warehouse(self, lager_id):
        success = self.db.delete(self.COLLECTION, lager_id)

        if not success:
            raise KeyError("Warehouse not found")