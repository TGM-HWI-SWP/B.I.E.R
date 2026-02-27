"""Inventory report component implementing the ReportPort contract.

This report generates a deterministic, testable stock report (Bestandsbericht)
for a given warehouse based on the persisted data in the MongoDB adapter.
The core method :meth:`inventory_report` returns structured data for tests,
while :meth:`write_inventory_report` writes a formatted text file to the
``output`` folder of the reports package.

When run directly (``python -m bierapp.reports.inventory_report``), a report
for the specified warehouse ID is written automatically.
"""

from pathlib import Path
from sys import argv
from typing import Dict, List

from bierapp.contracts import ReportPort
from bierapp.db.mongodb import (
    COLLECTION_INVENTAR,
    COLLECTION_LAGER,
    COLLECTION_PRODUKTE,
    MongoDBAdapter,
)


class InventoryReport(ReportPort):
    """Generate an inventory report for a single warehouse.

    The report returns a list of rows, each containing the product details and
    current quantity for that warehouse. No I/O side effects are performed so
    that the component remains deterministic and easily unit-testable.
    """

    def __init__(self, db: MongoDBAdapter) -> None:
        """Initialise the report with an already-connected MongoDBAdapter.

        Args:
            db (MongoDBAdapter): Connected database adapter used for data retrieval.
        """
        self._db = db

    def inventory_report(self, warehouse_id: str) -> List[Dict]:
        """Generate an inventory report for a single warehouse.

        Args:
            warehouse_id (str): Unique warehouse identifier.

        Returns:
            List[Dict]: Sorted list of inventory rows, each containing lager_id,
                lagername, produkt_id, produkt_name, produkt_beschreibung and menge.

        Raises:
            KeyError: If no warehouse with the given warehouse_id exists.
        """
        warehouse = self._db.find_by_id(COLLECTION_LAGER, warehouse_id)
        if not warehouse:
            raise KeyError(f"Lager '{warehouse_id}' nicht gefunden.")

        # Query all inventory entries for the warehouse
        entries = self._db.find_inventory_by_warehouse(warehouse_id)
        result: List[Dict] = []
        for entry in entries:
            product_id = entry.get("produkt_id", "")
            product = self._db.find_by_id(COLLECTION_PRODUKTE, product_id) or {}

            result.append(
                {
                    "lager_id": warehouse_id,
                    "lagername": warehouse.get("lagername", ""),
                    "produkt_id": product_id,
                    "produkt_name": product.get("name", "?"),
                    "produkt_beschreibung": product.get("beschreibung", ""),
                    "menge": int(entry.get("menge", 0)),
                }
            )

        # Sort deterministically by product name, then product_id
        result.sort(key=lambda row: (row["produkt_name"], row["produkt_id"]))
        return result

    # ------------------------------------------------------------------
    # Convenience API: write reports as files in the output folder
    # ------------------------------------------------------------------
    def write_inventory_report(self, warehouse_id: str) -> Path:
        """Write a formatted text report for a single warehouse.

        The file is saved in the ``output`` subdirectory of this package,
        e.g. ``.../bierapp/reports/output/inventory_L1.txt``.
        Returns the path to the generated file.
        """

        rows = self.inventory_report(warehouse_id)
        if not rows:
            warehouse_name = "(leer)"
        else:
            warehouse_name = rows[0].get("lagername", "") or "(unbenannt)"

        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"inventory_{warehouse_id}.txt"

        lines: List[str] = []
        lines.append(f"Bestandsreport für Lager {warehouse_name} (ID: {warehouse_id})")
        lines.append("=" * 72)
        if not rows:
            lines.append("Keine Produkte im Lager vorhanden.")
        else:
            header = f"{'Produkt':25} | {'Menge':>5} | Beschreibung"
            lines.append(header)
            lines.append("-" * len(header))
            for row in rows:
                name = str(row.get("produkt_name", "?"))[:25]
                menge = int(row.get("menge", 0))
                beschreibung = str(row.get("produkt_beschreibung", ""))
                lines.append(f"{name:25} | {menge:5d} | {beschreibung}")

        file_path.write_text("\n".join(lines), encoding="utf-8")
        return file_path

    def write_all_inventory_report(self) -> Path:
        """Write a combined report covering all warehouses in a single file.

        Each warehouse gets a section with the same table layout as the
        single-warehouse report. The file is named ``inventory_all.txt``
        and is stored in the ``output`` folder.
        """

        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / "inventory_all.txt"

        lines: List[str] = []
        lines.append("Globaler Bestandsreport über alle Lager")
        lines.append("=" * 72)

        warehouses_list = self._db.find_all(COLLECTION_LAGER)
        if not warehouses_list:
            lines.append("Keine Lager vorhanden.")
        else:
            for warehouse in warehouses_list:
                warehouse_id = warehouse.get("_id", "?")
                warehouse_name = warehouse.get("lagername", "") or "(unbenannt)"
                lines.append("")
                lines.append(f"Lager {warehouse_name} (ID: {warehouse_id})")
                lines.append("-" * 72)
                try:
                    rows = self.inventory_report(str(warehouse_id))
                except KeyError:
                    rows = []

                if not rows:
                    lines.append("  Keine Produkte im Lager vorhanden.")
                else:
                    header = f"  {'Produkt':25} | {'Menge':>5} | Beschreibung"
                    lines.append(header)
                    lines.append("  " + "-" * (len(header) - 2))
                    for row in rows:
                        name = str(row.get("produkt_name", "?"))[:25]
                        menge = int(row.get("menge", 0))
                        beschreibung = str(row.get("produkt_beschreibung", ""))
                        lines.append(f"  {name:25} | {menge:5d} | {beschreibung}")

        file_path.write_text("\n".join(lines), encoding="utf-8")
        return file_path

    def statistics_report(self) -> Dict:
        """Not used in this component.

        The statistics report is provided by a separate component. This method
        is implemented only to satisfy the ReportPort contract.
        """

        raise NotImplementedError("InventoryReport does not provide statistics_report().")


if __name__ == "__main__":  # pragma: no cover - simple CLI helper
    db = MongoDBAdapter()
    db.connect()
    report = InventoryReport(db)

    if len(argv) >= 2:
        warehouse_id_arg = argv[1]
        path = report.write_inventory_report(warehouse_id_arg)
        print(f"Inventory report for Lager {warehouse_id_arg} written to {path}")
    else:
        path = report.write_all_inventory_report()
        print(f"Global inventory report written to {path}")
