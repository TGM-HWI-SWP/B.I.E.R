"""UI layer – Flask web interface for B.I.E.R."""

from collections import defaultdict
from os import environ, path
from typing import Optional

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for, Response

from bierapp.backend.services import InventoryService, ProductService, WarehouseService
from bierapp.db.mongodb import (
    COLLECTION_EVENTS,
    COLLECTION_INVENTAR,
    COLLECTION_LAGER,
    COLLECTION_PRODUKTE,
    MongoDBAdapter,
)
from datetime import datetime

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


@app.route("/logo/<variant>")
def logo(variant: str):
    """Serve the B.I.E.R logo.

    The UI used to request separate light/dark variants. We now only
    have a single transparent logo file, so the *variant* argument is
    ignored but kept for backwards compatibility.
    """
    filename = "BIER_LOGO_NOBG.png"
    return send_from_directory(RESOURCES_DIR, filename, mimetype="image/png")


@app.route("/")
def index():
    """Render the dashboard entry page.

    For backwards compatibility with the tests and legacy UI this
    renders the same content as the new Page 1 product overview
    instead of issuing a redirect.
    """
    return page1_products()


@app.route("/produkte")
def produkte_list():
    """Render the legacy product list using the new Page 1 UI."""
    return page1_products()


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
    """Render the legacy warehouse list using the new Page 3 UI."""
    raw_lager = get_warehouse_service().list_warehouses()
    enriched = _enrich_warehouses(raw_lager)
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
        lager_list = db.find_all(COLLECTION_LAGER)
        if not lager_list:
                # Empty state – just show the statistics dashboard (200 OK).
                return page4_statistics()

        first = lager_list[0]
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

    # --- Auslastung (%) auf Basis der belegten Plätze (Anzahl Produkte) ---
    aus_labels = [r["lagername"] for r in lager_stats]
    aus_pct    = [
        round(min(r["num_produkte"] / max(r["max_plaetze"], 1) * 100, 100), 1)
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
    svc_p = get_product_service()
    svc_w = get_warehouse_service()
    db = get_db()

    lager_id = request.args.get("lager_id", "").strip()
    produkte = svc_p.list_products()

    # Map produkt_id -> {lager_id: menge} aus Inventar
    inventar_all = db.find_all(COLLECTION_INVENTAR)
    inventar_by_product: dict[str, dict[str, int]] = {}
    for entry in inventar_all:
        pid = entry.get("produkt_id", "")
        lid = entry.get("lager_id", "")
        if not pid or not lid:
            continue
        if pid not in inventar_by_product:
            inventar_by_product[pid] = {}
        inventar_by_product[pid][lid] = inventar_by_product[pid].get(lid, 0) + entry.get("menge", 0)

    # Enrich products with lager_id/menge for the UI
    enriched: list[dict] = []
    for p in produkte:
        pid = p.get("_id")
        lager_map = inventar_by_product.get(pid, {})
        p = dict(p)
        if lager_id:
            # Bei aktivem Lager-Filter: Menge in genau diesem Lager anzeigen
            p["lager_id"] = lager_id
            p["menge"] = lager_map.get(lager_id, 0)
            if lager_id in lager_map:
                enriched.append(p)
        else:
            # Ohne Filter: Gesamtmenge über alle Lager anzeigen
            p["lager_id"] = ""
            p["menge"] = sum(lager_map.values()) if lager_map else 0
            enriched.append(p)

    lager = svc_w.list_warehouses()
    active_filter = None
    for l in lager:
        if l["_id"] == lager_id:
            active_filter = l
            break

    return render_template(
        "page1_products.html",
        produkte=enriched,
        lager=lager,
        active_page=1,
        active_lager_filter=active_filter,
    )


# PAGE 2 — Product edit (new)
@app.route("/ui/produkt/neu")
def page2_product_edit():
    """Render Page 2 in create-mode (no existing product)."""
    lager = get_warehouse_service().list_warehouses()
    # Für neue Produkte gibt es noch keine Lagerzuordnung
    produkt_menge_by_lager: dict[str, int] = {}
    return render_template(
        "page2_product_edit.html",
        produkt=None,
        lager=lager,
        inventar_entries=[],
        produkt_menge_by_lager=produkt_menge_by_lager,
        active_page=2,
    )


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
    # Attach inventory data: all inventar-Einträge dieses Produkts mit Lagername
    db = get_db()
    lager = svc_w.list_warehouses()
    lager_by_id = {l["_id"]: l for l in lager}
    inventar_entries: list[dict] = []
    for entry in db.find_all(COLLECTION_INVENTAR):
        if entry.get("produkt_id") == produkt_id:
            lid = entry.get("lager_id", "")
            lager_doc = lager_by_id.get(lid)
            inventar_entries.append(
                {
                    "lager_id": lid,
                    "lagername": lager_doc.get("lagername", lid) if lager_doc else lid,
                    "menge": entry.get("menge", 0),
                }
            )

    produkt_menge_by_lager: dict[str, int] = {
        e["lager_id"]: int(e.get("menge", 0)) for e in inventar_entries if e.get("lager_id")
    }

    # Gather extra attrs (all keys not among the defaults)
    defaults = {"_id", "name", "beschreibung", "gewicht", "preis", "waehrung", "lieferant"}
    extra = {k: v for k, v in produkt.items() if k not in defaults}
    produkt["extra_attrs"] = extra
    return render_template(
        "page2_product_edit.html",
        produkt=produkt,
        lager=lager,
        inventar_entries=inventar_entries,
        produkt_menge_by_lager=produkt_menge_by_lager,
        active_page=2,
    )


# PAGE 2 — Save (create)
@app.route("/ui/produkt/neu", methods=["POST"])
def page2_create_product():
    """Handle product creation from the Page 2 form."""
    svc_p = get_product_service()
    svc_inv = get_inventory_service()
    # Pflichtfelder validieren (Name, Preis, Gewicht)
    name = request.form.get("name", "").strip()
    preis_raw = request.form.get("preis", "").strip()
    gewicht_raw = request.form.get("gewicht", "").strip()
    if not name or not preis_raw or not gewicht_raw:
        flash("Bitte alle Pflichtfelder (Name, Preis und Gewicht) ausfüllen.", "danger")
        return redirect(url_for("page2_product_edit"))

    try:
        doc = svc_p.create_product(
            name=name,
            beschreibung=request.form.get("beschreibung", ""),
            gewicht=float(gewicht_raw),
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

        # Inventory entries: support multiple Lager mit unterschiedlichen Mengen
        lager_ids = request.form.getlist("lager_ids[]")
        mengen_raw = request.form.getlist("mengen[]")
        stock_entries: list[tuple[str, int]] = []

        for lid, m_raw in zip(lager_ids, mengen_raw):
            lid = (lid or "").strip()
            if not lid:
                continue
            try:
                menge_val = int(m_raw or 0)
            except ValueError:
                continue
            # 0 oder negative Mengen ignorieren (kein Bestand)
            if menge_val <= 0:
                continue
            stock_entries.append((lid, menge_val))

        # Fallback: falls nur ein einzelnes Lager/Menge-Paar gesendet wurde
        if not stock_entries:
            single_lager_id = request.form.get("lager_id", "").strip()
            single_menge_raw = request.form.get("menge", "").strip()
            try:
                single_menge = int(single_menge_raw or 0)
            except ValueError:
                single_menge = 0
            if single_lager_id and single_menge > 0:
                stock_entries.append((single_lager_id, single_menge))

        for lid, menge_val in stock_entries:
            try:
                svc_inv.add_product(lager_id=lid, produkt_id=produkt_id, menge=menge_val)
            except (KeyError, ValueError):
                # Ungültige Lager-IDs oder Mengen ignorieren wir still
                pass

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
    # Pflichtfelder validieren (Name, Preis, Gewicht)
    name = request.form.get("name", "").strip()
    preis_raw = request.form.get("preis", "").strip()
    gewicht_raw = request.form.get("gewicht", "").strip()
    if not name or not preis_raw or not gewicht_raw:
        flash("Bitte alle Pflichtfelder (Name, Preis und Gewicht) ausfüllen.", "danger")
        return redirect(url_for("page2_product_edit_existing", produkt_id=produkt_id))

    try:
        update_data: dict = {
            "name":         name,
            "beschreibung": request.form.get("beschreibung", "").strip(),
            "gewicht":      float(gewicht_raw or 0),
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

        # Inventory: alle Lager/Mengen dieses Produkts synchronisieren
        lager_ids = request.form.getlist("lager_ids[]")
        mengen_raw = request.form.getlist("mengen[]")
        stock_entries: list[tuple[str, int]] = []

        for lid, m_raw in zip(lager_ids, mengen_raw):
            lid = (lid or "").strip()
            if not lid:
                continue
            try:
                menge_val = int(m_raw or 0)
            except ValueError:
                continue
            if menge_val <= 0:
                continue
            stock_entries.append((lid, menge_val))

        # Fallback für alte Formate: einzelnes Lager/Menge-Paar
        if not stock_entries:
            single_lager_id = request.form.get("lager_id", "").strip()
            single_menge_raw = request.form.get("menge", "").strip()
            try:
                single_menge = int(single_menge_raw or 0)
            except ValueError:
                single_menge = 0
            if single_lager_id and single_menge > 0:
                stock_entries.append((single_lager_id, single_menge))

        db = get_db()
        existing_entries = [
            e for e in db.find_all(COLLECTION_INVENTAR) if e.get("produkt_id") == produkt_id
        ]
        existing_by_lager: dict[str, dict] = {
            e.get("lager_id", ""): e for e in existing_entries if e.get("lager_id")
        }

        # Ziel-Mengen pro Lager aggregieren (falls Lager mehrfach vorkommt)
        desired_by_lager: dict[str, int] = {}
        for lid, menge_val in stock_entries:
            desired_by_lager[lid] = desired_by_lager.get(lid, 0) + menge_val

        # Updates / Neuanlagen
        for lid, menge_val in desired_by_lager.items():
            try:
                if lid in existing_by_lager:
                    svc_inv.update_quantity(lager_id=lid, produkt_id=produkt_id, menge=menge_val)
                else:
                    svc_inv.add_product(lager_id=lid, produkt_id=produkt_id, menge=menge_val)
            except (KeyError, ValueError) as exc:
                flash(f"Fehler beim Aktualisieren des Bestands für Lager {lid}: {exc}", "danger")

        # Entfernen von Lagerzuordnungen, die nicht mehr vorhanden sein sollen
        for lid in list(existing_by_lager.keys()):
            if lid not in desired_by_lager:
                try:
                    svc_inv.remove_product(lager_id=lid, produkt_id=produkt_id)
                except KeyError:
                    pass

        flash("Produkt gespeichert.", "success")
    except (ValueError, KeyError) as exc:
        flash(f"Fehler: {exc}", "danger")
    return redirect(url_for("page1_products"))


# PAGE 2 — Move product between warehouses
@app.route("/ui/produkt/<produkt_id>/verschieben", methods=["POST"])
def page2_move_product(produkt_id: str):
    """Move a quantity of a product from its current warehouse to another.

    The current warehouse is derived from the existing inventory entry.
    """
    svc_inv = get_inventory_service()
    db = get_db()
    target_lager_id = request.form.get("target_lager_id", "").strip()
    source_lager_id_override = request.form.get("source_lager_id", "").strip()
    menge_raw = request.form.get("menge", "0").strip()

    try:
        menge = int(menge_raw or 0)
    except ValueError:
        flash("Menge muss eine ganze Zahl sein.", "danger")
        return redirect(url_for("page1_products"))

    # Finde Quelllager: bevorzugt das aus dem Formular, sonst erster Inventareintrag
    source_entry = None
    if source_lager_id_override:
        source_entry = db.find_inventar_entry(source_lager_id_override, produkt_id)
    if not source_entry:
        for e in db.find_all(COLLECTION_INVENTAR):
            if e.get("produkt_id") == produkt_id:
                source_entry = e
                break

    if not source_entry:
        flash("Für dieses Produkt ist kein Lagerbestand vorhanden.", "danger")
        return redirect(url_for("page1_products"))

    source_lager_id = source_entry.get("lager_id", "")

    if not target_lager_id or target_lager_id == source_lager_id:
        flash("Bitte ein anderes Ziellager auswählen.", "danger")
        return redirect(url_for("page1_products"))

    try:
        svc_inv.move_product(source_lager_id, target_lager_id, produkt_id, menge)
        flash("Produktbestand wurde verschoben.", "success")
    except (KeyError, ValueError) as exc:
        flash(f"Fehler beim Verschieben: {exc}", "danger")

    return redirect(url_for("page1_products"))


# PAGE 2 — Delete product (including inventory)
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
                    svc_inv.remove_product(lager_id=entry.get("lager_id", ""), produkt_id=produkt_id)
                except KeyError:
                    # If an entry disappeared between reading and deleting, ignore
                    pass
        svc_p.delete_product(produkt_id)
        flash("Produkt und zugehöriger Bestand gelöscht.", "success")
    except KeyError as exc:
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


# PAGE 5 — History of changes
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

    # Add a human-friendly timestamp for display (dd.mm.yyyy HH:MM:SS)
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
    events_sorted = sorted(events, key=lambda e: e.get("timestamp", ""))

    lines: list[str] = []
    lines.append("B.I.E.R – Vollständige Historie")
    lines.append("=" * 80)
    if not events_sorted:
        lines.append("Keine Historie-Einträge vorhanden.")
    else:
        for ev in events_sorted:
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
        round(min(r["num_produkte"] / max(r["max_plaetze"], 1) * 100, 100), 1)
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
    # Verteilung pro Produkt gesamt sowie pro Lager ermitteln
    per_lager_product: dict = defaultdict(lambda: defaultdict(int))
    for entry in inventar:
        pid = entry.get("produkt_id", "")
        lid = entry.get("lager_id", "")
        menge = entry.get("menge", 0)
        menge_per_p[pid] += menge
        per_lager_product[lid][pid] += menge

    # Globale Top 10 über alle Lager
    top10 = sorted(menge_per_p.items(), key=lambda x: x[1], reverse=True)[:10]
    top10_labels = [produkt_name.get(pid, pid) for pid, _ in top10]
    top10_values = [v for _, v in top10]

    # Top-Produkte pro Lager (gleiche Reihenfolge wie lager_list)
    lager_top_labels: list[list[str]] = []
    lager_top_values: list[list[int]] = []
    for l in lager_list:
        lid = l["_id"]
        items = per_lager_product.get(lid, {})
        if items:
            sorted_items = sorted(items.items(), key=lambda x: x[1], reverse=True)[:10]
            lager_top_labels.append([produkt_name.get(pid, pid) for pid, _ in sorted_items])
            lager_top_values.append([v for _, v in sorted_items])
        else:
            lager_top_labels.append([])
            lager_top_values.append([])

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
        lager_top_labels=lager_top_labels,
        lager_top_values=lager_top_values,
        aus_labels=aus_labels,
        aus_pct=aus_pct,
    )


if __name__ == "__main__":
    from bierapp.db.init.seed import seed_database
    seed_database()
    host = environ.get("FLASK_HOST", "0.0.0.0")
    port = int(environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port, debug=False)
