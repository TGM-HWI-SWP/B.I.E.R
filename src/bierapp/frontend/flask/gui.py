"""UI layer – Flask web interface for B.I.E.R.

This module wires together the Flask application, the database singleton,
and all route handlers. Route handlers are kept short by delegating complex
data computation to the helper functions in helpers.py.
"""

from datetime import datetime
from os import environ, path
from typing import Optional

from flask import Flask, Response, flash, redirect, render_template, request, send_from_directory, url_for

from bierapp.backend.inventory_service import InventoryService
from bierapp.backend.product_service import ProductService
from bierapp.backend.warehouse_service import WarehouseService
from bierapp.contracts import (
    DatabasePort,
    HttpResponsePort,
    InventoryServicePort,
    ProductServicePort,
    WarehouseServicePort,
)
from bierapp.db.mongodb import (
    COLLECTION_EVENTS,
    COLLECTION_INVENTAR,
    COLLECTION_LAGER,
    COLLECTION_PRODUKTE,
    MongoDBAdapter,
)
from bierapp.frontend.flask.helpers import (
    compute_category_counts,
    compute_top10_products,
    compute_utilisation,
    compute_warehouse_aggregates,
    compute_warehouse_stats,
    compute_warehouse_top_products,
    compute_warehouse_values,
    enrich_warehouses,
)
from bierapp.frontend.flask.http_adapter import FlaskHttpAdapter

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------

_HERE = path.dirname(__file__)
_DEFAULT_RESOURCES = path.abspath(path.join(_HERE, "..", "..", "..", "resources"))
_RESOURCES_BASE = environ.get("RESOURCES_DIR", _DEFAULT_RESOURCES)
RESOURCES_DIR = path.join(_RESOURCES_BASE, "pictures")
TEMPLATES_DIR = path.join(_RESOURCES_BASE, "templates")

app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = environ.get("FLASK_SECRET", "bier-dev-secret")

# ---------------------------------------------------------------------------
# Database singleton and service factories
# ---------------------------------------------------------------------------

_db: Optional[MongoDBAdapter] = None

def get_db() -> MongoDBAdapter:
    """Return the shared MongoDBAdapter, creating and connecting it on first call.

    Returns:
        A connected MongoDBAdapter instance.
    """
    global _db
    if _db is None:
        _db = MongoDBAdapter()
        _db.connect()
    return _db

def get_product_service() -> ProductServicePort:
    """Create a ProductService bound to the shared database adapter.

    Returns:
        A ready-to-use ProductService instance.
    """
    return ProductService(get_db())

def get_warehouse_service() -> WarehouseServicePort:
    """Create a WarehouseService bound to the shared database adapter.

    Returns:
        A ready-to-use WarehouseService instance.
    """
    return WarehouseService(get_db())

def get_inventory_service() -> InventoryServicePort:
    """Create an InventoryService bound to the shared database adapter.

    Returns:
        A ready-to-use InventoryService instance.
    """
    return InventoryService(get_db())

# ---------------------------------------------------------------------------
# Static file routes
# ---------------------------------------------------------------------------

@app.route("/favicon.ico")
def favicon():
    """Serve the application favicon."""
    return send_from_directory(RESOURCES_DIR, "BIER_ICON_COMPRESSED.png", mimetype="image/png")

@app.route("/logo")
def logo():
    """Serve the B.I.E.R logo image."""
    return send_from_directory(RESOURCES_DIR, "BIER_LOGO_NOBG.png", mimetype="image/png")

