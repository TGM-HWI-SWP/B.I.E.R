"""Seed the bierapp MongoDB database with realistic test data.

Creates 5 test warehouses and 150 test products spread across categories,
then populates inventory entries across the warehouses with random quantities.

This script is idempotent by default: if products already exist, it exits
without making any changes unless force=True is passed.

Run directly:

    python -m bierapp.db.init.seed
    python -m bierapp.db.init.seed --force  # drop existing data first
"""

from __future__ import annotations

from os import environ
from random import choice, randint, sample, uniform

from bson import ObjectId
from pymongo import MongoClient

COLLECTION_PRODUKTE = "produkte"
COLLECTION_LAGER = "lager"
COLLECTION_INVENTAR = "inventar"

# ---------------------------------------------------------------------------
# Warehouse seed data
# ---------------------------------------------------------------------------

_LAGER_DATA = [
    {"lagername": "Hauptlager Wien",   "adresse": "Wiener Straße 1, 1010 Wien",          "max_plaetze": 500},
    {"lagername": "Nebenlager Graz",   "adresse": "Grazer Gasse 22, 8010 Graz",          "max_plaetze": 300},
    {"lagername": "Außenlager Linz",   "adresse": "Linzer Allee 7, 4020 Linz",           "max_plaetze": 200},
    {"lagername": "Kühlhaus Salzburg", "adresse": "Mozartplatz 3, 5020 Salzburg",        "max_plaetze": 150},
    {"lagername": "Depot Innsbruck",   "adresse": "Innsbrucker Ring 9, 6020 Innsbruck",  "max_plaetze": 180},
]

# ---------------------------------------------------------------------------
# Product generation – one function per category
# ---------------------------------------------------------------------------

def _make_product(name: str, category: str, weight: float, price: float) -> dict:
    """Build a single product document ready for insertion into MongoDB.

    Args:
        name: Human-readable display name.
        category: Category label stored on the product.
        weight: Weight in kilograms.
        price: Price in euros.

    Returns:
        A product document dictionary.
    """
    return {
        "name": name,
        "beschreibung": f"{name}. Ideal für den professionellen Einsatz. Kategorie: {category}.",
        "gewicht": weight,
        "preis": price,
        "waehrung": "EUR",
        "kategorie": category,
    }

def _generate_category_products(
    category: str,
    variants: list,
    weight_min: float,
    weight_max: float,
    price_min: float,
    price_max: float,
) -> list:
    """Generate one product document for each variant in a category.

    Args:
        category: Category label (e.g. "Monitor").
        variants: List of variant suffixes (e.g. ["27-Zoll", "4K UHD"]).
        weight_min: Minimum weight in kg.
        weight_max: Maximum weight in kg.
        price_min: Minimum price in euros.
        price_max: Maximum price in euros.

    Returns:
        A list of product documents, one per variant.
    """
    products = []
    for variant in variants:
        product_name = f"{category} {variant}"
        weight = round(uniform(weight_min, weight_max), 2)
        price = round(uniform(price_min, price_max), 2)
        product = _make_product(product_name, category, weight, price)
        products.append(product)
    return products

def _generate_chair_products() -> list:
    """Generate 10 office chair product variants."""
    variants = [
        "Ergonomisch", "Standard", "Executive", "Netz", "Kinder",
        "Rollstuhl", "Hocker", "Barhocker", "Gamer", "Sattelhocker",
    ]
    return _generate_category_products("Bürostuhl", variants, 3.0, 15.0, 80.0, 400.0)

def _generate_desk_products() -> list:
    """Generate 10 desk product variants."""
    variants = [
        "Höhenverstellbar", "Eck", "Klein", "XXL", "Glas",
        "Massivholz", "Industrie", "Stehpult", "Winkel", "Camping",
    ]
    return _generate_category_products("Schreibtisch", variants, 10.0, 60.0, 120.0, 800.0)

