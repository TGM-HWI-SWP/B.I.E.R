"""Seed the bierapp MongoDB database with realistic test data.

Creates 5 test warehouses and 150 test products spread across categories,
then populates inventory entries across the warehouses with random quantities.

Run once at application startup (idempotent – skips if data already exists):

    python -m bierapp.db.init.seed

Or call :func:`seed_database` programmatically.
"""

from __future__ import annotations

import random
from os import environ

import pymongo
from bson import ObjectId

COLLECTION_PRODUKTE = "produkte"
COLLECTION_LAGER = "lager"
COLLECTION_INVENTAR = "inventar"

# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

_LAGER_DATA = [
    {"lagername": "Hauptlager Wien",      "adresse": "Wiener Straße 1, 1010 Wien",        "max_plaetze": 500},
    {"lagername": "Nebenlager Graz",      "adresse": "Grazer Gasse 22, 8010 Graz",        "max_plaetze": 300},
    {"lagername": "Außenlager Linz",      "adresse": "Linzer Allee 7, 4020 Linz",         "max_plaetze": 200},
    {"lagername": "Kühlhaus Salzburg",    "adresse": "Mozartplatz 3, 5020 Salzburg",      "max_plaetze": 150},
    {"lagername": "Depot Innsbruck",      "adername": "Innsbrucker Ring 9, 6020 Innsbruck", "max_plaetze": 180},
]

# 150 realistic products across 10 categories
_PRODUKTE_DATA: list[dict] = []

def _gen_products() -> list[dict]:
    categories = [
        # (category_prefix, items, weight_range_kg)
        ("Bürostuhl",    ["Ergonomisch", "Standard", "Executive", "Netz", "Kinder",
                          "Rollstuhl", "Hocker", "Barhocker", "Gamer", "Sattelhocker"],            (3.0, 15.0)),
        ("Schreibtisch", ["Höhenverstellbar", "Eck", "Klein", "XXL", "Glas",
                          "Massivholz", "Industrie", "Stehpult", "Winkel", "Camping"],             (10.0, 60.0)),
        ("Monitor",      ["24-Zoll", "27-Zoll", "32-Zoll", "4K UHD", "Curved",
                          "IPS", "TN", "OLED", "Ultra-Wide", "Portable"],                          (2.0, 8.0)),
        ("Tastatur",     ["Mechanisch", "Membrane", "Wireless", "Ergonomisch", "Kompakt",
                          "Slim", "Gaming", "Beleuchtet", "Bluetooth", "USB-C"],                   (0.3, 1.5)),
        ("Maus",         ["Optisch", "Laser", "Vertikal", "Gaming", "Trackball",
                          "Wireless", "Ergonomisch", "Silent", "Kabellos", "Reise"],               (0.05, 0.3)),
        ("Drucker",      ["Laser", "Tintenstrahl", "Multifunktion", "Foto", "Label",
                          "Thermodruck", "3D", "Großformat", "Netzwerk", "Mobil"],                 (3.0, 25.0)),
        ("Kabel",        ["USB-C", "HDMI", "DisplayPort", "Ethernet", "Thunderbolt",
                          "Verlängerung", "Adapter", "Spiralkabel", "Flachkabel", "Glasfaser"],    (0.05, 0.5)),
        ("Lampe",        ["LED-Schreibtisch", "Klemmleuchte", "Stehlampe", "Deckenspot",
                          "Akku", "Solar", "UV", "Tageslicht", "Leseleuchte", "Nachtlicht"],       (0.5, 5.0)),
        ("Regal",        ["Metall", "Holz", "Glas", "Winkelregal", "Schwing", "Würfel",
                          "Archiv", "Lager", "Rollregal", "Hängeregal"],                           (5.0, 40.0)),
        ("Verpackung",   ["Karton A4", "Karton A3", "Luftpolster", "Stretch", "Klebeband",
                          "Etiketten", "Beutel", "Koffer", "Transportbox", "Palette"],             (0.1, 20.0)),
    ]
    products = []
    for cat, variants, (wmin, wmax) in categories:
        for i, variant in enumerate(variants):
            products.append({
                "name": f"{cat} {variant}",
                "beschreibung": (
                    f"{cat} der Variante '{variant}'. Ideal für den professionellen Einsatz. "
                    f"Kategorie-Nr. {i+1:02d}."
                ),
                "gewicht": round(random.uniform(wmin, wmax), 2),
                "kategorie": cat,
            })
    # Add 50 extra filler products
    adjectives = ["Premium", "Standard", "Economy", "Profi", "Classic", "Ultra",
                  "Smart", "Kompakt", "Light", "Heavy-Duty"]
    nouns = ["Halterung", "Aufbewahrung", "Ständer", "Ablage", "Organizer",
             "Box", "Schublade", "Haken", "Klemme", "Tablett"]
    for i, (adj, noun) in enumerate([(random.choice(adjectives), random.choice(nouns)) for _ in range(50)]):
        products.append({
            "name": f"{adj} {noun} #{i+1}",
            "beschreibung": f"Universeller {noun} in Qualitätsstufe '{adj}'.",
            "gewicht": round(random.uniform(0.1, 10.0), 2),
            "kategorie": "Zubehör",
        })
    return products


