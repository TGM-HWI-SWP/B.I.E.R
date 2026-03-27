"""UI layer - Flask web interface"""

import os
from flask import Flask, send_from_directory, render_template, jsonify, request

from bierapp.backend import service
from bierapp.backend.service import (
    BierService,
    ProductService,
    WarehouseService
)
from bierapp.db.postgress import PostgresRepository
repo = PostgresRepository()
db = BierService(repo)

product_service = ProductService(db)
warehouse_service = WarehouseService(db)


RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "pictures"))
TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "templates"))

app = Flask(__name__, template_folder=TEMPLATES_DIR)

@app.route("/products", methods=["GET"])
def get_products():
    products = product_service.list_products()
    return jsonify(products)

@app.route("/products", methods=["POST"])
def create_product():
    data = request.json

    product = product_service.create_product(
        name=data["name"],
        beschreibung=data.get("beschreibung", ""),
        gewicht=float(data["gewicht"])
    )

    return jsonify(product), 201

@app.route("/warehouses", methods=["GET"])
def get_warehouses():
    warehouses = warehouse_service.list_warehouses()
    return jsonify(warehouses)

@app.route("/warehouses/with-products", methods=["GET"])
def get_warehouses_with_products():
    warehouses = warehouse_service.list_warehouses_with_products()
    return jsonify(warehouses)

@app.route("/warehouses", methods=["POST"])
def create_warehouse():
    data = request.json

    warehouse = warehouse_service.create_warehouse(
        lagername=data["lagername"],
        adresse=data["adresse"],
        max_plaetze=int(data["max_plaetze"]),
        firma_id=data["firma_id"]
    )

    return jsonify(warehouse), 201

@app.route("/lagerprodukte", methods=["POST"])
def add_product_to_warehouse():
    data = request.json

    lagerprodukt = warehouse_service.add_product_to_warehouse(
        lager_id=data["lager_id"],
        produkt_id=data["produkt_id"],
        menge=int(data["menge"])
    )

    return jsonify(lagerprodukt), 201

@app.route("/favicon.ico")
def favicon():
    """Serve the application favicon.

    Returns:
        Response: PNG image response for the browser favicon.
    """
    return send_from_directory(RESOURCES_DIR, "BIER_ICON_COMPRESSED.png", mimetype="image/png")

@app.route("/")
def index():
    """Render the main application page.

    Returns:
        str: Rendered HTML of ``index.html``.
    """
    return render_template("index.html")

@app.route("/page1")
def page1():
    """Render the second application page.

    Returns:
        str: Rendered HTML of ``page1.html``.
    """
    return render_template("page1.html")

@app.route("/page2")
def page2():
    """Render the third application page.

    Returns:
        str: Rendered HTML of ``page2.html``.
    """
    return render_template("page2.html")

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port)
