"""UI layer – Flask web interface for B.I.E.R."""

from collections import defaultdict
from os import environ, path
from typing import Optional

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for

from bierapp.backend.services import InventoryService, ProductService, WarehouseService
from bierapp.db.mongodb import MongoDBAdapter, COLLECTION_INVENTAR, COLLECTION_LAGER, COLLECTION_PRODUKTE

_HERE = path.dirname(__file__)
_DEFAULT_RESOURCES = path.abspath(path.join(_HERE, "..", "..", "..", "resources"))
_RESOURCES_BASE = environ.get("RESOURCES_DIR", _DEFAULT_RESOURCES)
RESOURCES_DIR = path.join(_RESOURCES_BASE, "pictures")
TEMPLATES_DIR = path.join(_RESOURCES_BASE, "templates")

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
    """Redirect root to the new Page 1 dashboard."""
    return redirect(url_for("page1_products"))


@app.route("/produkte")
def produkte_list():
    """Redirect to the new product UI."""
    return redirect(url_for("page1_products"))


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
    """Redirect to the new warehouse UI."""
    return redirect(url_for("page3_warehouse_list"))


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
    """Redirect to the statistics page (new UI)."""
    return redirect(url_for("page4_statistics"))


@app.route("/inventar/<lager_id>")
def inventar_detail(lager_id: str):
    """Redirect to the statistics page (new UI)."""
    return redirect(url_for("page4_statistics"))


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


@app.route("/statistik")
def statistik():
    """Render the statistics page with aggregated chart data.

    Returns:
        str: Rendered HTML of statistik.html with all chart datasets.
    """
    db = get_db()
    produkte   = db.find_all(COLLECTION_PRODUKTE)
    lager_list = db.find_all(COLLECTION_LAGER)
    inventar   = db.find_all(COLLECTION_INVENTAR)

    # --- Bestand je Lager -------------------------------------------------
    menge_per_lager: dict[str, int]         = defaultdict(int)
    produkte_per_lager: dict[str, set[str]] = defaultdict(set)
    for entry in inventar:
        lid = entry.get("lager_id", "")
        menge_per_lager[lid]       += entry.get("menge", 0)
        produkte_per_lager[lid].add(entry.get("produkt_id", ""))

    lager_labels = [l.get("lagername", l["_id"]) for l in lager_list]
    lager_mengen = [menge_per_lager.get(l["_id"], 0) for l in lager_list]

    lager_stats = []
    for l in lager_list:
        lid = l["_id"]
        lager_stats.append({
            "lagername":   l.get("lagername", lid),
            "num_produkte": len(produkte_per_lager.get(lid, set())),
            "menge":        menge_per_lager.get(lid, 0),
            "max_plaetze":  l.get("max_plaetze", 1),
        })

    # --- Auslastung (%) ---------------------------------------------------
    aus_labels = [r["lagername"] for r in lager_stats]
    aus_pct    = [
        round(min(r["menge"] / max(r["max_plaetze"], 1) * 100, 100), 1)
        for r in lager_stats
    ]

    # --- Kategorieverteilung ----------------------------------------------
    kat_counts_map: dict[str, int] = defaultdict(int)
    for p in produkte:
        kat = p.get("kategorie") or "Sonstige"
        kat_counts_map[kat] += 1
    kat_labels = list(kat_counts_map.keys())
    kat_counts  = list(kat_counts_map.values())

    # --- Top 10 Produkte nach Gesamtbestand --------------------------------
    produkt_name  = {p["_id"]: p.get("name", p["_id"]) for p in produkte}
    menge_per_p: dict[str, int] = defaultdict(int)
    for entry in inventar:
        menge_per_p[entry.get("produkt_id", "")] += entry.get("menge", 0)
    top10 = sorted(menge_per_p.items(), key=lambda x: x[1], reverse=True)[:10]
    top10_labels = [produkt_name.get(pid, pid) for pid, _ in top10]
    top10_values = [v for _, v in top10]

    # --- Gewichtsverteilung (Histogramm) ----------------------------------
    bins = [
        (0,   0.5,  "0–0.5"),
        (0.5, 1,    "0.5–1"),
        (1,   2,    "1–2"),
        (2,   5,    "2–5"),
        (5,   10,   "5–10"),
        (10,  20,   "10–20"),
        (20,  50,   "20–50"),
        (50,  1e9,  ">50"),
    ]
    gewicht_bins   = [b[2] for b in bins]
    gewicht_counts = [0] * len(bins)
    for p in produkte:
        w = float(p.get("gewicht", 0))
        for i, (lo, hi, _) in enumerate(bins):
            if lo <= w < hi:
                gewicht_counts[i] += 1
                break

    total_menge = sum(menge_per_lager.values())

    return render_template(
        "statistik.html",
        num_produkte=len(produkte),
        num_lager=len(lager_list),
        total_menge=total_menge,
        num_inventar=len(inventar),
        lager_stats=lager_stats,
        lager_labels=lager_labels,
        lager_mengen=lager_mengen,
        kat_labels=kat_labels,
        kat_counts=kat_counts,
        top10_labels=top10_labels,
        top10_values=top10_values,
        gewicht_bins=gewicht_bins,
        gewicht_counts=gewicht_counts,
        aus_labels=aus_labels,
        aus_pct=aus_pct,
    )


