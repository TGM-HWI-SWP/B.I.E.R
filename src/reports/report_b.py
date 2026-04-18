from typing import List, Dict, Optional
from matplotlib.backends.backend_pdf import PdfPages
from collections import defaultdict
import pathlib
import json
from datetime import datetime

from bierapp.db.postgress import PostgresRepository
from reports.report_format import create_cover_page, create_table_pages, create_bar_chart, create_summary_page


DEFAULT_OUTPUT_FILE = pathlib.Path("report_b.pdf")


class ReportB:
    """Generate a per-product statistics report and export it as PDF.

    The report loads data from the database (products + inventory) and computes
    simple statistics per product (total stock, warehouses count, average per
    warehouse). It renders a table and a bar chart using helpers from
    `report_format` and writes a PDF to the current working directory.
    """

    def __init__(self, db_repo: Optional[object] = None):
        self.db = db_repo or PostgresRepository()
        try:
            if getattr(self.db, "connect", None):
                self.db.connect()
        except Exception:
            # If DB connection fails we'll keep db as None to allow graceful
            # handling by callers.
            self.db = None

    def _load_db_tables(self) -> Dict[str, List[Dict]]:
        products = []
        inventory = []
        try:
            if self.db:
                products = self.db.find_all("products") or []
                inventory = self.db.find_all("inventory") or []
        except Exception:
            products = products or []
            inventory = inventory or []
        return {"products": products, "inventory": inventory}

    def compute_statistics(self) -> Dict:
        data = self._load_db_tables()
        products = data.get("products", [])
        inventory = data.get("inventory", [])

        # Index products by id (string)
        prod_map: Dict[str, Dict] = {}
        for p in products:
            pid = str(p.get("id"))
            prod_map[pid] = {"id": pid, "name": p.get("name") or str(pid), "gewicht": p.get("gewicht")}

        # Aggregate inventory per product
        stats: Dict[str, Dict] = {}
        for item in inventory:
            pid = str(item.get("produkt_id") or item.get("product_id") or item.get("produktId") or item.get("produkt") or item.get("id"))
            if not pid:
                continue
            qty = float(item.get("menge") or item.get("quantity") or 0)
            lid = item.get("lager_id") or item.get("lager") or item.get("warehouse_id")
            s = stats.setdefault(pid, {"total_stock": 0.0, "warehouses": set()})
            s["total_stock"] += qty
            if lid is not None:
                s["warehouses"].add(str(lid))

        # Ensure all products appear in stats (even with zero stock)
        for pid, pinfo in prod_map.items():
            if pid not in stats:
                stats[pid] = {"total_stock": 0.0, "warehouses": set()}

        # Build final per-product statistics list
        rows: List[Dict] = []
        for pid, s in stats.items():
            name = prod_map.get(pid, {}).get("name") or pid
            weight = prod_map.get(pid, {}).get("gewicht")
            total = float(s.get("total_stock") or 0.0)
            wh_count = len(s.get("warehouses") or set())
            avg = total / wh_count if wh_count > 0 else 0.0
            rows.append({
                "product_id": pid,
                "name": name,
                "total_stock": total,
                "warehouses": wh_count,
                "avg_per_warehouse": avg,
                "weight": weight,
            })

        # Sort by total_stock desc
        rows.sort(key=lambda r: r["total_stock"], reverse=True)
        return {"rows": rows, "generated_at": datetime.now().isoformat()}

    def generate_report(self, output_path: pathlib.Path = DEFAULT_OUTPUT_FILE) -> Dict:
        stats = self.compute_statistics()
        rows = stats.get("rows", [])

        # Prepare table rows
        table_rows: List[List[str]] = []
        for r in rows:
            table_rows.append([
                r["product_id"],
                r["name"],
                f"{int(r['total_stock']):d}",
                str(r["warehouses"]),
                f"{r['avg_per_warehouse']:.2f}",
                f"{r['weight'] or '-'}",
            ])

        headers = ["Produkt ID", "Name", "Total Lagerbestand", "Lager (Anzahl)", "Durchschnitt / Lager", "Gewicht (kg)"]

        # Create PDF
        with PdfPages(output_path) as pdf:
            meta = {"Erstellt": datetime.now().strftime("%Y-%m-%d %H:%M")}
            create_cover_page(pdf, "Produktstatistiken", "Report B — Statistiken pro Produkt", meta)
            create_table_pages(pdf, headers, table_rows, title="Produktstatistiken", fit_one_page=False)

            # Bar chart: top 10 products by stock
            top = rows[:10]
            if top:
                names = [t["name"] for t in top]
                values = [float(t["total_stock"]) for t in top]
                create_bar_chart(pdf, names, values, "Top 10 Produkte nach Lagerbestand")

            summary = {"Produkte": len(rows), "Totaleinheiten (gesamt)": int(sum(float(r["total_stock"]) for r in rows))}
            create_summary_page(pdf, summary)

        return {"output": str(output_path), "summary": summary, "generated": stats.get("generated_at")}


if __name__ == "__main__":
    import sys

    arg = sys.argv[1] if len(sys.argv) > 1 else None
    report = ReportB()
    try:
        out = report.generate_report(pathlib.Path(arg) if arg else DEFAULT_OUTPUT_FILE)
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"Fehler beim Generieren des Reports: {e}")
        raise
