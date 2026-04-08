from typing import List, Dict, Optional
from matplotlib.backends.backend_pdf import PdfPages
import pathlib
import sys
import json
from datetime import datetime, timedelta
from collections import defaultdict
from src.bierapp.db.postgress import PostgresRepository
from src.bierapp.contracts import ReportPort
from src.bierapp.reports.report_format import create_cover_page, create_table_pages,create_bar_chart, create_summary_page


DEFAULT_OUTPUT_FILE = pathlib.Path("report_a.pdf")
SAMPLE_BASE_DATE = datetime(2026, 1, 1, 8, 0, 0)
ID_MODULO = 100
INITIAL_OFFSET = 20
MAX_DAY_SPAN = 60
OUT_QUANTITY_MOD = 15
OUT_DAYS_OFFSET = 10


def _products_to_movements(product_list: List[Dict]) -> List[Dict]:
    """Create deterministic synthetic movements from a product list.

    For each product we create one initial inbound movement and optionally one small outbound.
    """
    movements: List[Dict] = []
    for item in product_list:
        raw_id = item.get("id") or item.get("product_id") or item.get("produkt_id") or ""
        product_id = str(raw_id)
        product_name = item.get("product") or item.get("product_name") or f"Produkt {product_id}"

        try:
            numeric_seed = int(item.get("id"))
        except Exception:
            numeric_seed = abs(hash(product_id)) % ID_MODULO

        initial_quantity = (numeric_seed % ID_MODULO) + INITIAL_OFFSET
        initial_timestamp = (SAMPLE_BASE_DATE + timedelta(days=numeric_seed % MAX_DAY_SPAN)).isoformat()

        movements.append({
            "id": f"init-{product_id}",
            "product_id": product_id,
            "product_name": product_name,
            "quantity_change": initial_quantity,
            "timestamp": initial_timestamp,
        })

        outbound_quantity = -(numeric_seed % OUT_QUANTITY_MOD)
        if outbound_quantity != 0:
            outbound_timestamp = (SAMPLE_BASE_DATE + timedelta(days=(numeric_seed % MAX_DAY_SPAN) + OUT_DAYS_OFFSET)).isoformat()
            movements.append({
                "id": f"out-{product_id}",
                "product_id": product_id,
                "product_name": product_name,
                "quantity_change": outbound_quantity,
                "timestamp": outbound_timestamp,
            })

    return movements


