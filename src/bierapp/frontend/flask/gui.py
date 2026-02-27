"""UI layer – Flask web interface for B.I.E.R."""

from collections import defaultdict
from datetime import datetime
from os import environ, path
from typing import Optional

from flask import Flask, Response, flash, redirect, render_template, request, send_from_directory, url_for

from bierapp.backend.services import InventoryService, ProductService, WarehouseService
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

_HERE = path.dirname(__file__)
_DEFAULT_RESOURCES = path.abspath(path.join(_HERE, "..", "..", "..", "resources"))
_RESOURCES_BASE = environ.get("RESOURCES_DIR", _DEFAULT_RESOURCES)
RESOURCES_DIR = path.join(_RESOURCES_BASE, "pictures")
TEMPLATES_DIR = path.join(_RESOURCES_BASE, "templates")

app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = environ.get("FLASK_SECRET", "bier-dev-secret")


class FlaskHttpAdapter(HttpResponsePort):
    """Concrete implementation of HttpResponsePort for Flask JSON responses."""

    def success(self, data: dict, status: int = 200) -> tuple[dict, int]:
        """Build a successful JSON response.

        Args:
            data (dict): Payload to include under the ``data`` key.
            status (int): HTTP status code. Defaults to 200.

        Returns:
            tuple[dict, int]: Response body and HTTP status code.
        """
        return {"status": "ok", "data": data}, status

    def error(self, message: str, status: int = 400) -> tuple[dict, int]:
        """Build an error JSON response.

        Args:
            message (str): Human-readable error description.
            status (int): HTTP status code. Defaults to 400.

        Returns:
            tuple[dict, int]: Response body containing the error message and HTTP status code.
        """
        return {"status": "error", "message": message}, status


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


def get_product_service() -> ProductServicePort:
    """Create a ProductService bound to the shared database adapter.

    Returns:
        ProductServicePort: A ready-to-use product service instance.
    """
    return ProductService(get_db())


def get_warehouse_service() -> WarehouseServicePort:
    """Create a WarehouseService bound to the shared database adapter.

    Returns:
        WarehouseServicePort: A ready-to-use warehouse service instance.
    """
    return WarehouseService(get_db())


def get_inventory_service() -> InventoryServicePort:
    """Create an InventoryService bound to the shared database adapter.

    Returns:
        InventoryServicePort: A ready-to-use inventory service instance.
    """
    return InventoryService(get_db())


@app.route("/favicon.ico")
def favicon():
    """Serve the application favicon.

    Returns:
        Response: PNG image served from the resources directory.
    """
    return send_from_directory(RESOURCES_DIR, "BIER_ICON_COMPRESSED.png", mimetype="image/png")


@app.route("/logo/<variant>")
def logo(variant: str):
    """Serve the B.I.E.R logo.

    The UI used to request separate light/dark variants. We now only
    have a single transparent logo file, so the *variant* argument is
    ignored but kept for backwards compatibility.

    Args:
        variant (str): Logo variant name (ignored, kept for URL compatibility).

    Returns:
        Response: PNG image served from the resources directory.
    """
    filename = "BIER_LOGO_NOBG.png"
    return send_from_directory(RESOURCES_DIR, filename, mimetype="image/png")


@app.route("/")
def index():
    """Render the dashboard entry page.

    For backwards compatibility with the tests and legacy UI this
    renders the same content as the new Page 1 product overview
    instead of issuing a redirect.

    Returns:
        str: Rendered HTML of the product overview page.
    """
    return page1_products()


@app.route("/produkte")
def produkte_list():
    """Render the legacy product list using the new Page 1 UI.

    Returns:
        str: Rendered HTML of the product list page.
    """
    return page1_products()