# ──────────────────────────────────────────────────────────────────────────────
# NEW UI ROUTES  (4-page modern dashboard)
# ──────────────────────────────────────────────────────────────────────────────

# ── Helper: enrich warehouses with menge & num_produkte ───────────────────────
def _enrich_warehouses(lager_list):
    """Attach aggregated menge and num_produkte to each warehouse dict."""
    db = get_db()
    inventar_all = db.find_all(COLLECTION_INVENTAR)
    menge_per_lager: dict = defaultdict(int)
    produkte_per_lager: dict = defaultdict(set)
    for entry in inventar_all:
        lid = entry.get("lager_id", "")
        menge_per_lager[lid] += entry.get("menge", 0)
        produkte_per_lager[lid].add(entry.get("produkt_id", ""))
    enriched = []
    for l in lager_list:
        lid = l["_id"]
        l = dict(l)
        l["menge"]        = menge_per_lager.get(lid, 0)
        l["num_produkte"] = len(produkte_per_lager.get(lid, set()))
        enriched.append(l)
    return enriched


# PAGE 1 — Product list
@app.route("/ui/produkte")
def page1_products():
    """Render Page 1: product management overview."""
    svc = get_product_service()
    produkte = svc.list_products()
    return render_template("page1_products.html", produkte=produkte, active_page=1)


# PAGE 2 — Product edit (new)
@app.route("/ui/produkt/neu")
def page2_product_edit():
    """Render Page 2 in create-mode (no existing product)."""
    lager = get_warehouse_service().list_warehouses()
    return render_template("page2_product_edit.html", produkt=None, lager=lager, active_page=2)


# PAGE 2 — Product edit (existing)
@app.route("/ui/produkt/<produkt_id>/bearbeiten")
def page2_product_edit_existing(produkt_id: str):
    """Render Page 2 in edit-mode for an existing product."""
    svc_p = get_product_service()
    svc_w = get_warehouse_service()
    produkt = svc_p.get_product(produkt_id)
    if not produkt:
        flash("Produkt nicht gefunden.", "danger")
        return redirect(url_for("page1_products"))
    # Attach inventory data (menge, lager_id)
    db = get_db()
    for entry in db.find_all(COLLECTION_INVENTAR):
        if entry.get("produkt_id") == produkt_id:
            produkt.setdefault("menge",    entry.get("menge", 0))
            produkt.setdefault("lager_id", entry.get("lager_id", ""))
            break
    # Gather extra attrs (all keys not among the defaults)
    defaults = {"_id", "name", "beschreibung", "gewicht",
                "lager_id", "menge", "preis", "waehrung", "lieferant"}
    extra = {k: v for k, v in produkt.items() if k not in defaults}
    produkt["extra_attrs"] = extra
    lager = svc_w.list_warehouses()
    return render_template("page2_product_edit.html", produkt=produkt, lager=lager, active_page=2)