def _generate_monitor_products() -> list:
    """Generate 10 monitor product variants."""
    variants = [
        "24-Zoll", "27-Zoll", "32-Zoll", "4K UHD", "Curved",
        "IPS", "TN", "OLED", "Ultra-Wide", "Portable",
    ]
    return _generate_category_products("Monitor", variants, 2.0, 8.0, 90.0, 600.0)

def _generate_keyboard_products() -> list:
    """Generate 10 keyboard product variants."""
    variants = [
        "Mechanisch", "Membrane", "Wireless", "Ergonomisch", "Kompakt",
        "Slim", "Gaming", "Beleuchtet", "Bluetooth", "USB-C",
    ]
    return _generate_category_products("Tastatur", variants, 0.3, 1.5, 20.0, 180.0)

def _generate_mouse_products() -> list:
    """Generate 10 mouse product variants."""
    variants = [
        "Optisch", "Laser", "Vertikal", "Gaming", "Trackball",
        "Wireless", "Ergonomisch", "Silent", "Kabellos", "Reise",
    ]
    return _generate_category_products("Maus", variants, 0.05, 0.3, 10.0, 120.0)

def _generate_printer_products() -> list:
    """Generate 10 printer product variants."""
    variants = [
        "Laser", "Tintenstrahl", "Multifunktion", "Foto", "Label",
        "Thermodruck", "3D", "Großformat", "Netzwerk", "Mobil",
    ]
    return _generate_category_products("Drucker", variants, 3.0, 25.0, 150.0, 1200.0)

def _generate_cable_products() -> list:
    """Generate 10 cable and connector product variants."""
    variants = [
        "USB-C", "HDMI", "DisplayPort", "Ethernet", "Thunderbolt",
        "Verlängerung", "Adapter", "Spiralkabel", "Flachkabel", "Glasfaser",
    ]
    return _generate_category_products("Kabel", variants, 0.05, 0.5, 5.0, 40.0)

def _generate_lamp_products() -> list:
    """Generate 10 lamp product variants."""
    variants = [
        "LED-Schreibtisch", "Klemmleuchte", "Stehlampe", "Deckenspot",
        "Akku", "Solar", "UV", "Tageslicht", "Leseleuchte", "Nachtlicht",
    ]
    return _generate_category_products("Lampe", variants, 0.5, 5.0, 15.0, 200.0)

def _generate_shelf_products() -> list:
    """Generate 10 shelf product variants."""
    variants = [
        "Metall", "Holz", "Glas", "Winkelregal", "Schwing",
        "Würfel", "Archiv", "Lager", "Rollregal", "Hängeregal",
    ]
    return _generate_category_products("Regal", variants, 5.0, 40.0, 60.0, 500.0)

def _generate_packaging_products() -> list:
    """Generate 10 packaging product variants."""
    variants = [
        "Karton A4", "Karton A3", "Luftpolster", "Stretch", "Klebeband",
        "Etiketten", "Beutel", "Koffer", "Transportbox", "Palette",
    ]
    return _generate_category_products("Verpackung", variants, 0.1, 20.0, 2.0, 80.0)

def _generate_filler_products(count: int = 50) -> list:
    """Generate a number of miscellaneous accessory products with random names.

    Args:
        count: How many filler products to generate. Defaults to 50.

    Returns:
        A list of product documents.
    """
    adjectives = [
        "Premium", "Standard", "Economy", "Profi", "Classic",
        "Ultra", "Smart", "Kompakt", "Light", "Heavy-Duty",
    ]
    nouns = [
        "Halterung", "Aufbewahrung", "Ständer", "Ablage", "Organizer",
        "Box", "Schublade", "Haken", "Klemme", "Tablett",
    ]

    products = []
    for i in range(count):
        adjective = choice(adjectives)
        noun = choice(nouns)
        product_name = f"{adjective} {noun} #{i + 1}"
        weight = round(uniform(0.1, 10.0), 2)
        price = round(uniform(5.0, 120.0), 2)
        product = _make_product(product_name, "Zubehör", weight, price)
        products.append(product)

    return products

