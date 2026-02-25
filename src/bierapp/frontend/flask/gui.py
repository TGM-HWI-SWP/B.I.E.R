"""UI layer – Flask web interface for B.I.E.R."""

from os import environ, path
from typing import Optional

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for

from bierapp.backend.services import InventoryService, ProductService, WarehouseService
from bierapp.db.mongodb import MongoDBAdapter

_HERE = path.dirname(__file__)
RESOURCES_DIR = path.abspath(path.join(_HERE, "..", "..", "..", "resources", "pictures"))
TEMPLATES_DIR = path.abspath(path.join(_HERE, "..", "..", "..", "resources", "templates"))

app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = environ.get("FLASK_SECRET", "bier-dev-secret")

_db: Optional[MongoDBAdapter] = None


def get_db() -> MongoDBAdapter:
    """Return the lazily initialised, shared MongoDBAdapter singleton.

    Returns:
        MongoDBAdapter: A connected adapter instance.
    """
    global _db
    if _db is None:
        _db = MongoDBAdapter()
        _db.connect()
    return _db


def get_product_service() -> ProductService:
    """Create a ProductService bound to the shared database adapter.

    Returns:
        ProductService: A ready-to-use product service instance.
    """
    return ProductService(get_db())


def get_warehouse_service() -> WarehouseService:
    """Create a WarehouseService bound to the shared database adapter.

    Returns:
        WarehouseService: A ready-to-use warehouse service instance.
    """
    return WarehouseService(get_db())


def get_inventory_service() -> InventoryService:
    """Create an InventoryService bound to the shared database adapter.

    Returns:
        InventoryService: A ready-to-use inventory service instance.
    """
    return InventoryService(get_db())


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(RESOURCES_DIR, "BIER_ICON_COMPRESSED.png", mimetype="image/png")


@app.route("/")
def index():
    svc_p = get_product_service()
    svc_w = get_warehouse_service()
    produkte = svc_p.list_products()
    lager = svc_w.list_warehouses()

    # Total stock across all inventory entries
    db = get_db()
    from bierapp.db.mongodb import COLLECTION_INVENTAR
    inventar_all = db.find_all(COLLECTION_INVENTAR)
    total_menge = sum(e.get("menge", 0) for e in inventar_all)

    return render_template(
        "index.html",
        num_produkte=len(produkte),
        num_lager=len(lager),
        total_menge=total_menge,
        lager_list=lager,
    )


@app.route("/produkte")
def produkte_list():
    svc = get_product_service()
    return render_template("produkte.html", produkte=svc.list_products())