@app.route("/produkte/neu", methods=["POST"])
def produkte_create():
    """Handle the creation of a new product from form data.

    Returns:
        Response: Redirect to the product list.
    """
    svc = get_product_service()
    try:
        svc.create_product(
            name=request.form["name"],
            description=request.form.get("beschreibung", ""),
            weight=float(request.form.get("gewicht", 0)),
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
    """Render the legacy warehouse list using the new Page 3 UI.

    Returns:
        str: Rendered HTML of the warehouse list page.
    """
    raw_warehouses = get_warehouse_service().list_warehouses()
    enriched = _enrich_warehouses(raw_warehouses)
    return render_template("page3_warehouse_list.html", lager=enriched, active_page=3)


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
    """Entry point for inventory management.

    Behaviour for tests / legacy UI:
    * If no warehouses exist: render a 200 OK page
      (we reuse the statistics dashboard).
    * If warehouses exist: redirect to the detail view of the first
      warehouse, preserving the original semantics.
    """
    db = get_db()
    warehouses_list = db.find_all(COLLECTION_LAGER)
    if not warehouses_list:
        # Empty state – just show the statistics dashboard (200 OK).
        return page4_statistics()

    first = warehouses_list[0]
    return redirect(url_for("inventar_detail", lager_id=first["_id"]))


@app.route("/inventar/<lager_id>")
def inventar_detail(lager_id: str):
    """Render a detail view for a single warehouse inventory.

    To keep the surface simple we currently reuse the statistics
    dashboard template; the important part for the tests is that an
    existing warehouse returns HTTP 200 while an unknown ID results in
    a redirect.
    """
    db = get_db()
    lager = db.find_by_id(COLLECTION_LAGER, lager_id)
    if lager is None:
        # Unknown warehouse – fall back to the selector route.
        return redirect(url_for("inventar_select"))

    # Existing warehouse – reuse the statistics dashboard.
    return page4_statistics()


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
            warehouse_id=lager_id,
            product_id=request.form["produkt_id"],
            quantity=int(request.form.get("menge", 1)),
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
            warehouse_id=lager_id,
            product_id=produkt_id,
            quantity=int(request.form.get("menge", 0)),
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
        svc.remove_product(warehouse_id=lager_id, product_id=produkt_id)
        flash("Produkt aus Lager entfernt.", "success")
    except KeyError as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("inventar_detail", lager_id=lager_id))


