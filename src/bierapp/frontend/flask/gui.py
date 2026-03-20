from flask import Flask, render_template, jsonify, request

# Services & DB
from bierapp.backend.service.product_service import ProductService, InventoryService
from bierapp.backend.service.warehouse_service import WarehouseService
from bierapp.backend.service.db_Service import dbService
from bierapp.db.postgress import PostgresRepository

app = Flask(__name__)

# =========================
# INIT SERVICES
# =========================
repo = PostgresRepository()
db = dbService(repo)

product_service = ProductService(db)
warehouse_service = WarehouseService(db)
inventory_service = InventoryService(db)

# =========================
# FRONTEND
# =========================
@app.route("/")
def index():
    return render_template("index.html")

# =========================
# PRODUCTS API
# =========================

@app.route("/inventory", methods=["POST"])
def add_inventory():
    data = request.json

    inventory_service.add_product(
        lager_id=data["lager_id"],
        produkt_id=data["produkt_id"],
        menge=int(data["menge"])
    )

    return {"status": "ok"}, 201

# GET all products
@app.route("/products", methods=["GET"])
def get_products():
    products = product_service.list_products()
    return jsonify(products)

# CREATE product
@app.route("/products", methods=["POST"])
def create_product():
    data = request.json

    product = product_service.create_product(
        name=data["name"],
        beschreibung=data.get("beschreibung", ""),
        gewicht=float(data["gewicht"])
    )

    return jsonify(product), 201

# DELETE product (optional)
@app.route("/products/<produkt_id>", methods=["DELETE"])
def delete_product(produkt_id):
    product_service.delete_product(produkt_id)
    return "", 204


# =========================
# WAREHOUSE API
# =========================

# GET warehouses + product count
@app.route("/warehouses", methods=["GET"])
def get_warehouses():
    warehouses = warehouse_service.list_warehouses_with_products()
    return jsonify(warehouses)

# CREATE warehouse
@app.route("/warehouses", methods=["GET"])
def get_warehouses():
    warehouses = warehouse_service.list_warehouses()
    inventory = inventory_service.db.find_all("inventory")

    for w in warehouses:
        w["products"] = sum(
            item["menge"]
            for item in inventory
            if item["lager_id"] == w["id"]
        )

    return warehouses

# DELETE warehouse
@app.route("/warehouses/<lager_id>", methods=["DELETE"])
def delete_warehouse(lager_id):
    warehouse_service.delete_warehouse(lager_id)
    return "", 204


# =========================
# LAGERPRODUKT API (NEU!)
# =========================

# Produkt einem Lager zuweisen
@app.route("/lagerprodukte", methods=["POST"])
def add_product_to_warehouse():
    data = request.json

    warehouse_service.add_product_to_warehouse(
        lager_id=int(data["lager_id"]),
        produkt_id=int(data["produkt_id"]),
        menge=int(data["menge"])
    )

    return jsonify({"status": "ok"}), 201


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)