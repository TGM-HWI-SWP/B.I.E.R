
from typing import List, Dict, Optional
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pathlib
import sys
import json
from datetime import datetime
from collections import defaultdict
from src.bierapp.db.postgress import PostgresRepository
from src.bierapp.contracts import ReportPort
from datetime import timedelta
from src.bierapp.reports.report_format import create_cover_page, create_table_pages, create_barh_chart, create_summary_page


def _products_to_movements(products: List[Dict]) -> List[Dict]:
    """Convert a simple product list into deterministic synthetic movements.

    Creates one initial inbound movement and one small outbound movement per product.
    """
    out: List[Dict] = []
    base = datetime(2026, 1, 1, 8, 0, 0)
    for item in products:
        pid = str(item.get("id") or item.get("product_id") or item.get("produkt_id") or "")
        name = item.get("product") or item.get("product_name") or f"Produkt {pid}"
        try:
            nid = int(item.get("id"))
        except Exception:
            nid = abs(hash(pid)) % 100

        initial = (nid % 100) + 20
        out.append({
            "id": f"init-{pid}",
            "product_id": pid,
            "product_name": name,
            "quantity_change": initial,
            "timestamp": (base + timedelta(days=nid % 60)).isoformat(),
        })

        out_qty = -(nid % 15)
        if out_qty != 0:
            out.append({
                "id": f"out-{pid}",
                "product_id": pid,
                "product_name": name,
                "quantity_change": out_qty,
                "timestamp": (base + timedelta(days=(nid % 60) + 10)).isoformat(),
            })

    return out



