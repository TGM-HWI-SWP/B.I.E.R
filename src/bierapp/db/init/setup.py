"""Initialize the bierapp MongoDB database.

Creates the three collections defined in the DB diagram and applies indexes:

    produkte   – product catalogue
    lager      – warehouse registry
    inventar   – warehouse ↔ product stock levels (junction collection)

Run directly:

    python -m bierapp.db.init.setup

Or import and call :func:`setup_database` from application startup code.
"""

from os import environ
from sys import exit, stderr

import pymongo

COLLECTION_PRODUKTE = "produkte"
COLLECTION_LAGER = "lager"
COLLECTION_INVENTAR = "inventar"


def _build_uri() -> str:
    """Construct a MongoDB connection URI from environment variables.

    Returns:
        str: A fully qualified mongodb:// URI string.
    """
    user = environ.get("MONGO_USER", "admin")
    password = environ.get("MONGO_PASS", "secret")
    host = environ.get("MONGO_HOST", "localhost")
    port = int(environ.get("MONGO_PORT", 27017))
    return f"mongodb://{user}:{password}@{host}:{port}/"


def setup_database() -> None:
    """Connect to MongoDB and ensure all required collections and indexes exist.

    Creates the produkte, lager and inventar collections if they do not yet
    exist and applies appropriate indexes on each. This function is idempotent:
    running it multiple times produces no errors and no duplicate collections.
    """
    uri = _build_uri()
    db_name = environ.get("MONGO_DB", "bierapp")

    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5_000)
    db = client[db_name]

    existing = db.list_collection_names()

    if COLLECTION_PRODUKTE not in existing:
        db.create_collection(COLLECTION_PRODUKTE)
        print(f"[setup] Created collection '{COLLECTION_PRODUKTE}'.")

    db[COLLECTION_PRODUKTE].create_index("name", unique=False)
    print(f"[setup] Index on '{COLLECTION_PRODUKTE}.name' ensured.")


    if COLLECTION_LAGER not in existing:
        db.create_collection(COLLECTION_LAGER)
        print(f"[setup] Created collection '{COLLECTION_LAGER}'.")

    db[COLLECTION_LAGER].create_index("lagername", unique=True)
    print(f"[setup] Unique index on '{COLLECTION_LAGER}.lagername' ensured.")


    if COLLECTION_INVENTAR not in existing:
        db.create_collection(COLLECTION_INVENTAR)
        print(f"[setup] Created collection '{COLLECTION_INVENTAR}'.")

    db[COLLECTION_INVENTAR].create_index(
        [("lager_id", pymongo.ASCENDING), ("produkt_id", pymongo.ASCENDING)],
        unique=True,
        name="lager_produkt_unique",
    )
    print(
        f"[setup] Compound unique index on "
        f"'{COLLECTION_INVENTAR}.(lager_id, produkt_id)' ensured."
    )

    client.close()
    print("[setup] Database initialization complete.")


if __name__ == "__main__":
    try:
        setup_database()
    except Exception as exc:  # noqa: BLE001
        print(f"[setup] ERROR: {exc}", file=stderr)
        exit(1)
