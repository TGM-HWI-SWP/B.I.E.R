"""Statistics report component implementing the ReportPort contract.

This report computes aggregated KPIs (global statistics) across all
warehouses and products based on the persisted data.  The core method
``statistics_report`` returns a dictionary suitable for testing, while
``write_statistics_report`` writes a formatted text file to the
``output`` folder of the reports package.

When run directly (``python -m bierapp.reports.statistics_report``),
the statistics report is written to a text file automatically.
"""

from pathlib import Path
from typing import Dict, List

from bierapp.contracts import ReportPort
from bierapp.db.mongodb import (
    COLLECTION_INVENTAR,
    COLLECTION_LAGER,
    COLLECTION_PRODUKTE,
    MongoDBAdapter,
)


class StatisticsReport(ReportPort):
    """Calculate global statistics across all warehouses and products."""

    def __init__(self, db: MongoDBAdapter) -> None:
        """Initialise the report with an already-connected MongoDBAdapter.

        Args:
            db (MongoDBAdapter): Connected database adapter used for data retrieval.
        """
        self._db = db

    def inventory_report(self, warehouse_id: str) -> List[Dict]:
        """This component focuses on global statistics only.

        A dedicated InventoryReport component is responsible for
        inventory_report().
        """

        raise NotImplementedError("StatisticsReport does not provide inventory_report().")

    def statistics_report(self) -> Dict:
        """Compute aggregated KPIs across all warehouses and products.

        Returns:
            Dict: Dictionary containing total_products, total_warehouses,
                total_units, total_weight, total_value and capacity_usage
                per warehouse name.
        """
        # Load all domain data
        products = self._db.find_all(COLLECTION_PRODUKTE)
        warehouses = self._db.find_all(COLLECTION_LAGER)
        inventory = self._db.find_all(COLLECTION_INVENTAR)

        total_products = len(products)
        total_warehouses = len(warehouses)

        # Build lookup tables
        weight_by_id = {p["_id"]: float(p.get("gewicht", 0.0)) for p in products}
        price_by_id  = {p["_id"]: float(p.get("preis",   0.0)) for p in products}
        capacity_by_warehouse = {w["_id"]: int(w.get("max_plaetze", 0)) for w in warehouses}
        warehouse_name_by_id = {w["_id"]: w.get("lagername", "") for w in warehouses}

        total_units = 0
        total_weight = 0.0
        total_value = 0.0
        used_capacity_by_warehouse: Dict[str, int] = {lid: 0 for lid in capacity_by_warehouse}

        for entry in inventory:
            warehouse_id = entry.get("lager_id", "")
            product_id = entry.get("produkt_id", "")
            quantity = int(entry.get("menge", 0))

            total_units += quantity
            weight = weight_by_id.get(product_id, 0.0)
            total_weight += quantity * weight
            price = price_by_id.get(product_id, 0.0)
            total_value += quantity * price

            if warehouse_id in used_capacity_by_warehouse and quantity > 0:
                used_capacity_by_warehouse[warehouse_id] += 1

        # Capacity usage per warehouse
        capacity_usage_by_warehouse: Dict[str, float] = {}
        for warehouse_id, max_slots in capacity_by_warehouse.items():
            used_slots = used_capacity_by_warehouse.get(warehouse_id, 0)
            if max_slots > 0:
                capacity_usage_by_warehouse[warehouse_id] = used_slots / max_slots
            else:
                capacity_usage_by_warehouse[warehouse_id] = 0.0

        return {
            "total_products": total_products,
            "total_warehouses": total_warehouses,
            "total_units": total_units,
            "total_weight": total_weight,
            "total_value": total_value,
            "capacity_usage": {
                warehouse_name_by_id.get(warehouse_id, warehouse_id): usage
                for warehouse_id, usage in capacity_usage_by_warehouse.items()
            },
        }

    # ------------------------------------------------------------------
    # Convenience API: write the statistics report as a file in output/
    # ------------------------------------------------------------------
    def write_statistics_report(self) -> Path:
        """Write a textual overview of all KPIs to a file.

        The file is saved under ``output/statistics.txt`` in the reports
        package. Returns the path to the generated file.
        """

        stats = self.statistics_report()

        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / "statistics.txt"

        lines: List[str] = []
        lines.append("Globale Lagerstatistik")
        lines.append("=" * 72)
        lines.append(f"Gesamtzahl Produkte:   {int(stats['total_products'])}")
        lines.append(f"Gesamtzahl Lager:      {int(stats['total_warehouses'])}")
        lines.append(f"Gesamtbestand (Stk.):  {int(stats['total_units'])}")
        lines.append(f"Gesamtgewicht (kg):    {stats['total_weight']:.3f}")
        lines.append(f"Gesamtwert (€):        {stats['total_value']:.2f}")
        lines.append("")
        lines.append("Kapazitätsauslastung pro Lager:")
        capacity = stats.get("capacity_usage", {})
        if not capacity:
            lines.append("  (keine Lager vorhanden)")
        else:
            for name, usage in sorted(capacity.items()):
                percent = usage * 100.0
                lines.append(f"  - {name}: {percent:5.1f}% belegt")

        file_path.write_text("\n".join(lines), encoding="utf-8")
        return file_path


if __name__ == "__main__":  # pragma: no cover - simple CLI helper
    db = MongoDBAdapter()
    db.connect()
    report = StatisticsReport(db)
    path = report.write_statistics_report()
    print(f"Statistics report written to {path}")