class ReportA(ReportPort):
    """Generates a PDF report of warehouse movements (Lagerbewegungen).

    Behavior:
    - If `input_path` points to an existing JSON file, movements are loaded from it.
    - If `input_path` is the string 'db' (or a non-existing path) and PostgresRepository
      is available, movements are loaded from the DB table `movements` (fallbacks
      to `inventory` if not present).

    Output: saves `report_a.pdf` in the current working directory and returns
    a summary dictionary.
    """

    def __init__(self, db_repo: Optional[object] = None):
        self.db = db_repo or (PostgresRepository() if PostgresRepository else None)
        if self.db:
            try:
                self.db.connect()
            except Exception:
                pass

    def get_data(self, input_path: Optional[pathlib.Path] = None) -> List[Dict]:
        if input_path:
            try:
                p = pathlib.Path(input_path)
                if p.exists() and p.is_file():
                    with p.open("r", encoding="utf-8") as fh:
                        data = json.load(fh)
                        if isinstance(data, list) and data and isinstance(data[0], dict):
 
                            if "quantity_change" not in data[0] and "timestamp" not in data[0]:
                                return _products_to_movements(data)
                        return data
            except Exception:
                pass

        if self.db:
            for table in ("movements", "inventory_movements", "inventory"):
                try:
                    rows = self.db.find_all(table)
                    if rows:
                        return rows
                except Exception:
                    continue

        try:
            repo_dummy = pathlib.Path(__file__).parent / "dummy_data.json"
            if repo_dummy.exists():
                with repo_dummy.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    if isinstance(data, list) and data and isinstance(data[0], dict):
                        if "quantity_change" not in data[0] and "timestamp" not in data[0]:
                            return _products_to_movements(data)
                    return data
        except Exception:
            pass

        return []

    def inventory_report(self, lager_id: str) -> List[Dict]:
        """ReportPort: return inventory entries for a given warehouse.

        If DB is configured, reads `inventory` table and enriches with product data.
        Otherwise uses converted movements from dummy data and supports a
        pseudo-warehouse id `default`.
        """
        if self.db:

            wh = self.db.find_by_id("warehouses", lager_id)
            if not wh:
                raise KeyError("Warehouse not found")

            inventory = self.db.find_all("inventory")
            items = [item for item in inventory if item.get("lager_id") == lager_id]

            for item in items:
                pid = item.get("produkt_id") or item.get("product_id")
                if pid:
                    prod = self.db.find_by_id("products", pid)
                    if prod:
                        item.setdefault("product", {})
                        item["product"]["id"] = prod.get("id")
                        item["product"]["name"] = prod.get("name")
            return items

        data = self.get_data(None)

        if data and isinstance(data, list) and "quantity_change" in data[0]:
            stocks: Dict[str, Dict] = {}
            for m in data:
                pid = str(m.get("product_id") or m.get("produkt_id") or m.get("id"))
                name = m.get("product_name") or m.get("product") or pid
                qty = float(m.get("quantity_change") or 0)
                if pid not in stocks:
                    stocks[pid] = {"produkt_id": pid, "menge": 0, "product_name": name}
                stocks[pid]["menge"] += qty

            if lager_id != "default":
                raise KeyError("Warehouse not found")

            return list(stocks.values())
        if data and isinstance(data, list):
            if lager_id != "default":
                raise KeyError("Warehouse not found")
            return [{"produkt_id": str(p.get("id")), "menge": 0, "product_name": p.get("product")} for p in data]

        raise KeyError("Warehouse not found")

    def statistics_report(self) -> Dict:
        """ReportPort: return aggregated statistics."""
        if self.db:
            products = self.db.find_all("products")
            warehouses = self.db.find_all("warehouses")
            inventory = self.db.find_all("inventory")
            total_stock = sum((item.get("menge") or 0) for item in inventory)
            return {"total_products": len(products), "total_warehouses": len(warehouses), "total_stock_units": total_stock}

        data = self.get_data(None)
        if data and isinstance(data, list) and "quantity_change" in data[0]:
            pids = set()
            total = 0
            for m in data:
                pids.add(str(m.get("product_id") or m.get("produkt_id") or m.get("id")))
                total += float(m.get("quantity_change") or 0)
            return {"total_products": len(pids), "total_warehouses": 1, "total_stock_units": total}

        if data and isinstance(data, list):
            return {"total_products": len(data), "total_warehouses": 1, "total_stock_units": 0}

        return {"total_products": 0, "total_warehouses": 0, "total_stock_units": 0}

    def process_data(self, data: List[Dict]) -> Dict:
        products: Dict[str, Dict] = {}
        by_product = defaultdict(list)

        for row in data:
            pid = row.get("product_id") or row.get("produkt_id") or str(row.get("id"))
            name = row.get("product_name") or row.get("product") or row.get("name") or pid
            qty = row.get("quantity_change") or row.get("menge") or row.get("quantity") or 0
            try:
                qty = float(qty)
            except Exception:
                qty = 0.0

            ts = row.get("timestamp") or row.get("time") or row.get("created_at")
            dt = None
            if ts:
                try:

                    dt = datetime.fromisoformat(ts)
                except Exception:
                    try:
                        dt = datetime.fromtimestamp(float(ts))
                    except Exception:
                        dt = None

            entry = {
                "product_id": pid,
                "product_name": name,
                "quantity": qty,
                "timestamp": dt,
                "raw": row,
            }
            by_product[pid].append(entry)
            products[pid] = {"id": pid, "name": name}

        for pid, entries in by_product.items():
            entries.sort(key=lambda x: x["timestamp"] or datetime.max)

        return {"products": products, "by_product": dict(by_product)}

    def generate_report(self, processed: Dict, output_path: pathlib.Path = pathlib.Path("report_a.pdf")) -> Dict:
        products = processed.get("products", {})
        by_product = processed.get("by_product", {})

        summary = {"products": {}}


        all_movements = []
        for pid, entries in by_product.items():
            for e in entries:
                mv = e.copy()
                mv["product_id"] = pid
                mv["product_name"] = products.get(pid, {}).get("name", mv.get("product_name") or pid)
                all_movements.append(mv)

        all_movements.sort(key=lambda x: x["timestamp"] or datetime.max)


        table_rows: List[List[str]] = []
        cumulative_by_pid = defaultdict(float)
        for m in all_movements:
            pid = m.get("product_id")
            name = m.get("product_name") or products.get(pid, {}).get("name") or pid
            change = float(m.get("quantity") or 0)
            prev = cumulative_by_pid[pid]
            new = prev + change
            ts = m.get("timestamp")
            tstr = ts.strftime("%Y-%m-%d %H:%M") if isinstance(ts, datetime) else (ts.isoformat() if hasattr(ts, "isoformat") else str(ts) if ts else "")
            table_rows.append([tstr, name, f"{prev:g}", f"{change:g}", f"{new:g}"])
            cumulative_by_pid[pid] = new


        meta = {
            "Erstellt": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Bewegungen": str(len(all_movements)),
            "Produkte": str(len(products)),
        }

        with PdfPages(output_path) as pdf:
            create_cover_page(pdf, "Lagerbewegungsbericht", "Report A — Bewegungen aller Produkte", meta)

            headers = ["Datum", "Produkt", "Menge", "Änderungen", "Neue Menge"]
            create_table_pages(pdf, headers, table_rows, title="Lagerbewegungen", fit_one_page=False)

            sales = defaultdict(float)
            for m in all_movements:
                q = float(m.get("quantity") or 0)
                if q < 0:
                    sales[m.get("product_name") or m.get("product_id")] += abs(q)

            top10 = sorted(sales.items(), key=lambda x: x[1], reverse=True)[:10]
            if top10:
                names = [t[0] for t in top10]
                values = [t[1] for t in top10]
                create_barh_chart(pdf, names, values, "Top 10 Produkte nach Verkaufszahlen")

            total_in = sum(float(m.get("quantity") or 0) for m in all_movements if float(m.get("quantity") or 0) >= 0)
            total_out = sum(abs(float(m.get("quantity") or 0)) for m in all_movements if float(m.get("quantity") or 0) < 0)
            summary_data = {
                "Total Bewegungen": len(all_movements),
                "Total eingegangen": int(total_in),
                "Total verkauft/ausgang": int(total_out),
            }
            create_summary_page(pdf, summary_data)

        summary.update({
            "total_movements": len(all_movements),
            "total_in": total_in,
            "total_out": total_out,
            "top_sales": [{"product_name": n, "sold": v} for n, v in top10],
        })

        return {"output": str(output_path), "summary": summary}


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    report = ReportA()
    data = report.get_data(arg)
    processed_data = report.process_data(data)
    report_output = report.generate_report(processed_data)
    print(json.dumps(report_output, indent=4, default=str))

