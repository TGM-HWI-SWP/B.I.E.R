"""Pytest fixtures with in-memory service fakes for isolated test execution."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from typing import Any

import pytest
from flask import Flask

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from bierapp.frontend.flask.gui import register_routes


class FakeDb:
    def __init__(self) -> None:
        self.collections: dict[str, list[dict[str, Any]]] = {
            "products": [],
            "warehouses": [],
            "inventory": [],
            "history": [],
        }
        self._next_id = 1

    def insert(self, collection: str, data: dict[str, Any]) -> int:
        row = deepcopy(data)
        if "id" not in row:
            row["id"] = self._next_id
            self._next_id += 1
        self.collections.setdefault(collection, []).append(row)
        return int(row["id"])

    def find_all(self, collection: str) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self.collections.get(collection, [])]


class FakeProductService:
    def __init__(self, db: FakeDb) -> None:
        self.db = db

    def list_products(self):
        return self.db.find_all("products")

    def get_product(self, produkt_id: str):
        return next((item for item in self.db.collections["products"] if str(item["id"]) == str(produkt_id)), None)

    def create_product(self, name: str, beschreibung: str, gewicht: float, preis: float = 0.0, waehrung: str = "EUR", lieferant: str = "", einheit: str = "Stk", attributes=None):
        if gewicht <= 0:
            raise ValueError("gewicht must be positive")
        if preis < 0:
            raise ValueError("preis cannot be negative")
        row = {
            "name": name,
            "beschreibung": beschreibung,
            "gewicht": gewicht,
            "preis": preis,
            "waehrung": waehrung,
            "lieferant": lieferant,
            "einheit": einheit,
            "attributes": attributes or [],
        }
        row["id"] = self.db.insert("products", row)
        return deepcopy(row)

    def update_product(self, produkt_id: str, data: dict[str, Any]):
        product = self.get_product(produkt_id)
        if product is None:
            raise KeyError("Product not found")
        product.update(deepcopy(data))
        return deepcopy(product)

    def delete_product(self, produkt_id: str):
        before = len(self.db.collections["products"])
        self.db.collections["products"] = [item for item in self.db.collections["products"] if str(item["id"]) != str(produkt_id)]
        if len(self.db.collections["products"]) == before:
            raise KeyError("Product not found")


class FakeInventoryService:
    def __init__(self, db: FakeDb) -> None:
        self.db = db

    def _find(self, lager_id: int, produkt_id: int):
        for item in self.db.collections["inventory"]:
            if int(item["lager_id"]) == int(lager_id) and int(item["produkt_id"]) == int(produkt_id):
                return item
        return None

    def add_product(self, lager_id: int, produkt_id: int, menge: int):
        if menge <= 0:
            raise ValueError("menge must be positive")
        existing = self._find(lager_id, produkt_id)
        if existing:
            existing["menge"] = int(existing.get("menge", 0)) + int(menge)
            return
        self.db.insert("inventory", {"lager_id": int(lager_id), "produkt_id": int(produkt_id), "menge": int(menge)})

    def set_quantity(self, lager_id: int, produkt_id: int, menge: int):
        if menge < 0:
            raise ValueError("menge cannot be negative")
        existing = self._find(lager_id, produkt_id)
        if menge == 0:
            self.remove_product(lager_id, produkt_id)
            return
        if existing is None:
            self.db.insert("inventory", {"lager_id": int(lager_id), "produkt_id": int(produkt_id), "menge": int(menge)})
        else:
            existing["menge"] = int(menge)

    def remove_product(self, lager_id: int, produkt_id: int):
        before = len(self.db.collections["inventory"])
        self.db.collections["inventory"] = [
            item
            for item in self.db.collections["inventory"]
            if not (int(item["lager_id"]) == int(lager_id) and int(item["produkt_id"]) == int(produkt_id))
        ]
        if len(self.db.collections["inventory"]) == before:
            raise KeyError("Inventory entry not found")

    def list_inventory(self, lager_id: int):
        return [item for item in self.db.find_all("inventory") if int(item["lager_id"]) == int(lager_id)]


class FakeWarehouseService:
    def __init__(self, db: FakeDb, inventory_service: FakeInventoryService) -> None:
        self.db = db
        self.inventory_service = inventory_service

    def list_warehouses(self):
        return self.db.find_all("warehouses")

    def get_warehouse(self, warehouse_id: str):
        return next((item for item in self.db.collections["warehouses"] if str(item["id"]) == str(warehouse_id)), None)

    def create_warehouse(self, lagername: str, adresse: str, max_plaetze: int, firma_id: int):
        row = {
            "lagername": lagername,
            "adresse": adresse,
            "max_plaetze": int(max_plaetze),
            "firma_id": int(firma_id),
        }
        row["id"] = self.db.insert("warehouses", row)
        return deepcopy(row)

    def update_warehouse(self, lager_id: str, data: dict[str, Any]):
        warehouse = self.get_warehouse(lager_id)
        if warehouse is None:
            raise KeyError("Warehouse not found")
        warehouse.update(deepcopy(data))
        return deepcopy(warehouse)

    def delete_warehouse(self, lager_id: str):
        before = len(self.db.collections["warehouses"])
        self.db.collections["warehouses"] = [item for item in self.db.collections["warehouses"] if str(item["id"]) != str(lager_id)]
        if len(self.db.collections["warehouses"]) == before:
            raise KeyError("Warehouse not found")

    def add_product_to_warehouse(self, lager_id: int, produkt_id: int, menge: int):
        self.inventory_service.add_product(int(lager_id), int(produkt_id), int(menge))


@pytest.fixture
def services():
    db = FakeDb()
    product_service = FakeProductService(db)
    inventory_service = FakeInventoryService(db)
    warehouse_service = FakeWarehouseService(db, inventory_service)
    return {
        "db": db,
        "products": product_service,
        "inventory": inventory_service,
        "warehouses": warehouse_service,
    }


@pytest.fixture
def app_factory(services):
    app = Flask(__name__, template_folder="src/resources/templates")
    app.config["TESTING"] = True
    register_routes(app, services["products"], services["warehouses"], services["inventory"])
    return app


@pytest.fixture
def client(app_factory):
    return app_factory.test_client()

