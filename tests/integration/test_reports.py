from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from reports.report_a import ReportA
from reports.report_b import ReportB


class FakeDb:
    def __init__(self, history=None, products=None, warehouses=None):
        self._history = history or []
        self._products = products or []
        self._warehouses = warehouses or []

    def connect(self):
        return None

    def find_all(self, collection):
        if collection == "history":
            return list(self._history)
        if collection == "products":
            return list(self._products)
        if collection == "warehouses":
            return list(self._warehouses)
        return []

    def find_many_by_ids(self, collection, ids):
        ids_set = {str(i) for i in ids}
        if collection == "products":
            return [p for p in self._products if str(p.get("id")) in ids_set]
        return []


def test_report_a_inventory_report_handles_inbound_and_outbound_movements():
    db = FakeDb(
        history=[
            {
                "entry_type": "inventory",
                "action": "assign",
                "details": "produkt_id=10 lager_id=1 menge=5",
                "created_at": "2026-01-01T10:00:00",
            },
            {
                "entry_type": "inventory",
                "action": "book",
                "details": "produkt_id=10 source_lager=1 target_lager=2 menge=2",
                "created_at": "2026-01-01T11:00:00",
            },
        ],
        products=[{"id": "10", "name": "Pils"}],
        warehouses=[{"id": "1", "lagername": "A"}, {"id": "2", "lagername": "B"}],
    )

    report = ReportA(db)

    inventory = report.inventory_report("1")

    assert len(inventory) == 1
    assert inventory[0]["product_id"] == "10"
    assert inventory[0]["product_name"] == "Pils"
    assert inventory[0]["menge"] == 3.0


def test_report_a_statistics_report_aggregates_over_warehouses():
    db = FakeDb(
        history=[
            {
                "entry_type": "inventory",
                "action": "assign",
                "details": "produkt_id=10 lager_id=1 menge=5",
                "created_at": "2026-01-01T10:00:00",
            },
            {
                "entry_type": "inventory",
                "action": "assign",
                "details": "produkt_id=20 lager_id=2 menge=4",
                "created_at": "2026-01-01T11:00:00",
            },
        ],
        products=[{"id": "10", "name": "Pils"}, {"id": "20", "name": "Stout"}],
        warehouses=[{"id": "1", "lagername": "A"}, {"id": "2", "lagername": "B"}],
    )

    report = ReportA(db)

    stats = report.statistics_report()

    assert stats["total_products"] == 2
    assert stats["total_warehouses"] == 2
    assert stats["total_stock_units"] == 9.0


def test_report_b_inventory_report_fallback_without_report_a():
    db = FakeDb(
        history=[
            {
                "entry_type": "inventory",
                "action": "assign",
                "details": "produkt_id=7 lager_id=3 menge=8",
                "created_at": "2026-01-01T10:00:00",
            },
            {
                "entry_type": "inventory",
                "action": "book",
                "details": "produkt_id=7 source_lager=3 target_lager=4 menge=3",
                "created_at": "2026-01-01T12:00:00",
            },
        ],
        products=[{"id": "7", "name": "Weizen"}],
        warehouses=[{"id": "3", "lagername": "Nord"}, {"id": "4", "lagername": "Sued"}],
    )

    report = ReportB(db)
    report.report_a = None

    inventory = report.inventory_report("3")

    assert len(inventory) == 1
    assert inventory[0]["product_id"] == "7"
    assert inventory[0]["product_name"] == "Weizen"
    assert inventory[0]["menge"] == 5.0


def test_report_b_generate_report_returns_summary_on_empty_data(tmp_path, monkeypatch):
    class DummyPdf:
        def __init__(self, _):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    db = FakeDb(history=[], products=[], warehouses=[])
    report = ReportB(db)
    report.report_a = type(
        "DummyReportA",
        (),
        {
            "warehouses": {},
            "_movement_direction": staticmethod(lambda raw, qty: "Nicht angegeben"),
            "inventory_report": staticmethod(lambda lager_id: []),
        },
    )()

    from reports import report_b as report_b_module

    monkeypatch.setattr(report_b_module, "PdfPages", DummyPdf)
    monkeypatch.setattr(report_b_module, "create_cover_page", lambda *args, **kwargs: None)
    monkeypatch.setattr(report_b_module, "create_bar_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(report_b_module, "create_pie_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(report_b_module, "create_summary_page", lambda *args, **kwargs: None)

    output_path = tmp_path / "report_b_test.pdf"
    result = report.generate_report(output_path)

    assert result["output"] == str(output_path)
    assert result["summary"]["total_filtered"] == 0
    assert result["summary"]["top_count"] == 0
    assert result["summary"]["bottom_count"] == 0