@app.route("/produkte/neu", methods=["POST"])
def produkte_create():
    svc = get_product_service()
    try:
        svc.create_product(
            name=request.form["name"],
            beschreibung=request.form.get("beschreibung", ""),
            gewicht=float(request.form.get("gewicht", 0)),
        )
        flash("Produkt erfolgreich angelegt.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("produkte_list"))


@app.route("/produkte/<produkt_id>/bearbeiten", methods=["POST"])
def produkte_update(produkt_id: str):
    """Handle a partial update of an existing product.

    Args:
        produkt_id (str): Unique product identifier taken from the URL.

    Returns:
        Response: Redirect to the product list.
    """
    svc = get_product_service()
    try:
        svc.update_product(
            produkt_id,
            {
                "name": request.form["name"],
                "beschreibung": request.form.get("beschreibung", ""),
                "gewicht": float(request.form.get("gewicht", 0)),
            },
        )
        flash("Produkt erfolgreich aktualisiert.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("produkte_list"))


@app.route("/produkte/<produkt_id>/loeschen", methods=["POST"])
def produkte_delete(produkt_id: str):
    """Handle the deletion of a product.

    Args:
        produkt_id (str): Unique product identifier taken from the URL.

    Returns:
        Response: Redirect to the product list.
    """
    svc = get_product_service()
    try:
        svc.delete_product(produkt_id)
        flash("Produkt gelöscht.", "success")
    except KeyError as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("produkte_list"))


@app.route("/lager")
def lager_list():
    """Render the warehouse overview page.

    Returns:
        str: Rendered HTML of lager.html.
    """
    return render_template("lager.html", lager=get_warehouse_service().list_warehouses())


@app.route("/lager/neu", methods=["POST"])
def lager_create():
    """Handle the creation of a new warehouse from form data.

    Returns:
        Response: Redirect to the warehouse list.
    """
    svc = get_warehouse_service()
    try:
        svc.create_warehouse(
            lagername=request.form["lagername"],
            adresse=request.form.get("adresse", ""),
            max_plaetze=int(request.form.get("max_plaetze", 1)),
        )
        flash("Lager erfolgreich angelegt.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("lager_list"))


@app.route("/lager/<lager_id>/bearbeiten", methods=["POST"])
def lager_update(lager_id: str):
    """Handle a partial update of an existing warehouse.

    Args:
        lager_id (str): Unique warehouse identifier taken from the URL.

    Returns:
        Response: Redirect to the warehouse list.
    """
    svc = get_warehouse_service()
    try:
        svc.update_warehouse(
            lager_id,
            {
                "lagername": request.form["lagername"],
                "adresse": request.form.get("adresse", ""),
                "max_plaetze": int(request.form.get("max_plaetze", 1)),
            },
        )
        flash("Lager erfolgreich aktualisiert.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("lager_list"))


@app.route("/lager/<lager_id>/loeschen", methods=["POST"])
def lager_delete(lager_id: str):
    """Handle the deletion of a warehouse.

    Args:
        lager_id (str): Unique warehouse identifier taken from the URL.

    Returns:
        Response: Redirect to the warehouse list.
    """
    svc = get_warehouse_service()
    try:
        svc.delete_warehouse(lager_id)
        flash("Lager gelöscht.", "success")
    except KeyError as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("lager_list"))


@app.route("/inventar")
def inventar_select():
    """Redirect to the first warehouse inventory, or show an empty state.

    Returns:
        Response: Redirect to inventar_detail of the first warehouse, or
            rendered HTML of inventar.html with empty context.
    """
    lager = get_warehouse_service().list_warehouses()
    if lager:
        return redirect(url_for("inventar_detail", lager_id=lager[0]["_id"]))
    return render_template("inventar.html", lager_list=[], inventar=[], selected_lager=None)


@app.route("/inventar/<lager_id>")
def inventar_detail(lager_id: str):
    """Render the inventory page for a specific warehouse.

    Args:
        lager_id (str): Unique warehouse identifier taken from the URL.

    Returns:
        str: Rendered HTML of inventar.html with enriched inventory data.
    """
    svc_inv = get_inventory_service()
    svc_w = get_warehouse_service()
    svc_p = get_product_service()
    try:
        inventar = svc_inv.list_inventory(lager_id)
    except KeyError:
        flash("Lager nicht gefunden.", "danger")
        return redirect(url_for("inventar_select"))

    lager_list = svc_w.list_warehouses()
    selected_lager = svc_w.get_warehouse(lager_id)
    produkte = svc_p.list_products()
    return render_template(
        "inventar.html",
        lager_list=lager_list,
        inventar=inventar,
        selected_lager=selected_lager,
        produkte=produkte,
    )


@app.route("/inventar/<lager_id>/hinzufuegen", methods=["POST"])
def inventar_add(lager_id: str):
    """Handle adding a product to a warehouse inventory.

    Args:
        lager_id (str): Unique warehouse identifier taken from the URL.

    Returns:
        Response: Redirect to inventar_detail for the same warehouse.
    """
    svc = get_inventory_service()
    try:
        svc.add_product(
            lager_id=lager_id,
            produkt_id=request.form["produkt_id"],
            menge=int(request.form.get("menge", 1)),
        )
        flash("Produkt dem Lager hinzugefügt.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("inventar_detail", lager_id=lager_id))


@app.route("/inventar/<lager_id>/<produkt_id>/aktualisieren", methods=["POST"])
def inventar_update(lager_id: str, produkt_id: str):
    """Handle updating the quantity of a product in a warehouse.

    Args:
        lager_id (str): Unique warehouse identifier taken from the URL.
        produkt_id (str): Unique product identifier taken from the URL.

    Returns:
        Response: Redirect to inventar_detail for the same warehouse.
    """
    svc = get_inventory_service()
    try:
        svc.update_quantity(
            lager_id=lager_id,
            produkt_id=produkt_id,
            menge=int(request.form.get("menge", 0)),
        )
        flash("Menge aktualisiert.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("inventar_detail", lager_id=lager_id))


@app.route("/inventar/<lager_id>/<produkt_id>/entfernen", methods=["POST"])
def inventar_remove(lager_id: str, produkt_id: str):
    """Handle removing a product from a warehouse inventory.

    Args:
        lager_id (str): Unique warehouse identifier taken from the URL.
        produkt_id (str): Unique product identifier taken from the URL.

    Returns:
        Response: Redirect to inventar_detail for the same warehouse.
    """
    svc = get_inventory_service()
    try:
        svc.remove_product(lager_id=lager_id, produkt_id=produkt_id)
        flash("Produkt aus Lager entfernt.", "success")
    except KeyError as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("inventar_detail", lager_id=lager_id))


if __name__ == "__main__":
    host = environ.get("FLASK_HOST", "0.0.0.0")
    port = int(environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port, debug=False)