class ReportB(ReportPort):
    """Simplified, well-named implementation that produces a PDF report.

    The class keeps the same external behavior: load movements (from JSON, DB
    or bundled dummy), process them and create a PDF using the report_format helpers.
    """

    def __init__(self, db_repo: Optional[object] = None):
        self.db = db_repo or (PostgresRepository() if PostgresRepository else None)
        if self.db:
            try:
                self.db.connect()
            except Exception:
                self.db = None

    def get_data(self, input_path: Optional[pathlib.Path] = None) -> List[Dict]:
        """Load movements from a file, the DB, or bundled dummy data.

        If the loaded list looks like products (no quantity/timestamp keys)
        we convert it to synthetic movements.
        """
        def looks_like_movements(sample: Dict) -> bool:
            return "quantity_change" in sample or "timestamp" in sample


        if self.db:
            for candidate_table in ("movements", "inventory_movements", "inventory"):
                try:
                    rows = self.db.find_all(candidate_table)
                    if rows:
                        return rows
                except Exception:
                    continue
                
        if input_path:
            try:
                path = pathlib.Path(input_path)
                if path.exists() and path.is_file():
                    with path.open("r", encoding="utf-8") as reader:
                        payload = json.load(reader)
                        if isinstance(payload, list) and payload:
                            first = payload[0]
                            if isinstance(first, dict) and not looks_like_movements(first):
                                return _products_to_movements(payload)
                        return payload if isinstance(payload, list) else []
            except Exception:
                pass



        try:
            dummy_path = pathlib.Path(__file__).parent / "dummy_data.json"
            if dummy_path.exists():
                with dummy_path.open("r", encoding="utf-8") as reader:
                    payload = json.load(reader)
                    if isinstance(payload, list) and payload:
                        first = payload[0]
                        if isinstance(first, dict) and not looks_like_movements(first):
                            return _products_to_movements(payload)
                    return payload if isinstance(payload, list) else []
        except Exception:
            pass

        return []

    def inventory_report(self, warehouse_id: str) -> List[Dict]:
        """Return inventory entries for a warehouse.

        When DB is present we enrich inventory rows with product info. When there
        is no DB we support a pseudo-warehouse id 'default' by aggregating movements.
        """
        if self.db:
            warehouse = self.db.find_by_id("warehouses", warehouse_id)
            if not warehouse:
                raise KeyError("Warehouse not found")

            inventory_rows = self.db.find_all("inventory") or []
            filtered = [r for r in inventory_rows if r.get("lager_id") == warehouse_id]
            for row in filtered:
                pid = row.get("produkt_id") or row.get("product_id")
                if pid:
                    product = self.db.find_by_id("products", pid)
                    if product:
                        row.setdefault("product", {})
                        row["product"]["id"] = product.get("id")
                        row["product"]["name"] = product.get("name")
            return filtered

        movements = self.get_data(None)
        if not isinstance(movements, list):
            raise KeyError("Warehouse not found")
        
        if movements and isinstance(movements[0], dict) and "quantity_change" in movements[0]:
            stock_by_product: Dict[str, Dict] = {}
            for row in movements:
                pid = str(row.get("product_id") or row.get("produkt_id") or row.get("id"))
                name = row.get("product_name") or row.get("product") or pid
                qty = float(row.get("quantity_change") or 0)
                if pid not in stock_by_product:
                    stock_by_product[pid] = {"produkt_id": pid, "menge": 0.0, "product_name": name}
                stock_by_product[pid]["menge"] += qty

            if warehouse_id != "default":
                raise KeyError("Warehouse not found")
            return list(stock_by_product.values())

        if isinstance(movements, list):
            if warehouse_id != "default":
                raise KeyError("Warehouse not found")
            return [{"produkt_id": str(p.get("id")), "menge": 0, "product_name": p.get("product")} for p in movements]

        raise KeyError("Warehouse not found")

    def statistics_report(self) -> Dict:
        """Return simple aggregated statistics (products, warehouses, stock units)."""
        if self.db:
            products = self.db.find_all("products") or []
            warehouses = self.db.find_all("warehouses") or []
            inventory = self.db.find_all("inventory") or []
            total_units = sum((item.get("menge") or 0) for item in inventory)
            return {"total_products": len(products), "total_warehouses": len(warehouses), "total_stock_units": total_units}

        movements = self.get_data(None)
        if isinstance(movements, list) and movements and isinstance(movements[0], dict) and "quantity_change" in movements[0]:
            product_ids = {str(m.get("product_id") or m.get("produkt_id") or m.get("id")) for m in movements}
            total_units = sum(float(m.get("quantity_change") or 0) for m in movements)
            return {"total_products": len(product_ids), "total_warehouses": 1, "total_stock_units": total_units}

        if isinstance(movements, list):
            return {"total_products": len(movements), "total_warehouses": 1, "total_stock_units": 0}

        return {"total_products": 0, "total_warehouses": 0, "total_stock_units": 0}

    def process_data(self, movements: List[Dict]) -> Dict:
        """Normalize raw movement rows into structured products and sorted per-product movements."""
        products_map: Dict[str, Dict] = {}
        movements_by_product: Dict[str, List[Dict]] = defaultdict(list)

        for row in movements:
            product_id = row.get("product_id") or row.get("produkt_id") or str(row.get("id"))
            product_name = row.get("product_name") or row.get("product") or row.get("name") or product_id
            raw_qty = row.get("quantity_change") or row.get("menge") or row.get("quantity") or 0
            try:
                quantity = float(raw_qty)
            except Exception:
                quantity = 0.0

            timestamp_value = row.get("timestamp") or row.get("time") or row.get("created_at")
            parsed_ts = None
            if timestamp_value:
                try:
                    parsed_ts = datetime.fromisoformat(timestamp_value)
                except Exception:
                    try:
                        parsed_ts = datetime.fromtimestamp(float(timestamp_value))
                    except Exception:
                        parsed_ts = None

            entry = {
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity,
                "timestamp": parsed_ts,
                "raw": row,
            }
            movements_by_product[product_id].append(entry)
            products_map[product_id] = {"id": product_id, "name": product_name}

        for pid, entries in movements_by_product.items():
            entries.sort(key=lambda e: e["timestamp"] or datetime.max)

        return {"products": products_map, "by_product": dict(movements_by_product)}

    def generate_report(self, processed: Dict, output_path: pathlib.Path = DEFAULT_OUTPUT_FILE) -> Dict:
        """Create a PDF report and return a summary dict."""
        products = processed.get("products", {})
        movements_by_product = processed.get("by_product", {})

        flattened: List[Dict] = []
        for pid, entries in movements_by_product.items():
            for e in entries:
                row = e.copy()
                row["product_id"] = pid
                row["product_name"] = products.get(pid, {}).get("name") or row.get("product_name") or pid
                flattened.append(row)

        flattened.sort(key=lambda x: x["timestamp"] or datetime.max)

        table_rows: List[List[str]] = []
        running_totals: Dict[str, float] = defaultdict(float)
        for movement in flattened:
            pid = movement.get("product_id")
            name = movement.get("product_name") or pid
            change = float(movement.get("quantity") or 0)
            previous = running_totals[pid]
            current = previous + change
            ts = movement.get("timestamp")
            time_str = ts.strftime("%Y-%m-%d %H:%M") if isinstance(ts, datetime) else (getattr(ts, "isoformat", lambda: str(ts))()) if ts else ""
            table_rows.append([time_str, name, f"{previous:g}", f"{change:g}", f"{current:g}"])
            running_totals[pid] = current

  
        metadata = {
            "Erstellt": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Bewegungen": str(len(flattened)),
            "Produkte": str(len(products)),
        }


        with PdfPages(output_path) as pdf:
            create_cover_page(pdf, "Lagerbewegungsbericht", "Report A — Bewegungen aller Produkte", metadata)

            headers = ["Datum", "Produkt", "Menge", "Änderung", "Neue Menge"]
            create_table_pages(pdf, headers, table_rows, title="Lagerbewegungen", fit_one_page=False)

          
            sales: Dict[str, float] = defaultdict(float)
            for m in flattened:
                qty = float(m.get("quantity") or 0)
                if qty < 0:
                    sales[m.get("product_name") or m.get("product_id")] += abs(qty)

            top_sales = sorted(sales.items(), key=lambda x: x[1], reverse=True)[:10]
            if top_sales:
                names, values = zip(*top_sales)
                create_bar_chart(pdf, list(names), list(values), "Top 10 Produkte nach Verkaufszahlen")

            total_in = sum(float(m.get("quantity") or 0) for m in flattened if float(m.get("quantity") or 0) >= 0)
            total_out = sum(abs(float(m.get("quantity") or 0)) for m in flattened if float(m.get("quantity") or 0) < 0)
            summary_data = {"Total Bewegungen": len(flattened), "Total eingegangen": int(total_in), "Total verkauft/ausgang": int(total_out)}
            create_summary_page(pdf, summary_data)

        result_summary = {
            "output": str(output_path),
            "summary": {
                "total_movements": len(flattened),
                "total_in": total_in,
                "total_out": total_out,
                "top_sales": [{"product_name": n, "sold": v} for n, v in top_sales],
            },
        }

        return result_summary


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    report = ReportB()
    raw = report.get_data(arg)
    processed = report.process_data(raw)
    output = report.generate_report(processed)
    print(json.dumps(output, indent=4, default=str))