def _generate_all_products() -> list:
    """Generate the full product catalogue with 150 products across 10 categories.

    Returns:
        A list of 150 product documents ready for insertion into MongoDB.
    """
    products = []
    products.extend(_generate_chair_products())
    products.extend(_generate_desk_products())
    products.extend(_generate_monitor_products())
    products.extend(_generate_keyboard_products())
    products.extend(_generate_mouse_products())
    products.extend(_generate_printer_products())
    products.extend(_generate_cable_products())
    products.extend(_generate_lamp_products())
    products.extend(_generate_shelf_products())
    products.extend(_generate_packaging_products())
    products.extend(_generate_filler_products(50))
    return products

# ---------------------------------------------------------------------------
# Database connection helpers
# ---------------------------------------------------------------------------

def _build_connection_uri() -> str:
    """Build a MongoDB connection URI from environment variables.

    Reads MONGO_USER, MONGO_PASS, MONGO_HOST and MONGO_PORT. Falls back to
    safe local development defaults if any variable is not set.

    Returns:
        A complete mongodb:// URI string.
    """
    user = environ.get("MONGO_USER", "admin")
    password = environ.get("MONGO_PASS", "secret")
    host = environ.get("MONGO_HOST", "localhost")
    port = int(environ.get("MONGO_PORT", 27017))
    return f"mongodb://{user}:{password}@{host}:{port}/"

# ---------------------------------------------------------------------------
# Main seeding function
# ---------------------------------------------------------------------------

def seed_database(force: bool = False) -> None:
    """Populate MongoDB with test warehouses, products and inventory entries.

    This function is idempotent by default: if products already exist it does
    nothing unless force is True, in which case all existing data is dropped
    before the new seed data is inserted.

    Args:
        force: When True, drops all existing collections before seeding.
    """
    uri = _build_connection_uri()
    db_name = environ.get("MONGO_DB", "bierapp")
    client = MongoClient(uri, serverSelectionTimeoutMS=5_000)
    db = client[db_name]

    # Idempotency check – skip if data already exists
    existing_product_count = db[COLLECTION_PRODUKTE].count_documents({})
    if not force and existing_product_count > 0:
        print("[seed] Database already contains data – seed skipped.")
        print("[seed] Run with force=True to drop and re-seed.")
        return

    if force:
        db[COLLECTION_PRODUKTE].drop()
        db[COLLECTION_LAGER].drop()
        db[COLLECTION_INVENTAR].drop()
        print("[seed] Existing data deleted.")

    # Insert warehouses
    warehouse_ids: list = []
    for lager in _LAGER_DATA:
        warehouse_doc = {
            "lagername": lager["lagername"],
            "adresse": lager.get("adresse", ""),
            "max_plaetze": lager["max_plaetze"],
        }
        result = db[COLLECTION_LAGER].insert_one(warehouse_doc)
        warehouse_ids.append(result.inserted_id)
        print(f"[seed] Warehouse created: {lager['lagername']}")

    # Insert products
    all_products = _generate_all_products()
    result = db[COLLECTION_PRODUKTE].insert_many(all_products)
    product_ids = list(result.inserted_ids)
    print(f"[seed] {len(product_ids)} products created.")

    # Create inventory entries: each warehouse stocks 60–100% of all products
    inventory_docs = []
    for warehouse_id in warehouse_ids:
        # Determine how many products to stock in this warehouse (60–100%)
        min_count = int(len(product_ids) * 0.6)
        max_count = len(product_ids)
        subset_size = randint(min_count, max_count)
        chosen_product_ids = sample(product_ids, subset_size)

        for product_id in chosen_product_ids:
            inventory_entry = {
                "lager_id": str(warehouse_id),
                "produkt_id": str(product_id),
                "menge": randint(1, 500),
            }
            inventory_docs.append(inventory_entry)

    if inventory_docs:
        db[COLLECTION_INVENTAR].insert_many(inventory_docs)
        print(f"[seed] {len(inventory_docs)} inventory entries created.")

    client.close()
    print("[seed] Seed complete.")

if __name__ == "__main__":
    import sys
    should_force = "--force" in sys.argv
    seed_database(force=should_force)
