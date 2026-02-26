"""Inventory report component implementing the ReportPort contract.

This report generates a deterministic, testable Bestandsbericht (stock
report) for a given warehouse based on the persisted data in the MongoDB
adapter.  The core method :meth:`inventory_report` returns structured data
for tests, while :meth:`write_inventory_report` schreibt eine schön
formatierte Textdatei in den ``output``-Ordner des reports-Packages.

Wird dieses Modul direkt ausgeführt (``python -m bierapp.reports.inventory_report``),
so wird automatisch ein Report für die angegebene Lager-ID geschrieben.
"""

from pathlib import Path
from typing import Dict, List
import sys

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
        self._db = db

    def inventory_report(self, lager_id: str) -> List[Dict]:
        # Ensure the warehouse exists
        lager = self._db.find_by_id(COLLECTION_LAGER, lager_id)
        if not lager:
            raise KeyError(f"Lager '{lager_id}' nicht gefunden.")

        # Query all inventory entries for the warehouse
        entries = self._db.find_inventar_by_lager(lager_id)
        result: List[Dict] = []
        for entry in entries:
            produkt_id = entry.get("produkt_id", "")
            produkt = self._db.find_by_id(COLLECTION_PRODUKTE, produkt_id) or {}

            result.append(
                {
                    "lager_id": lager_id,
                    "lagername": lager.get("lagername", ""),
                    "produkt_id": produkt_id,
                    "produkt_name": produkt.get("name", "?"),
                    "produkt_beschreibung": produkt.get("beschreibung", ""),
                    "menge": int(entry.get("menge", 0)),
                }
            )

        # Sort deterministically by product name, then product_id
        result.sort(key=lambda row: (row["produkt_name"], row["produkt_id"]))
        return result

    # ------------------------------------------------------------------
    # Convenience API: Reports als Datei im output-Ordner ablegen
    # ------------------------------------------------------------------
    def write_inventory_report(self, lager_id: str) -> Path:
        """Erzeuge eine hübsch formatierte Textdatei für *ein* Lager.

        Die Datei wird im Unterordner ``output`` dieses Packages
        gespeichert, z.B. ``.../bierapp/reports/output/inventory_L1.txt``.
        Der Rückgabewert ist der Pfad zur erzeugten Datei.
        """

        rows = self.inventory_report(lager_id)
        if not rows:
            # inventory_report wirft bereits KeyError, falls das Lager
            # nicht existiert. Wenn es existiert, aber leer ist, bauen
            # wir trotzdem einen minimalen Report.
            lagername = "(leer)"
        else:
            lagername = rows[0].get("lagername", "") or "(unbenannt)"

        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"inventory_{lager_id}.txt"

        lines: List[str] = []
        lines.append(f"Bestandsreport für Lager {lagername} (ID: {lager_id})")
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
        """Erzeuge einen Gesamtreport über *alle* Lager in einer Datei.

        Es wird für jedes Lager ein Abschnitt mit derselben Tabelle wie im
        Einzel-Report erzeugt. Die Datei heißt ``inventory_all.txt`` und
        liegt im ``output``-Ordner.
        """

        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / "inventory_all.txt"

        lines: List[str] = []
        lines.append("Globaler Bestandsreport über alle Lager")
        lines.append("=" * 72)

        lager_list = self._db.find_all(COLLECTION_LAGER)
        if not lager_list:
            lines.append("Keine Lager vorhanden.")
        else:
            for lager in lager_list:
                lager_id = lager.get("_id", "?")
                lagername = lager.get("lagername", "") or "(unbenannt)"
                lines.append("")
                lines.append(f"Lager {lagername} (ID: {lager_id})")
                lines.append("-" * 72)
                try:
                    rows = self.inventory_report(str(lager_id))
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

    if len(sys.argv) >= 2:
        lager_id_arg = sys.argv[1]
        path = report.write_inventory_report(lager_id_arg)
        print(f"Inventory report for Lager {lager_id_arg} written to {path}")
    else:
        path = report.write_all_inventory_report()
        print(f"Global inventory report written to {path}")