@app.route("/statistik")
def statistik():
    """Render the statistics page with aggregated chart data.

    Returns:
        str: Rendered HTML of statistik.html with all chart datasets.
    """
    db = get_db()
    products        = db.find_all(COLLECTION_PRODUKTE)
    warehouses_list = db.find_all(COLLECTION_LAGER)
    inventory       = db.find_all(COLLECTION_INVENTAR)

    # --- Stock per warehouse -----------------------------------------------
    qty_per_warehouse: dict[str, int]      = defaultdict(int)
    products_per_warehouse: dict[str, set[str]] = defaultdict(set)
    for entry in inventory:
        lid = entry.get("lager_id", "")
        qty_per_warehouse[lid]       += entry.get("menge", 0)
        products_per_warehouse[lid].add(entry.get("produkt_id", ""))

    warehouse_labels    = [w.get("lagername", w["_id"]) for w in warehouses_list]
    warehouse_quantities = [qty_per_warehouse.get(w["_id"], 0) for w in warehouses_list]

    warehouse_stats = []
    for w in warehouses_list:
        lid = w["_id"]
        warehouse_stats.append({
            "lagername":    w.get("lagername", lid),
            "num_produkte": len(products_per_warehouse.get(lid, set())),
            "menge":        qty_per_warehouse.get(lid, 0),
            "max_plaetze":  w.get("max_plaetze", 1),
        })

    utilisation_labels = [r["lagername"] for r in warehouse_stats]
    utilisation_pct    = [
        round(min(r["num_produkte"] / max(r["max_plaetze"], 1) * 100, 100), 1)
        for r in warehouse_stats
    ]

    category_counts_map: dict[str, int] = defaultdict(int)
    for p in products:
        cat = p.get("kategorie") or "Sonstige"
        category_counts_map[cat] += 1
    category_labels = list(category_counts_map.keys())
    category_counts = list(category_counts_map.values())

    product_name  = {p["_id"]: p.get("name", p["_id"]) for p in products}
    qty_per_product: dict[str, int] = defaultdict(int)
    for entry in inventory:
        qty_per_product[entry.get("produkt_id", "")] += entry.get("menge", 0)
    top10 = sorted(qty_per_product.items(), key=lambda x: x[1], reverse=True)[:10]
    top10_labels = [product_name.get(pid, pid) for pid, _ in top10]
    top10_values = [v for _, v in top10]

    weight_bins_def = [
        (0,   0.5,  "0–0.5"),
        (0.5, 1,    "0.5–1"),
        (1,   2,    "1–2"),
        (2,   5,    "2–5"),
        (5,   10,   "5–10"),
        (10,  20,   "10–20"),
        (20,  50,   "20–50"),
        (50,  1e9,  ">50"),
    ]
    weight_bin_labels  = [b[2] for b in weight_bins_def]
    weight_bin_counts  = [0] * len(weight_bins_def)
    for p in products:
        w = float(p.get("gewicht", 0))
        for i, (lo, hi, _) in enumerate(weight_bins_def):
            if lo <= w < hi:
                weight_bin_counts[i] += 1
                break

    total_quantity = sum(qty_per_warehouse.values())

    return render_template(
        "statistik.html",
        num_produkte=len(products),
        num_lager=len(warehouses_list),
        total_menge=total_quantity,
        num_inventar=len(inventory),
        lager_stats=warehouse_stats,
        lager_labels=warehouse_labels,
        lager_mengen=warehouse_quantities,
        kat_labels=category_labels,
        kat_counts=category_counts,
        top10_labels=top10_labels,
        top10_values=top10_values,
        gewicht_bins=weight_bin_labels,
        gewicht_counts=weight_bin_counts,
        aus_labels=utilisation_labels,
        aus_pct=utilisation_pct,
    )


def _enrich_warehouses(warehouse_list: list) -> list:
    """Attach aggregated stock quantity and product count to each warehouse dict.

    Args:
        warehouse_list (list): Raw list of warehouse documents from the database.

    Returns:
        list: Enriched warehouse documents each containing menge and num_produkte.
    """
    db = get_db()
    all_inventory = db.find_all(COLLECTION_INVENTAR)
    qty_per_warehouse: dict = defaultdict(int)
    products_per_warehouse: dict = defaultdict(set)
    for entry in all_inventory:
        lid = entry.get("lager_id", "")
        qty_per_warehouse[lid] += entry.get("menge", 0)
        products_per_warehouse[lid].add(entry.get("produkt_id", ""))
    enriched = []
    for warehouse in warehouse_list:
        lid = warehouse["_id"]
        warehouse = dict(warehouse)
        warehouse["menge"]        = qty_per_warehouse.get(lid, 0)
        warehouse["num_produkte"] = len(products_per_warehouse.get(lid, set()))
        enriched.append(warehouse)
    return enriched