def _build_uri() -> str:
    user = environ.get("MONGO_USER", "admin")
    password = environ.get("MONGO_PASS", "secret")
    host = environ.get("MONGO_HOST", "localhost")
    port = int(environ.get("MONGO_PORT", 27017))
    return f"mongodb://{user}:{password}@{host}:{port}/"


def seed_database(force: bool = False) -> None:
    """Populate MongoDB with test warehouses, products and inventory entries.

    This function is **idempotent** by default: if products already exist it
    does nothing unless *force* is True.

    Args:
        force (bool): Drop and re-seed even if data is already present.
    """
    uri = _build_uri()
    db_name = environ.get("MONGO_DB", "bierapp")
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5_000)
    db = client[db_name]

    # Idempotency check
    if not force and db[COLLECTION_PRODUKTE].count_documents({}) > 0:
        print("[seed] Datenbank enthält bereits Daten – Seed übersprungen. "
              "(Verwende force=True um neu zu befüllen.)")
        return

    if force:
        db[COLLECTION_PRODUKTE].drop()
        db[COLLECTION_LAGER].drop()
        db[COLLECTION_INVENTAR].drop()
        print("[seed] Bestehende Daten gelöscht.")

    # --- Lager ---
    lager_ids: list[ObjectId] = []
    for lager in _LAGER_DATA:
        lager_doc = {
            "lagername": lager["lagername"],
            "adresse": lager.get("adresse", lager.get("adername", "")),
            "max_plaetze": lager["max_plaetze"],
        }
        result = db[COLLECTION_LAGER].insert_one(lager_doc)
        lager_ids.append(result.inserted_id)
        print(f"[seed] Lager angelegt: {lager['lagername']}")

    # --- Produkte ---
    products = _gen_products()
    produkt_ids: list[ObjectId] = []
    produkt_docs = db[COLLECTION_PRODUKTE].insert_many(products)
    produkt_ids = list(produkt_docs.inserted_ids)
    print(f"[seed] {len(produkt_ids)} Produkte angelegt.")

    # --- Inventar ---
    # Every warehouse gets a random subset of products with random quantities
    inventar_docs = []
    for lager_id in lager_ids:
        # Each warehouse stocks 60–100 % of products
        subset_size = random.randint(int(len(produkt_ids) * 0.6), len(produkt_ids))
        chosen = random.sample(produkt_ids, subset_size)
        for pid in chosen:
            inventar_docs.append({
                "lager_id": str(lager_id),
                "produkt_id": str(pid),
                "menge": random.randint(1, 500),
            })

    if inventar_docs:
        db[COLLECTION_INVENTAR].insert_many(inventar_docs)
        print(f"[seed] {len(inventar_docs)} Inventar-Einträge angelegt.")

    client.close()
    print("[seed] Seed abgeschlossen.")


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    seed_database(force=force)
