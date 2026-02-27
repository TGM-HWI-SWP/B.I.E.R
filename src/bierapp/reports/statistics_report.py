"""Statistics report component implementing the ReportPort contract.

This report computes aggregated KPIs (global statistics) across all
warehouses and products based on the persisted data.  The core method
``statistics_report`` liefert ein Dictionary für Tests, während
``write_statistics_report`` eine schön formatierte Textdatei im
``output``-Ordner des reports-Packages erzeugt.

Wird dieses Modul direkt ausgeführt (``python -m bierapp.reports.statistics_report``),
so wird automatisch der Statistik-Report in eine Textdatei geschrieben.
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


class StatisticsReport(ReportPort):
    """Calculate global statistics across all warehouses and products."""

    def __init__(self, db: MongoDBAdapter) -> None:
        self._db = db

    def inventory_report(self, lager_id: str) -> List[Dict]:
        """This component focuses on global statistics only.

        A dedicated InventoryReport component is responsible for
        inventory_report().
        """

        raise NotImplementedError("StatisticsReport does not provide inventory_report().")

    def statistics_report(self) -> Dict:
        # Load all domain data
        produkte = self._db.find_all(COLLECTION_PRODUKTE)
        lager = self._db.find_all(COLLECTION_LAGER)
        inventar = self._db.find_all(COLLECTION_INVENTAR)

        total_products = len(produkte)
        total_warehouses = len(lager)

        # Build lookup tables
        gewicht_by_id = {p["_id"]: float(p.get("gewicht", 0.0)) for p in produkte}
        preis_by_id   = {p["_id"]: float(p.get("preis",   0.0)) for p in produkte}
        capacity_by_lager = {w["_id"]: int(w.get("max_plaetze", 0)) for w in lager}
        lagername_by_id = {w["_id"]: w.get("lagername", "") for w in lager}

        total_units = 0
        total_weight = 0.0
        total_value = 0.0
        used_capacity_by_lager: Dict[str, int] = {lid: 0 for lid in capacity_by_lager}

        for entry in inventar:
            lager_id = entry.get("lager_id", "")
            produkt_id = entry.get("produkt_id", "")
            menge = int(entry.get("menge", 0))

            total_units += menge
            gewicht = gewicht_by_id.get(produkt_id, 0.0)
            total_weight += menge * gewicht
            preis = preis_by_id.get(produkt_id, 0.0)
            total_value += menge * preis

            if lager_id in used_capacity_by_lager and menge > 0:
                used_capacity_by_lager[lager_id] += 1

        # Capacity usage per warehouse
        capacity_usage_by_lager: Dict[str, float] = {}
        for lager_id, max_plaetze in capacity_by_lager.items():
            used_slots = used_capacity_by_lager.get(lager_id, 0)
            if max_plaetze > 0:
                capacity_usage_by_lager[lager_id] = used_slots / max_plaetze
            else:
                capacity_usage_by_lager[lager_id] = 0.0

        return {
            "total_products": total_products,
            "total_warehouses": total_warehouses,
            "total_units": total_units,
            "total_weight": total_weight,
            "total_value": total_value,
            "capacity_usage": {
                lagername_by_id.get(lager_id, lager_id): usage
                for lager_id, usage in capacity_usage_by_lager.items()
            },
        }

    # ------------------------------------------------------------------
    # Convenience API: Statistik-Report als Datei im output-Ordner
    # ------------------------------------------------------------------
    def write_statistics_report(self) -> Path:
        """Erzeuge eine textuelle Übersicht aller KPIs als Datei.

        Die Datei wird unter ``output/statistics.txt`` im reports-Package
        gespeichert. Der Rückgabewert ist der Pfad zur generierten Datei.
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