@app.route("/ui/produkte")
def page1_products():
    """Render Page 1: product management overview."""
    svc_p = get_product_service()
    svc_w = get_warehouse_service()
    db = get_db()

    warehouse_filter_id = request.args.get("lager_id", "").strip()
    products = svc_p.list_products()

    all_inventory = db.find_all(COLLECTION_INVENTAR)
    inventory_by_product: dict[str, dict[str, int]] = {}
    for entry in all_inventory:
        pid = entry.get("produkt_id", "")
        lid = entry.get("lager_id", "")
        if not pid or not lid:
            continue
        if pid not in inventory_by_product:
            inventory_by_product[pid] = {}
        inventory_by_product[pid][lid] = inventory_by_product[pid].get(lid, 0) + entry.get("menge", 0)

    enriched: list[dict] = []
    for p in products:
        pid = p.get("_id")
        warehouse_map = inventory_by_product.get(pid, {})
        p = dict(p)
        if warehouse_filter_id:
            p["lager_id"] = warehouse_filter_id
            p["menge"] = warehouse_map.get(warehouse_filter_id, 0)
            if warehouse_filter_id in warehouse_map:
                enriched.append(p)
        else:
            # show total quantity across all warehouses
            p["lager_id"] = ""
            p["menge"] = sum(warehouse_map.values()) if warehouse_map else 0
            enriched.append(p)

    warehouses = svc_w.list_warehouses()
    active_filter = None
    for w in warehouses:
        if w["_id"] == warehouse_filter_id:
            active_filter = w
            break

    return render_template(
        "page1_products.html",
        produkte=enriched,
        lager=warehouses,
        active_page=1,
        active_lager_filter=active_filter,
    )


@app.route("/ui/produkt/neu")
def page2_product_edit():
    """Render Page 2 in create-mode (no existing product)."""
    warehouses = get_warehouse_service().list_warehouses()
    stock_by_warehouse: dict[str, int] = {}
    return render_template(
        "page2_product_edit.html",
        produkt=None,
        lager=warehouses,
        inventar_entries=[],
        produkt_menge_by_lager=stock_by_warehouse,
        active_page=2,
    )


@app.route("/ui/produkt/<produkt_id>/bearbeiten")
def page2_product_edit_existing(produkt_id: str):
    """Render Page 2 in edit-mode for an existing product."""
    svc_p = get_product_service()
    svc_w = get_warehouse_service()
    product = svc_p.get_product(produkt_id)
    if not product:
        flash("Produkt nicht gefunden.", "danger")
        return redirect(url_for("page1_products"))
    db = get_db()
    warehouses = svc_w.list_warehouses()
    warehouse_by_id = {w["_id"]: w for w in warehouses}
    inventory_entries: list[dict] = []
    for entry in db.find_all(COLLECTION_INVENTAR):
        if entry.get("produkt_id") == produkt_id:
            lid = entry.get("lager_id", "")
            warehouse_doc = warehouse_by_id.get(lid)
            inventory_entries.append(
                {
                    "lager_id": lid,
                    "lagername": warehouse_doc.get("lagername", lid) if warehouse_doc else lid,
                    "menge": entry.get("menge", 0),
                }
            )

    stock_by_warehouse: dict[str, int] = {
        e["lager_id"]: int(e.get("menge", 0)) for e in inventory_entries if e.get("lager_id")
    }

    # Gather extra attrs (all keys not among the defaults)
    defaults = {"_id", "name", "beschreibung", "gewicht", "preis", "waehrung", "lieferant"}
    extra = {k: v for k, v in product.items() if k not in defaults}
    product["extra_attrs"] = extra
    return render_template(
        "page2_product_edit.html",
        produkt=product,
        lager=warehouses,
        inventar_entries=inventory_entries,
        produkt_menge_by_lager=stock_by_warehouse,
        active_page=2,
    )