# PAGE 2 — Save (create)
@app.route("/ui/produkt/neu", methods=["POST"])
def page2_create_product():
    """Handle product creation from the Page 2 form."""
    svc_p = get_product_service()
    svc_inv = get_inventory_service()
    try:
        doc = svc_p.create_product(
            name=request.form["name"],
            beschreibung=request.form.get("beschreibung", ""),
            gewicht=float(request.form.get("gewicht", 0) or 0),
        )
        produkt_id = doc["_id"]

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
            svc_p.update_product(produkt_id, extra_data)

        # Inventory entry
        lager_id = request.form.get("lager_id", "").strip()
        menge = int(request.form.get("menge", 0) or 0)
        if lager_id and menge >= 0:
            try:
                svc_inv.add_product(lager_id=lager_id, produkt_id=produkt_id, menge=menge)
            except (KeyError, ValueError):
                pass  # lager may not exist; non-fatal

        flash("Produkt erfolgreich angelegt.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("page1_products"))


# PAGE 2 — Save (update)
@app.route("/ui/produkt/<produkt_id>/speichern", methods=["POST"])
def page2_save_product(produkt_id: str):
    """Handle product update from the Page 2 form."""
    svc_p = get_product_service()
    svc_inv = get_inventory_service()
    try:
        update_data: dict = {
            "name":         request.form.get("name", "").strip(),
            "beschreibung": request.form.get("beschreibung", "").strip(),
            "gewicht":      float(request.form.get("gewicht", 0) or 0),
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

        # Inventory: update or add
        lager_id = request.form.get("lager_id", "").strip()
        menge    = int(request.form.get("menge", 0) or 0)
        if lager_id:
            db = get_db()
            existing_entry = None
            for e in db.find_all(COLLECTION_INVENTAR):
                if e.get("produkt_id") == produkt_id:
                    existing_entry = e
                    break
            if existing_entry:
                try:
                    svc_inv.update_quantity(
                        lager_id=existing_entry["lager_id"],
                        produkt_id=produkt_id,
                        menge=menge,
                    )
                except KeyError:
                    pass
            else:
                try:
                    svc_inv.add_product(lager_id=lager_id, produkt_id=produkt_id, menge=menge)
                except (KeyError, ValueError):
                    pass

        flash("Produkt gespeichert.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("page1_products"))


# PAGE 3 — Warehouse list
@app.route("/ui/lager")
def page3_warehouse_list():
    """Render Page 3: warehouse list with enriched stats."""
    raw_lager = get_warehouse_service().list_warehouses()
    enriched = _enrich_warehouses(raw_lager)
    return render_template("page3_warehouse_list.html", lager=enriched, active_page=3)


# PAGE 3 — Create warehouse
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


# PAGE 3 — Update warehouse
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


# PAGE 3 — Delete warehouse
@app.route("/ui/lager/<lager_id>/loeschen", methods=["POST"])
def page3_delete_warehouse(lager_id: str):
    """Handle warehouse deletion from Page 3 (also removes inventar entries)."""
    svc_w   = get_warehouse_service()
    svc_inv = get_inventory_service()
    db      = get_db()
    try:
        # Remove all inventory entries for this warehouse first
        for entry in db.find_all(COLLECTION_INVENTAR):
            if entry.get("lager_id") == lager_id:
                try:
                    svc_inv.remove_product(lager_id=lager_id, produkt_id=entry["produkt_id"])
                except KeyError:
                    pass
        svc_w.delete_warehouse(lager_id)
        flash("Lager und alle enthaltenen Bestände gelöscht.", "success")
    except KeyError as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("page3_warehouse_list"))


# PAGE 4 — Statistics  (reuses existing statistik logic)
@app.route("/ui/statistik")
def page4_statistics():
    """Render Page 4: statistics dashboard."""
    db = get_db()
    produkte   = db.find_all(COLLECTION_PRODUKTE)
    lager_list = db.find_all(COLLECTION_LAGER)
    inventar   = db.find_all(COLLECTION_INVENTAR)

    menge_per_lager: dict = defaultdict(int)
    produkte_per_lager: dict = defaultdict(set)
    for entry in inventar:
        lid = entry.get("lager_id", "")
        menge_per_lager[lid]       += entry.get("menge", 0)
        produkte_per_lager[lid].add(entry.get("produkt_id", ""))

    lager_labels = [l.get("lagername", l["_id"]) for l in lager_list]
    lager_mengen = [menge_per_lager.get(l["_id"], 0) for l in lager_list]

    lager_stats = []
    for l in lager_list:
        lid = l["_id"]
        lager_stats.append({
            "lagername":    l.get("lagername", lid),
            "num_produkte": len(produkte_per_lager.get(lid, set())),
            "menge":        menge_per_lager.get(lid, 0),
            "max_plaetze":  l.get("max_plaetze", 1),
        })

    aus_labels = [r["lagername"] for r in lager_stats]
    aus_pct    = [
        round(min(r["menge"] / max(r["max_plaetze"], 1) * 100, 100), 1)
        for r in lager_stats
    ]

    kat_counts_map: dict = defaultdict(int)
    for p in produkte:
        kat = p.get("kategorie") or "Sonstige"
        kat_counts_map[kat] += 1
    kat_labels = list(kat_counts_map.keys())
    kat_counts = list(kat_counts_map.values())

    produkt_name: dict = {p["_id"]: p.get("name", p["_id"]) for p in produkte}
    menge_per_p: dict = defaultdict(int)
    for entry in inventar:
        menge_per_p[entry.get("produkt_id", "")] += entry.get("menge", 0)
    top10 = sorted(menge_per_p.items(), key=lambda x: x[1], reverse=True)[:10]
    top10_labels = [produkt_name.get(pid, pid) for pid, _ in top10]
    top10_values = [v for _, v in top10]

    total_menge = sum(menge_per_lager.values())

    return render_template(
        "page4_statistics.html",
        active_page=4,
        num_produkte=len(produkte),
        num_lager=len(lager_list),
        total_menge=total_menge,
        num_inventar=len(inventar),
        lager_stats=lager_stats,
        lager_labels=lager_labels,
        lager_mengen=lager_mengen,
        kat_labels=kat_labels,
        kat_counts=kat_counts,
        top10_labels=top10_labels,
        top10_values=top10_values,
        aus_labels=aus_labels,
        aus_pct=aus_pct,
    )


if __name__ == "__main__":
    from bierapp.db.init.seed import seed_database
    seed_database()
    host = environ.get("FLASK_HOST", "0.0.0.0")
    port = int(environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port, debug=False)
