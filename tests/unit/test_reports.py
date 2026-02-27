"""Unit tests for report components.

These tests ensure that the two required reports (inventory report and
statistics report) are deterministic and testable based on the persisted
data, as required by the project specification.
"""

from typing import Dict, List

from bierapp.db.mongodb import (
    COLLECTION_INVENTAR,
    COLLECTION_LAGER,
    COLLECTION_PRODUKTE,
)
from bierapp.reports.inventory_report import InventoryReport
from bierapp.reports.statistics_report import StatisticsReport


class InMemoryDb:
    """Simple in-memory stub implementing the minimal MongoDBAdapter API used by reports."""

    def __init__(self) -> None:
        self._collections: Dict[str, List[Dict]] = {
            COLLECTION_PRODUKTE: [],
            COLLECTION_LAGER: [],
            COLLECTION_INVENTAR: [],
        }

    # Helper methods for tests
    def add_produkt(self, _id: str, name: str, beschreibung: str, gewicht: float) -> None:
        """Insert a product document into the in-memory store.

        Args:
            _id (str): Unique identifier for the product.
            name (str): Human-readable product name.
            beschreibung (str): Short description of the product.
            gewicht (float): Weight of the product in kilograms.
        """
        self._collections[COLLECTION_PRODUKTE].append(
            {"_id": _id, "name": name, "beschreibung": beschreibung, "gewicht": gewicht}
        )

    def add_lager(self, _id: str, lagername: str, max_plaetze: int) -> None:
        """Insert a warehouse document into the in-memory store.

        Args:
            _id (str): Unique identifier for the warehouse.
            lagername (str): Human-readable warehouse name.
            max_plaetze (int): Maximum number of storage slots.
        """
        self._collections[COLLECTION_LAGER].append(
            {"_id": _id, "lagername": lagername, "max_plaetze": max_plaetze}
        )

    def add_inventar(self, _id: str, lager_id: str, produkt_id: str, menge: int) -> None:
        """Insert an inventory entry into the in-memory store.

        Args:
            _id (str): Unique identifier for the inventory entry.
            lager_id (str): Warehouse identifier this entry belongs to.
            produkt_id (str): Product identifier this entry refers to.
            menge (int): Stocked quantity.
        """
        self._collections[COLLECTION_INVENTAR].append(
            {"_id": _id, "lager_id": lager_id, "produkt_id": produkt_id, "menge": menge}
        )

    # Methods used by the report components
    def find_by_id(self, collection: str, document_id: str) -> Dict | None:
        """Retrieve a single document by its ID from the in-memory store.

        Args:
            collection (str): Target collection name.
            document_id (str): Unique document identifier.

        Returns:
            Dict | None: Copy of the matching document, or None if not found.
        """
        for doc in self._collections.get(collection, []):
            if doc.get("_id") == document_id:
                return dict(doc)
        return None

    def find_all(self, collection: str) -> List[Dict]:
        """Return all documents from a collection.

        Args:
            collection (str): Target collection name.

        Returns:
            List[Dict]: List of all documents as copies.
        """
        return [dict(d) for d in self._collections.get(collection, [])]

    def find_inventory_by_warehouse(self, warehouse_id: str) -> List[Dict]:
        """Return all inventory entries belonging to a given warehouse.

        Args:
            warehouse_id (str): Unique warehouse identifier.

        Returns:
            List[Dict]: All inventory entries for the warehouse as copies.
        """
        return [
            dict(d)
            for d in self._collections[COLLECTION_INVENTAR]
            if d.get("lager_id") == warehouse_id
        ]


class TestInventoryReport:
    def test_inventory_report_returns_sorted_entries_for_warehouse(self) -> None:
        """inventory_report returns entries sorted by product name for a valid warehouse."""
        db = InMemoryDb()
        db.add_lager("L1", "Halle 1", 10)
        db.add_produkt("P1", "Apfel", "Frischer Apfel", 0.2)
        db.add_produkt("P2", "Banane", "Gelbe Banane", 0.25)
        db.add_inventar("I1", "L1", "P2", 5)
        db.add_inventar("I2", "L1", "P1", 3)

        report = InventoryReport(db)  # type: ignore[arg-type]
        rows = report.inventory_report("L1")

        assert len(rows) == 2
        # sorted by name: Apfel, then Banane
        assert [r["produkt_name"] for r in rows] == ["Apfel", "Banane"]
        assert rows[0]["menge"] == 3
        assert rows[1]["menge"] == 5

    def test_inventory_report_raises_for_unknown_lager(self) -> None:
        """inventory_report raises KeyError when the warehouse does not exist."""
        db = InMemoryDb()
        report = InventoryReport(db)  # type: ignore[arg-type]

        try:
            report.inventory_report("UNKNOWN")
        except KeyError:
            pass
        else:
            raise AssertionError("Expected KeyError for unknown warehouse")


class TestStatisticsReport:
    def test_statistics_report_computes_basic_kpis(self) -> None:
        """statistics_report returns correct aggregated KPIs for a simple dataset."""
        db = InMemoryDb()
        db.add_lager("L1", "Halle 1", 2)
        db.add_lager("L2", "Depot", 1)
        db.add_produkt("P1", "Apfel", "Frischer Apfel", 0.2)
        db.add_produkt("P2", "Banane", "Gelbe Banane", 0.25)
        db.add_inventar("I1", "L1", "P1", 3)
        db.add_inventar("I2", "L1", "P2", 1)
        db.add_inventar("I3", "L2", "P2", 2)

        report = StatisticsReport(db)  # type: ignore[arg-type]
        stats = report.statistics_report()

        assert stats["total_products"] == 2
        assert stats["total_warehouses"] == 2
        # total_units = 3 + 1 + 2
        assert stats["total_units"] == 6
        # total_weight = 3*0.2 + 1*0.25 + 2*0.25 = 0.6 + 0.25 + 0.5
        assert abs(stats["total_weight"] - 1.35) < 1e-9

        capacity_usage = stats["capacity_usage"]
        # L1: 2 distinct products with menge>0 -> 2 used slots out of max_plaetze=2
        assert abs(capacity_usage["Halle 1"] - 1.0) < 1e-9
        # L2: 1 product with menge>0 -> 1 used slot out of max_plaetze=1
        assert abs(capacity_usage["Depot"] - 1.0) < 1e-9