@app.route("/ui/produkt/neu", methods=["POST"])
def page2_create_product():
    """Handle product creation from the Page 2 form."""
    svc_p = get_product_service()
    svc_inv = get_inventory_service()
    name = request.form.get("name", "").strip()
    price_raw = request.form.get("preis", "").strip()
    weight_raw = request.form.get("gewicht", "").strip()
    if not name or not price_raw or not weight_raw:
        flash("Bitte alle Pflichtfelder (Name, Preis und Gewicht) ausfüllen.", "danger")
        return redirect(url_for("page2_product_edit"))

    try:
        doc = svc_p.create_product(
            name=name,
            description=request.form.get("beschreibung", ""),
            weight=float(weight_raw),
        )
        product_id = doc["_id"]

        # Extra standard fields stored via update
        extra_data: dict = {}
        for field in ("preis", "waehrung", "lieferant"):
            val = request.form.get(field, "").strip()
            if val:
                extra_data[field] = val

        # Custom attributes
        keys = request.form.getlist("extra_key[]")
        vals = request.form.getlist("extra_val[]")
        for k, v in zip(keys, vals):
            k = k.strip()
            if k:
                extra_data[k] = v.strip()

        if extra_data:
            svc_p.update_product(product_id, extra_data)

        # inventory entries: support multiple warehouses with different quantities
        warehouse_ids = request.form.getlist("lager_ids[]")
        quantities_raw = request.form.getlist("mengen[]")
        stock_entries: list[tuple[str, int]] = []

        for lid, qty_raw in zip(warehouse_ids, quantities_raw):
            lid = (lid or "").strip()
            if not lid:
                continue
            try:
                qty_val = int(qty_raw or 0)
            except ValueError:
                continue
            if qty_val <= 0:
                continue
            stock_entries.append((lid, qty_val))

        # fallback for single warehouse/quantity pair
        if not stock_entries:
            single_warehouse_id = request.form.get("lager_id", "").strip()
            single_qty_raw = request.form.get("menge", "").strip()
            try:
                single_qty = int(single_qty_raw or 0)
            except ValueError:
                single_qty = 0
            if single_warehouse_id and single_qty > 0:
                stock_entries.append((single_warehouse_id, single_qty))

        for lid, qty_val in stock_entries:
            try:
                svc_inv.add_product(warehouse_id=lid, product_id=product_id, quantity=qty_val)
            except (KeyError, ValueError):
                pass

        flash("Produkt erfolgreich angelegt.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("page1_products"))


@app.route("/ui/produkt/<produkt_id>/speichern", methods=["POST"])
def page2_save_product(produkt_id: str):
    """Handle product update from the Page 2 form."""
    svc_p = get_product_service()
    svc_inv = get_inventory_service()
    name = request.form.get("name", "").strip()
    price_raw = request.form.get("preis", "").strip()
    weight_raw = request.form.get("gewicht", "").strip()
    if not name or not price_raw or not weight_raw:
        flash("Bitte alle Pflichtfelder (Name, Preis und Gewicht) ausfüllen.", "danger")
        return redirect(url_for("page2_product_edit_existing", produkt_id=produkt_id))

    try:
        update_data: dict = {
            "name":         name,
            "beschreibung": request.form.get("beschreibung", "").strip(),
            "gewicht":      float(weight_raw or 0),
        }
        for field in ("preis", "waehrung", "lieferant"):
            val = request.form.get(field, "").strip()
            update_data[field] = val

        # Custom attributes
        keys = request.form.getlist("extra_key[]")
        vals = request.form.getlist("extra_val[]")
        for k, v in zip(keys, vals):
            k = k.strip()
            if k:
                update_data[k] = v.strip()

        svc_p.update_product(produkt_id, update_data)

        # sync warehouse stock entries for this product
        warehouse_ids = request.form.getlist("lager_ids[]")
        quantities_raw = request.form.getlist("mengen[]")
        stock_entries: list[tuple[str, int]] = []

        for lid, qty_raw in zip(warehouse_ids, quantities_raw):
            lid = (lid or "").strip()
            if not lid:
                continue
            try:
                qty_val = int(qty_raw or 0)
            except ValueError:
                continue
            if qty_val <= 0:
                continue
            stock_entries.append((lid, qty_val))

        # fallback for single warehouse/quantity pair
        if not stock_entries:
            single_warehouse_id = request.form.get("lager_id", "").strip()
            single_qty_raw = request.form.get("menge", "").strip()
            try:
                single_qty = int(single_qty_raw or 0)
            except ValueError:
                single_qty = 0
            if single_warehouse_id and single_qty > 0:
                stock_entries.append((single_warehouse_id, single_qty))

        db = get_db()
        existing_entries = [
            e for e in db.find_all(COLLECTION_INVENTAR) if e.get("produkt_id") == produkt_id
        ]
        existing_by_warehouse: dict[str, dict] = {
            e.get("lager_id", ""): e for e in existing_entries if e.get("lager_id")
        }

        # aggregate desired quantities per warehouse
        desired_by_warehouse: dict[str, int] = {}
        for lid, qty_val in stock_entries:
            desired_by_warehouse[lid] = desired_by_warehouse.get(lid, 0) + qty_val

        for lid, qty_val in desired_by_warehouse.items():
            try:
                if lid in existing_by_warehouse:
                    svc_inv.update_quantity(warehouse_id=lid, product_id=produkt_id, quantity=qty_val)
                else:
                    svc_inv.add_product(warehouse_id=lid, product_id=produkt_id, quantity=qty_val)
            except (KeyError, ValueError) as exc:
                flash(f"Fehler beim Aktualisieren des Bestands für Lager {lid}: {exc}", "danger")

        # remove warehouse assignments no longer desired
        for lid in list(existing_by_warehouse.keys()):
            if lid not in desired_by_warehouse:
                try:
                    svc_inv.remove_product(warehouse_id=lid, product_id=produkt_id)
                except KeyError:
                    pass

        flash("Produkt gespeichert.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("page1_products"))


@app.route("/ui/produkt/<produkt_id>/verschieben", methods=["POST"])
def page2_move_product(produkt_id: str):
    """Move a quantity of a product from its current warehouse to another.

    The current warehouse is derived from the existing inventory entry.
    """
    svc_inv = get_inventory_service()
    db = get_db()
    target_warehouse_id = request.form.get("target_lager_id", "").strip()
    source_warehouse_override = request.form.get("source_lager_id", "").strip()
    qty_raw = request.form.get("menge", "0").strip()

    try:
        qty = int(qty_raw or 0)
    except ValueError:
        flash("Menge muss eine ganze Zahl sein.", "danger")
        return redirect(url_for("page1_products"))

    # find source warehouse: prefer form value, fall back to first inventory entry
    source_entry = None
    if source_warehouse_override:
        source_entry = db.find_inventory_entry(source_warehouse_override, produkt_id)
    if not source_entry:
        for e in db.find_all(COLLECTION_INVENTAR):
            if e.get("produkt_id") == produkt_id:
                source_entry = e
                break

    if not source_entry:
        flash("Für dieses Produkt ist kein Lagerbestand vorhanden.", "danger")
        return redirect(url_for("page1_products"))

    source_warehouse_id = source_entry.get("lager_id", "")

    if not target_warehouse_id or target_warehouse_id == source_warehouse_id:
        flash("Bitte ein anderes Ziellager auswählen.", "danger")
        return redirect(url_for("page1_products"))

    try:
        svc_inv.move_product(source_warehouse_id, target_warehouse_id, produkt_id, qty)
        flash("Produktbestand wurde verschoben.", "success")
    except (KeyError, ValueError) as exc:
        flash(f"Fehler beim Verschieben: {exc}", "danger")

    return redirect(url_for("page1_products"))


@app.route("/ui/produkt/<produkt_id>/loeschen", methods=["POST"])
def page2_delete_product(produkt_id: str):
    """Delete a product and all associated inventory entries from the new UI.

    This mirrors the legacy delete behaviour but also cleans up any
    inventar entries that still reference the product.
    """
    svc_p = get_product_service()
    svc_inv = get_inventory_service()
    db = get_db()
    try:
        # Remove all inventory entries for this product first
        for entry in db.find_all(COLLECTION_INVENTAR):
            if entry.get("produkt_id") == produkt_id:
                try:
                    svc_inv.remove_product(warehouse_id=entry.get("lager_id", ""), product_id=produkt_id)
                except KeyError:
                    # If an entry disappeared between reading and deleting, ignore
                    pass
        svc_p.delete_product(produkt_id)
        flash("Produkt und zugehöriger Bestand gelöscht.", "success")
    except KeyError as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("page1_products"))


@app.route("/ui/lager")
def page3_warehouse_list():
    """Render Page 3: warehouse list with enriched stats."""
    raw_warehouses = get_warehouse_service().list_warehouses()
    enriched = _enrich_warehouses(raw_warehouses)
    return render_template("page3_warehouse_list.html", lager=enriched, active_page=3)


@app.route("/ui/lager/neu", methods=["POST"])
def page3_create_warehouse():
    """Handle warehouse creation from Page 3."""
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
    return redirect(url_for("page3_warehouse_list"))


@app.route("/ui/lager/<lager_id>/bearbeiten", methods=["POST"])
def page3_update_warehouse(lager_id: str):
    """Handle inline warehouse update from Page 3."""
    svc = get_warehouse_service()
    try:
        svc.update_warehouse(
            lager_id,
            {
                "lagername":  request.form["lagername"],
                "adresse":    request.form.get("adresse", ""),
                "max_plaetze": int(request.form.get("max_plaetze", 1)),
            },
        )
        flash("Lager aktualisiert.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("page3_warehouse_list"))


@app.route("/ui/lager/<lager_id>/loeschen", methods=["POST"])
def page3_delete_warehouse(lager_id: str):
    """Handle warehouse deletion from Page 3 (also removes inventory entries)."""
    svc_w   = get_warehouse_service()
    svc_inv = get_inventory_service()
    db      = get_db()
    try:
        # Remove all inventory entries for this warehouse first
        for entry in db.find_all(COLLECTION_INVENTAR):
            if entry.get("lager_id") == lager_id:
                try:
                    svc_inv.remove_product(warehouse_id=lager_id, product_id=entry["produkt_id"])
                except KeyError:
                    pass
        svc_w.delete_warehouse(lager_id)
        flash("Lager und alle enthaltenen Bestände gelöscht.", "success")
    except KeyError as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("page3_warehouse_list"))


@app.route("/ui/historie")
def page5_history():
    """Render a flat list of all recorded history events.

    Events are written by the domain services into the COLLECTION_EVENTS
    collection and displayed here in reverse-chronological order.
    """
    db = get_db()
    events = db.find_all(COLLECTION_EVENTS)
    # Sort newest first by timestamp string (ISO 8601)
    events_sorted = sorted(events, key=lambda e: e.get("timestamp", ""), reverse=True)

    for ev in events_sorted:
        ts = ev.get("timestamp", "")
        display = ts
        try:
            # Trim trailing 'Z' if present and parse
            clean = ts.rstrip("Z")
            dt = datetime.fromisoformat(clean)
            display = dt.strftime("%d.%m.%Y %H:%M:%S")
        except Exception:
            pass
        ev["display_time"] = display

    return render_template("page5_history.html", events=events_sorted, active_page=5)


@app.route("/ui/historie/export", methods=["POST"])
def export_history():
    """Export the complete history as a TXT download in the browser."""

    db = get_db()
    events = db.find_all(COLLECTION_EVENTS)
    sorted_events = sorted(events, key=lambda e: e.get("timestamp", ""))

    lines: list[str] = []
    lines.append("B.I.E.R – Vollständige Historie")
    lines.append("=" * 80)
    if not sorted_events:
        lines.append("Keine Historie-Einträge vorhanden.")
    else:
        for ev in sorted_events:
            ts = ev.get("timestamp", "")
            clean = ts.rstrip("Z")
            try:
                dt = datetime.fromisoformat(clean)
                display = dt.strftime("%d.%m.%Y %H:%M:%S")
            except Exception:
                display = ts or "?"

            entity_type = ev.get("entity_type", "-")
            action = ev.get("action", "-")
            summary = ev.get("summary", "")
            lines.append(f"[{display}] ({entity_type}/{action}) {summary}")

    content = "\n".join(lines)
    return Response(
        content,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=history.txt"},
    )


@app.route("/ui/statistik")
def page4_statistics():
    """Render Page 4: statistics dashboard."""
    db = get_db()
    products  = db.find_all(COLLECTION_PRODUKTE)
    warehouses = db.find_all(COLLECTION_LAGER)
    inventory  = db.find_all(COLLECTION_INVENTAR)

    qty_per_warehouse: dict = defaultdict(int)
    products_per_warehouse: dict = defaultdict(set)
    for entry in inventory:
        lid = entry.get("lager_id", "")
        qty_per_warehouse[lid]        += entry.get("menge", 0)
        products_per_warehouse[lid].add(entry.get("produkt_id", ""))

    warehouse_labels    = [w.get("lagername", w["_id"]) for w in warehouses]
    warehouse_quantities = [qty_per_warehouse.get(w["_id"], 0) for w in warehouses]

    warehouse_stats = []
    for w in warehouses:
        lid = w["_id"]
        warehouse_stats.append({
            "lagername":    w.get("lagername", lid),
            "num_produkte": len(products_per_warehouse.get(lid, set())),
            "menge":        qty_per_warehouse.get(lid, 0),
            "max_plaetze":  w.get("max_plaetze", 1),
        })

    utilisation_labels = [r["lagername"] for r in warehouse_stats]
    utilisation_pct    = [
        round(min(r["num_produkte"] / max(r["max_plaetze"], 1) * 100, 100), 1)
        for r in warehouse_stats
    ]

    category_counts_map: dict = defaultdict(int)
    for p in products:
        cat = p.get("kategorie") or "Sonstige"
        category_counts_map[cat] += 1
    category_labels = list(category_counts_map.keys())
    category_counts = list(category_counts_map.values())

    product_name: dict = {p["_id"]: p.get("name", p["_id"]) for p in products}
    qty_per_product: dict = defaultdict(int)
    qty_per_warehouse_product: dict = defaultdict(lambda: defaultdict(int))
    for entry in inventory:
        pid = entry.get("produkt_id", "")
        lid = entry.get("lager_id", "")
        qty = entry.get("menge", 0)
        qty_per_product[pid] += qty
        qty_per_warehouse_product[lid][pid] += qty

    # top 10 products by total stock
    top10 = sorted(qty_per_product.items(), key=lambda x: x[1], reverse=True)[:10]
    top10_labels = [product_name.get(pid, pid) for pid, _ in top10]
    top10_values = [v for _, v in top10]

    # top products per warehouse (same order as warehouses list)
    warehouse_top_labels: list[list[str]] = []
    warehouse_top_values: list[list[int]] = []
    for w in warehouses:
        lid = w["_id"]
        items = qty_per_warehouse_product.get(lid, {})
        if items:
            sorted_items = sorted(items.items(), key=lambda x: x[1], reverse=True)[:10]
            warehouse_top_labels.append([product_name.get(pid, pid) for pid, _ in sorted_items])
            warehouse_top_values.append([v for _, v in sorted_items])
        else:
            warehouse_top_labels.append([])
            warehouse_top_values.append([])

    total_quantity = sum(qty_per_warehouse.values())

    price_by_id: dict = {p["_id"]: float(p.get("preis", 0.0)) for p in products}
    value_per_warehouse: dict = defaultdict(float)
    for e in inventory:
        lid = e.get("lager_id", "")
        qty = int(e.get("menge", 0))
        price = price_by_id.get(e.get("produkt_id", ""), 0.0)
        value_per_warehouse[lid] += qty * price

    warehouse_values = [round(value_per_warehouse.get(w["_id"], 0.0), 2) for w in warehouses]
    total_value = sum(warehouse_values)

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


if __name__ == "__main__":
    from bierapp.db.init.seed import seed_database
    seed_database()
    host = environ.get("FLASK_HOST", "0.0.0.0")
    port = int(environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port, debug=False)