# ---------------------------------------------------------------------------
# Dashboard / index
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Render the main dashboard page (product overview)."""
    return page1_products()

# ---------------------------------------------------------------------------
# Inventory routes
# ---------------------------------------------------------------------------

@app.route("/inventar")
def inventar_select():
    """Redirect to the first warehouse''s inventory, or show the statistics page when empty."""
    db = get_db()
    warehouses_list = db.find_all(COLLECTION_LAGER)

    if not warehouses_list:
        # No warehouses exist – show an empty state via the statistics page
        return page4_statistics()

    first_warehouse = warehouses_list[0]
    return redirect(url_for("inventar_detail", lager_id=first_warehouse["_id"]))

@app.route("/inventar/<lager_id>")
def inventar_detail(lager_id: str):
    """Show the detail view for a single warehouse inventory.

    Args:
        lager_id: Unique warehouse identifier from the URL.
    """
    db = get_db()
    lager = db.find_by_id(COLLECTION_LAGER, lager_id)

    if lager is None:
        return redirect(url_for("inventar_select"))

    return page4_statistics()

@app.route("/inventar/<lager_id>/hinzufuegen", methods=["POST"])
def inventar_add(lager_id: str):
    """Add a product to a warehouse inventory.

    Args:
        lager_id: Unique warehouse identifier from the URL.
    """
    svc = get_inventory_service()
    product_id = request.form.get("produkt_id", "")
    quantity_raw = request.form.get("menge", "1")

    try:
        quantity = int(quantity_raw)
        svc.add_product(warehouse_id=lager_id, product_id=product_id, quantity=quantity)
        flash("Produkt dem Lager hinzugefügt.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("inventar_detail", lager_id=lager_id))

@app.route("/inventar/<lager_id>/<produkt_id>/aktualisieren", methods=["POST"])
def inventar_update(lager_id: str, produkt_id: str):
    """Update the quantity of a specific product in a warehouse.

    Args:
        lager_id: Unique warehouse identifier from the URL.
        produkt_id: Unique product identifier from the URL.
    """
    svc = get_inventory_service()
    quantity_raw = request.form.get("menge", "0")

    try:
        quantity = int(quantity_raw)
        svc.update_quantity(warehouse_id=lager_id, product_id=produkt_id, quantity=quantity)
        flash("Menge aktualisiert.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("inventar_detail", lager_id=lager_id))

@app.route("/inventar/<lager_id>/<produkt_id>/entfernen", methods=["POST"])
def inventar_remove(lager_id: str, produkt_id: str):
    """Remove a product from a warehouse inventory.

    Args:
        lager_id: Unique warehouse identifier from the URL.
        produkt_id: Unique product identifier from the URL.
    """
    svc = get_inventory_service()
    try:
        svc.remove_product(warehouse_id=lager_id, product_id=produkt_id)
        flash("Produkt aus Lager entfernt.", "success")
    except KeyError as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("inventar_detail", lager_id=lager_id))

# ---------------------------------------------------------------------------
# Page 1 – Product overview
# ---------------------------------------------------------------------------

@app.route("/ui/produkte")
def page1_products():
    """Render Page 1: product management overview.

    Supports an optional ?lager_id= query parameter to filter products
    by warehouse. When no filter is active, the total quantity across
    all warehouses is shown for each product.
    """
    svc_p = get_product_service()
    svc_w = get_warehouse_service()
    db = get_db()

    warehouse_filter_id = request.args.get("lager_id", "").strip()
    all_products = svc_p.list_products()
    all_inventory = db.find_all(COLLECTION_INVENTAR)

    # Build a lookup: product_id → {warehouse_id → quantity}
    inventory_by_product: dict = {}
    for entry in all_inventory:
        product_id = entry.get("produkt_id", "")
        warehouse_id = entry.get("lager_id", "")

        if not product_id or not warehouse_id:
            continue

        if product_id not in inventory_by_product:
            inventory_by_product[product_id] = {}

        existing_qty = inventory_by_product[product_id].get(warehouse_id, 0)
        new_qty = existing_qty + entry.get("menge", 0)
        inventory_by_product[product_id][warehouse_id] = new_qty

    enriched_products = []
    for product in all_products:
        product_id = product.get("_id")
        warehouse_map = inventory_by_product.get(product_id, {})
        product_copy = dict(product)

        if warehouse_filter_id:
            # Only include products that are stocked in the selected warehouse
            if warehouse_filter_id in warehouse_map:
                product_copy["lager_id"] = warehouse_filter_id
                product_copy["menge"] = warehouse_map.get(warehouse_filter_id, 0)
                enriched_products.append(product_copy)
        else:
            # Show total quantity across all warehouses
            product_copy["lager_id"] = ""
            total_quantity = sum(warehouse_map.values()) if warehouse_map else 0
            product_copy["menge"] = total_quantity
            enriched_products.append(product_copy)

    all_warehouses = svc_w.list_warehouses()

    # Find the active warehouse filter object (if any)
    active_filter = None
    for warehouse in all_warehouses:
        if warehouse["_id"] == warehouse_filter_id:
            active_filter = warehouse
            break

    return render_template(
        "page1_products.html",
        produkte=enriched_products,
        lager=all_warehouses,
        active_page=1,
        active_lager_filter=active_filter,
    )

# ---------------------------------------------------------------------------
# Page 2 – Product detail / create / edit
# ---------------------------------------------------------------------------

@app.route("/ui/produkt/neu")
def page2_product_edit():
    """Render Page 2 in create-mode (no existing product pre-loaded)."""
    warehouses = get_warehouse_service().list_warehouses()
    return render_template(
        "page2_product_edit.html",
        produkt=None,
        lager=warehouses,
        inventar_entries=[],
        produkt_menge_by_lager={},
        active_page=2,
    )

@app.route("/ui/produkt/<produkt_id>/bearbeiten")
def page2_product_edit_existing(produkt_id: str):
    """Render Page 2 in edit-mode for an existing product.

    Args:
        produkt_id: Unique product identifier from the URL.
    """
    svc_p = get_product_service()
    svc_w = get_warehouse_service()
    db = get_db()

    product = svc_p.get_product(produkt_id)
    if not product:
        flash("Produkt nicht gefunden.", "danger")
        return redirect(url_for("page1_products"))

    all_warehouses = svc_w.list_warehouses()
    warehouse_by_id = {}
    for warehouse in all_warehouses:
        warehouse_by_id[warehouse["_id"]] = warehouse

    # Collect inventory entries for this specific product
    inventory_entries = []
    all_inventory = db.find_all(COLLECTION_INVENTAR)
    for entry in all_inventory:
        if entry.get("produkt_id") != produkt_id:
            continue

        warehouse_id = entry.get("lager_id", "")
        warehouse_doc = warehouse_by_id.get(warehouse_id)

        if warehouse_doc:
            warehouse_name = warehouse_doc.get("lagername", warehouse_id)
        else:
            warehouse_name = warehouse_id

        inventory_entries.append({
            "lager_id": warehouse_id,
            "lagername": warehouse_name,
            "menge": entry.get("menge", 0),
        })

    # Build a quick lookup: warehouse_id → quantity
    stock_by_warehouse = {}
    for entry in inventory_entries:
        if entry.get("lager_id"):
            stock_by_warehouse[entry["lager_id"]] = int(entry.get("menge", 0))

    # Collect any non-standard product fields for display
    standard_fields = {"_id", "name", "beschreibung", "gewicht", "preis", "waehrung", "lieferant"}
    extra_attrs = {}
    for key, value in product.items():
        if key not in standard_fields:
            extra_attrs[key] = value
    product["extra_attrs"] = extra_attrs

    return render_template(
        "page2_product_edit.html",
        produkt=product,
        lager=all_warehouses,
        inventar_entries=inventory_entries,
        produkt_menge_by_lager=stock_by_warehouse,
        active_page=2,
    )

@app.route("/ui/produkt/neu", methods=["POST"])
def page2_create_product():
    """Handle product creation from the Page 2 create form."""
    svc_p = get_product_service()
    svc_inv = get_inventory_service()

    name = request.form.get("name", "").strip()
    price_raw = request.form.get("preis", "").strip()
    weight_raw = request.form.get("gewicht", "").strip()

    if not name or not price_raw or not weight_raw:
        flash("Bitte alle Pflichtfelder (Name, Preis und Gewicht) ausfüllen.", "danger")
        return redirect(url_for("page2_product_edit"))

    try:
        product_doc = svc_p.create_product(
            name=name,
            description=request.form.get("beschreibung", ""),
            weight=float(weight_raw),
        )
        product_id = product_doc["_id"]

        # Collect standard optional fields
        extra_data = {}
        for field in ("preis", "waehrung", "lieferant"):
            field_value = request.form.get(field, "").strip()
            if field_value:
                extra_data[field] = field_value

        # Collect any custom key-value attributes from the form
        custom_keys = request.form.getlist("extra_key[]")
        custom_vals = request.form.getlist("extra_val[]")
        for key, value in zip(custom_keys, custom_vals):
            key = key.strip()
            if key:
                extra_data[key] = value.strip()

        if extra_data:
            svc_p.update_product(product_id, extra_data)

        # Collect warehouse/quantity pairs (supports multi-warehouse form)
        stock_entries = _parse_stock_entries_from_form()
        for warehouse_id, quantity in stock_entries:
            try:
                svc_inv.add_product(
                    warehouse_id=warehouse_id,
                    product_id=product_id,
                    quantity=quantity,
                )
            except (KeyError, ValueError):
                pass  # Skip invalid entries silently

        flash("Produkt erfolgreich angelegt.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("page1_products"))

@app.route("/ui/produkt/<produkt_id>/speichern", methods=["POST"])
def page2_save_product(produkt_id: str):
    """Handle product update from the Page 2 edit form.

    Args:
        produkt_id: Unique product identifier from the URL.
    """
    svc_p = get_product_service()
    svc_inv = get_inventory_service()
    db = get_db()

    name = request.form.get("name", "").strip()
    price_raw = request.form.get("preis", "").strip()
    weight_raw = request.form.get("gewicht", "").strip()

    if not name or not price_raw or not weight_raw:
        flash("Bitte alle Pflichtfelder (Name, Preis und Gewicht) ausfüllen.", "danger")
        return redirect(url_for("page2_product_edit_existing", produkt_id=produkt_id))

    try:
        # Build the core update payload
        update_data = {
            "name": name,
            "beschreibung": request.form.get("beschreibung", "").strip(),
            "gewicht": float(weight_raw or 0),
        }

        # Include standard optional fields
        for field in ("preis", "waehrung", "lieferant"):
            update_data[field] = request.form.get(field, "").strip()

        # Include custom attributes
        custom_keys = request.form.getlist("extra_key[]")
        custom_vals = request.form.getlist("extra_val[]")
        for key, value in zip(custom_keys, custom_vals):
            key = key.strip()
            if key:
                update_data[key] = value.strip()

        svc_p.update_product(produkt_id, update_data)

        # Sync warehouse stock entries for this product
        desired_stock = _parse_stock_entries_from_form()

        # Aggregate desired quantities per warehouse (handles duplicate warehouse IDs)
        desired_by_warehouse = {}
        for warehouse_id, quantity in desired_stock:
            previous = desired_by_warehouse.get(warehouse_id, 0)
            desired_by_warehouse[warehouse_id] = previous + quantity

        # Find existing inventory entries for this product
        existing_entries = []
        for entry in db.find_all(COLLECTION_INVENTAR):
            if entry.get("produkt_id") == produkt_id:
                existing_entries.append(entry)

        existing_by_warehouse = {}
        for entry in existing_entries:
            warehouse_id = entry.get("lager_id", "")
            if warehouse_id:
                existing_by_warehouse[warehouse_id] = entry

        # Apply desired quantities: update or create entries
        for warehouse_id, quantity in desired_by_warehouse.items():
            try:
                if warehouse_id in existing_by_warehouse:
                    svc_inv.update_quantity(
                        warehouse_id=warehouse_id,
                        product_id=produkt_id,
                        quantity=quantity,
                    )
                else:
                    svc_inv.add_product(
                        warehouse_id=warehouse_id,
                        product_id=produkt_id,
                        quantity=quantity,
                    )
            except (KeyError, ValueError) as exc:
                flash(f"Fehler beim Aktualisieren des Bestands für Lager {warehouse_id}: {exc}", "danger")

        # Remove warehouse assignments that are no longer desired
        for warehouse_id in list(existing_by_warehouse.keys()):
            if warehouse_id not in desired_by_warehouse:
                try:
                    svc_inv.remove_product(
                        warehouse_id=warehouse_id,
                        product_id=produkt_id,
                    )
                except KeyError:
                    pass

        flash("Produkt gespeichert.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("page1_products"))

@app.route("/ui/produkt/<produkt_id>/verschieben", methods=["POST"])
def page2_move_product(produkt_id: str):
    """Move a quantity of a product from its current warehouse to another.

    Args:
        produkt_id: Unique product identifier from the URL.
    """
    svc_inv = get_inventory_service()
    db = get_db()

    target_warehouse_id = request.form.get("target_lager_id", "").strip()
    source_warehouse_override = request.form.get("source_lager_id", "").strip()
    quantity_raw = request.form.get("menge", "0").strip()

    try:
        quantity = int(quantity_raw or 0)
    except ValueError:
        flash("Menge muss eine ganze Zahl sein.", "danger")
        return redirect(url_for("page1_products"))

    # Determine source warehouse: prefer the explicit form value, fall back to the first entry
    source_entry = None
    if source_warehouse_override:
        source_entry = db.find_inventory_entry(source_warehouse_override, produkt_id)

    if not source_entry:
        # Look for any inventory entry for this product
        all_inventory = db.find_all(COLLECTION_INVENTAR)
        for entry in all_inventory:
            if entry.get("produkt_id") == produkt_id:
                source_entry = entry
                break

    if not source_entry:
        flash("Für dieses Produkt ist kein Lagerbestand vorhanden.", "danger")
        return redirect(url_for("page1_products"))

    source_warehouse_id = source_entry.get("lager_id", "")

    if not target_warehouse_id or target_warehouse_id == source_warehouse_id:
        flash("Bitte ein anderes Ziellager auswählen.", "danger")
        return redirect(url_for("page1_products"))

    try:
        svc_inv.move_product(source_warehouse_id, target_warehouse_id, produkt_id, quantity)
        flash("Produktbestand wurde verschoben.", "success")
    except (KeyError, ValueError) as exc:
        flash(f"Fehler beim Verschieben: {exc}", "danger")

    return redirect(url_for("page1_products"))

@app.route("/ui/produkt/<produkt_id>/loeschen", methods=["POST"])
def page2_delete_product(produkt_id: str):
    """Delete a product and remove all associated inventory entries.

    Args:
        produkt_id: Unique product identifier from the URL.
    """
    svc_p = get_product_service()
    svc_inv = get_inventory_service()
    db = get_db()

    try:
        # Remove all inventory entries for this product first
        all_inventory = db.find_all(COLLECTION_INVENTAR)
        for entry in all_inventory:
            if entry.get("produkt_id") != produkt_id:
                continue
            entry_warehouse_id = entry.get("lager_id", "")
            try:
                svc_inv.remove_product(warehouse_id=entry_warehouse_id, product_id=produkt_id)
            except KeyError:
                pass  # Entry may have been removed already

        # Delete the product itself
        svc_p.delete_product(produkt_id)
        flash("Produkt und zugehöriger Bestand gelöscht.", "success")
    except KeyError as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("page1_products"))

# ---------------------------------------------------------------------------
# Page 3 – Warehouse list
# ---------------------------------------------------------------------------

@app.route("/ui/lager")
def page3_warehouse_list():
    """Render Page 3: warehouse list with aggregated stock statistics."""
    raw_warehouses = get_warehouse_service().list_warehouses()
    all_inventory = get_db().find_all(COLLECTION_INVENTAR)
    enriched = enrich_warehouses(raw_warehouses, all_inventory)
    return render_template("page3_warehouse_list.html", lager=enriched, active_page=3)

@app.route("/ui/lager/neu", methods=["POST"])
def page3_create_warehouse():
    """Handle warehouse creation from Page 3."""
    svc = get_warehouse_service()
    warehouse_name = request.form.get("lagername", "")
    address = request.form.get("adresse", "")
    max_slots_raw = request.form.get("max_plaetze", "1")

    try:
        max_slots = int(max_slots_raw)
        svc.create_warehouse(
            warehouse_name=warehouse_name,
            address=address,
            max_slots=max_slots,
        )
        flash("Lager erfolgreich angelegt.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("page3_warehouse_list"))

@app.route("/ui/lager/<lager_id>/bearbeiten", methods=["POST"])
def page3_update_warehouse(lager_id: str):
    """Handle warehouse update from Page 3.

    Args:
        lager_id: Unique warehouse identifier from the URL.
    """
    svc = get_warehouse_service()
    warehouse_name = request.form.get("lagername", "")
    address = request.form.get("adresse", "")
    max_slots_raw = request.form.get("max_plaetze", "1")

    try:
        max_slots = int(max_slots_raw)
        update_data = {
            "lagername": warehouse_name,
            "adresse": address,
            "max_plaetze": max_slots,
        }
        svc.update_warehouse(lager_id, update_data)
        flash("Lager aktualisiert.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("page3_warehouse_list"))

@app.route("/ui/lager/<lager_id>/loeschen", methods=["POST"])
def page3_delete_warehouse(lager_id: str):
    """Handle warehouse deletion from Page 3.

    All inventory entries belonging to this warehouse are removed first.

    Args:
        lager_id: Unique warehouse identifier from the URL.
    """
    svc_w = get_warehouse_service()
    svc_inv = get_inventory_service()
    db = get_db()

    try:
        # Remove all inventory entries for this warehouse before deleting the warehouse
        all_inventory = db.find_all(COLLECTION_INVENTAR)
        for entry in all_inventory:
            if entry.get("lager_id") != lager_id:
                continue
            entry_product_id = entry.get("produkt_id", "")
            try:
                svc_inv.remove_product(warehouse_id=lager_id, product_id=entry_product_id)
            except KeyError:
                pass  # Entry may have been removed already

        svc_w.delete_warehouse(lager_id)
        flash("Lager und alle enthaltenen Bestände gelöscht.", "success")
    except KeyError as exc:
        flash(f"Fehler: {exc}", "danger")

    return redirect(url_for("page3_warehouse_list"))

# ---------------------------------------------------------------------------
# Page 4 – Statistics dashboard
# ---------------------------------------------------------------------------

@app.route("/ui/statistik")
def page4_statistics():
    """Render Page 4: statistics dashboard with charts and KPI cards."""
    db = get_db()
    products = db.find_all(COLLECTION_PRODUKTE)
    warehouses = db.find_all(COLLECTION_LAGER)
    inventory = db.find_all(COLLECTION_INVENTAR)

    # Use helper functions from helpers.py to perform all the complex computations
    (
        quantity_per_warehouse,
        products_per_warehouse,
        warehouse_labels,
        warehouse_quantities,
    ) = compute_warehouse_aggregates(warehouses, inventory)

    warehouse_stats = compute_warehouse_stats(
        warehouses, quantity_per_warehouse, products_per_warehouse
    )
    utilisation_labels, utilisation_pct = compute_utilisation(warehouse_stats)
    category_labels, category_counts = compute_category_counts(products)
    top10_labels, top10_values = compute_top10_products(products, inventory)
    warehouse_top_labels, warehouse_top_values = compute_warehouse_top_products(
        warehouses, products, inventory
    )
    warehouse_values, total_value = compute_warehouse_values(warehouses, products, inventory)

    total_quantity = sum(quantity_per_warehouse.values())

    return render_template(
        "page4_statistics.html",
        active_page=4,
        num_produkte=len(products),
        num_lager=len(warehouses),
        total_menge=total_quantity,
        total_value=total_value,
        num_inventar=len(inventory),
        lager_stats=warehouse_stats,
        lager_labels=warehouse_labels,
        lager_werte=warehouse_values,
        lager_mengen=warehouse_quantities,
        kat_labels=category_labels,
        kat_counts=category_counts,
        top10_labels=top10_labels,
        top10_values=top10_values,
        lager_top_labels=warehouse_top_labels,
        lager_top_values=warehouse_top_values,
        aus_labels=utilisation_labels,
        aus_pct=utilisation_pct,
    )

# ---------------------------------------------------------------------------
# Page 5 – History
# ---------------------------------------------------------------------------

@app.route("/ui/historie")
def page5_history():
    """Render Page 5: a reverse-chronological list of all recorded events."""
    db = get_db()
    all_events = db.find_all(COLLECTION_EVENTS)

    # Sort newest-first by ISO 8601 timestamp string
    events_sorted = sorted(all_events, key=lambda e: e.get("timestamp", ""), reverse=True)

    # Format timestamps for display
    for event in events_sorted:
        raw_timestamp = event.get("timestamp", "")
        display_time = _format_timestamp_for_display(raw_timestamp)
        event["display_time"] = display_time

    return render_template("page5_history.html", events=events_sorted, active_page=5)

@app.route("/ui/historie/export", methods=["POST"])
def export_history():
    """Export the complete event history as a downloadable text file."""
    db = get_db()
    all_events = db.find_all(COLLECTION_EVENTS)

    # Sort oldest-first for a chronological export
    sorted_events = sorted(all_events, key=lambda e: e.get("timestamp", ""))

    lines = []
    lines.append("B.I.E.R – Vollständige Historie")
    lines.append("=" * 80)

    if not sorted_events:
        lines.append("Keine Historie-Einträge vorhanden.")
    else:
        for event in sorted_events:
            raw_timestamp = event.get("timestamp", "")
            display_time = _format_timestamp_for_display(raw_timestamp)
            entity_type = event.get("entity_type", "-")
            action = event.get("action", "-")
            summary = event.get("summary", "")
            lines.append(f"[{display_time}] ({entity_type}/{action}) {summary}")

    content = "\n".join(lines)
    return Response(
        content,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=history.txt"},
    )

# ---------------------------------------------------------------------------
# Private helper functions
# ---------------------------------------------------------------------------

def _format_timestamp_for_display(timestamp: str) -> str:
    """Convert an ISO 8601 UTC timestamp to a human-readable German date/time string.

    Args:
        timestamp: ISO 8601 string, optionally ending with ''Z''.

    Returns:
        A string in the format ''DD.MM.YYYY HH:MM:SS'', or the original
        timestamp if parsing fails.
    """
    try:
        clean_timestamp = timestamp.rstrip("Z")
        parsed = datetime.fromisoformat(clean_timestamp)
        return parsed.strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        return timestamp or "?"

def _parse_stock_entries_from_form() -> list:
    """Read warehouse/quantity pairs from the current request form.

    Supports two form layouts:
    1. Multi-warehouse: repeated fields ''lager_ids[]'' and ''mengen[]''.
    2. Single-warehouse: single fields ''lager_id'' and ''menge''.

    Returns:
        A list of (warehouse_id, quantity) tuples with valid, positive quantities.
    """
    stock_entries = []

    # Try the multi-warehouse format first
    warehouse_ids = request.form.getlist("lager_ids[]")
    quantities_raw = request.form.getlist("mengen[]")

    for warehouse_id, quantity_raw in zip(warehouse_ids, quantities_raw):
        warehouse_id = (warehouse_id or "").strip()
        if not warehouse_id:
            continue
        try:
            quantity = int(quantity_raw or 0)
        except ValueError:
            continue
        if quantity <= 0:
            continue
        stock_entries.append((warehouse_id, quantity))

    if stock_entries:
        return stock_entries

    # Fall back to the single-warehouse format
    single_warehouse_id = request.form.get("lager_id", "").strip()
    single_quantity_raw = request.form.get("menge", "").strip()

    if single_warehouse_id:
        try:
            single_quantity = int(single_quantity_raw or 0)
        except ValueError:
            single_quantity = 0

        if single_quantity > 0:
            stock_entries.append((single_warehouse_id, single_quantity))

    return stock_entries

if __name__ == "__main__":
    from bierapp.db.init.seed import seed_database
    seed_database()
    host = environ.get("FLASK_HOST", "0.0.0.0")
    port = int(environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port, debug=False)
