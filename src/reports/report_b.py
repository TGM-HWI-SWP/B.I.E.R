from typing import List, Dict, Optional, Tuple
from matplotlib.backends.backend_pdf import PdfPages
from collections import defaultdict
import re
import pathlib
import json
from datetime import datetime

from bierapp.db.postgress import PostgresRepository
from reports.report_format import (
    create_cover_page,
    create_table_pages,
    create_bar_chart,
    create_summary_page,
)
from reports.report_a import ReportA


DEFAULT_OUTPUT_FILE = pathlib.Path("report_b.pdf")


def _parse_history_row(row: Dict) -> Dict:
    """Extract product/warehouse/quantity and keep original row.

    Returns a normalized dict with keys: timestamp, entry_type, action,
    details, product_id, lager_id, quantity, raw.
    """
    details = row.get("details") or ""
    action = row.get("action")
    entry_type = row.get("entry_type")
    created_at = row.get("created_at")

    pid_m = re.search(r"produkt_id=(\d+)", details)
    lid_m = re.search(r"lager_id=(\d+)", details)
    menge_m = re.search(r"menge=(\-?\d+)", details)

    pid = pid_m.group(1) if pid_m else None
    lid = lid_m.group(1) if lid_m else None
    menge = int(menge_m.group(1)) if menge_m else None

    
    create_m = re.search(r"Produkt\s*(\d+)\s*:\s*(.+)", details, flags=re.IGNORECASE)
    if create_m:
        pid = pid or create_m.group(1)
        product_name_from_details = create_m.group(2).strip()
    else:
        product_name_from_details = None

    qty = None
    if menge is not None:
        qty = -abs(menge) if action == "assign" else abs(menge)
    result = {
        "timestamp": created_at,
        "entry_type": entry_type,
        "action": action,
        "details": details,
        "product_id": pid,
        "lager_id": lid,
        "quantity": qty,
        "raw": row,
    }
    if product_name_from_details:
        result["product_name"] = product_name_from_details

    return result


def _format_ts(ts) -> str:
    """Return a human readable timestamp similar to UI: D.M.YYYY, HH:MM:SS"""
    if ts is None:
        return ""
    try:
        if isinstance(ts, datetime):
            d = ts.astimezone() if ts.tzinfo else ts
        else:
            d = datetime.fromisoformat(str(ts))
            if d.tzinfo:
                d = d.astimezone()
        return f"{d.day}.{d.month}.{d.year}, {d.strftime('%H:%M:%S')}"
    except Exception:
        return str(ts)


class ReportB:
    """Generate per-product movement report (PDF)."""

    def __init__(self, db_repo: Optional[object] = None):
        self.db = db_repo or PostgresRepository()
        try:
            if getattr(self.db, "connect", None):
                self.db.connect()
        except Exception:
            self.db = None

    def _resolve_product_name(self, pid: Optional[str], details: str, report_a: ReportA, raw: Optional[Dict] = None) -> Optional[str]:
        """Try multiple strategies to get product name.

        Order of attempts:
        1. If `pid` provided: DB lookup.
        2. Parse `details` with several common patterns.
        3. Inspect `raw` row fields like `name` or `product_name`.
        4. Fallback to ReportA processed cache.
        """
        
        if pid:
            try:
                if self.db:
                    prod = self.db.find_by_id("products", pid)
                    if prod and prod.get("name"):
                        return prod.get("name")
            except Exception:
                pass

        def _name_from_details(txt: str) -> Optional[str]:
            if not txt:
                return None
            patterns = [
                r"Produkt\s*\d*:\s*(.+)$",
                r"Produkt:\s*(.+)$",
                r"name=\s*'?(\w[\w\s\-\._]+)'?",
                r"name=\s*\"?(\w[\w\s\-\._]+)\"?",
                r"produkt_name=\s*'?(\w[\w\s\-\._]+)'?",
                r"Produktname\s*[:=]\s*(.+)$",
                r"Neues Produkt[:=]\s*(.+)$",
            ]
            for pat in patterns:
                m = re.search(pat, txt, flags=re.IGNORECASE)
                if m:
                    return m.group(1).strip()
            return None

    
        name = _name_from_details(details)
        if name:
            return name

        if raw:
            for key in ("name", "product_name", "produkt_name", "title"):
                v = raw.get(key)
                if v:
                    return str(v)
        try:
           
            ra_raw = report_a.get_data(None)
            ra_proc = report_a.process_data(ra_raw)
            prod_info = ra_proc.get("products", {}).get(str(pid)) if pid else None
            if prod_info and prod_info.get("name"):
                return prod_info.get("name")
        except Exception:
            pass

        return None

    def _compute_running_rows(self, parsed: List[Dict], report_a: ReportA) -> List[List[str]]:
        """From parsed history entries compute ordered table rows with running totals.

        Returns list of table row lists: [time, product, direction, previous, change, current]
        """

        entries = [p for p in parsed if p.get("action") in ("create", "assign") and p.get("entry_type") in ("product", "inventory")]

      
        try:
            entries.sort(key=lambda x: x.get("timestamp") or datetime.max)
        except Exception:
            pass

        running: Dict[Tuple[str, str], float] = defaultdict(float)
        rows: List[Dict] = []

        for e in entries:
            pid = e.get("product_id")
            lid = e.get("lager_id")
            qty = float(e.get("quantity") or 0)
            key = (str(pid) if pid is not None else "", str(lid) if lid is not None else "")
            prev = running.get(key, 0.0)
            curr = prev + qty
            running[key] = curr

            
            if e.get("entry_type") == "product" and e.get("action") == "create":
                direction = "Neu angelegt"
            elif pid and lid:
                mapped_name = None
                try:
                    mapped_name = report_a.warehouses.get(str(lid)) if getattr(report_a, "warehouses", None) else None
                except Exception:
                    mapped_name = None
                dst_name = mapped_name or f"Lager {lid}"
                if qty >= 0:
                    src = "Neu"
                    dst = dst_name
                else:
                    src = dst_name
                    dst = "(nicht angegeben)"
                direction = f"{src} -> {dst}"
            else:
                direction = ""

            time_str = _format_ts(e.get("timestamp"))
            product_name = e.get("product_name") or f"Produkt {pid}" if pid else ""

            rows.append({
                "time_str": time_str,
                "product_name": product_name,
                "direction": direction,
                "previous": prev,
                "change": qty,
                "current": curr,
            })

  
        rows.reverse()

        out = []
        for r in rows:
            prev_disp = max(0.0, float(r["previous"]))
            curr_disp = max(0.0, float(r["current"]))
            out.append([
                r["time_str"],
                r["product_name"],
                r["direction"],
                f"{prev_disp:g}",
                f"{r['change']:g}",
                f"{curr_disp:g}",
            ])
        return out

    def generate_report(self, output_path: pathlib.Path = DEFAULT_OUTPUT_FILE) -> Dict:
        report_a = ReportA(self.db)

      
        try:
            history_rows = self.db.find_all("history") if getattr(self, "db", None) else []
        except Exception:
            history_rows = []

        flattened: List[Dict] = []
        table_rows: List[List[str]] = []

        if history_rows:
            parsed = [_parse_history_row(r) for r in history_rows]

      
            for p in parsed:
                if not p.get("product_name"):
                    p["product_name"] = self._resolve_product_name(p.get("product_id"), p.get("details") or "", report_a, raw=p.get("raw"))

            table_rows = self._compute_running_rows(parsed, report_a)
            flattened = parsed
        else:
         
            ra_raw = report_a.get_data(None)
            processed = report_a.process_data(ra_raw)
            products = processed.get("products", {})
            movements_by_product = processed.get("by_product", {})
            for pid, entries in movements_by_product.items():
                for e in entries:
                    row = e.copy()
                    row["product_id"] = pid
                    row["product_name"] = products.get(pid, {}).get("name") or row.get("product_name") or pid
                    flattened.append(row)

            try:
                flattened.sort(key=lambda x: x.get("timestamp") or datetime.max)
            except Exception:
                pass

            
            running_totals: Dict[Tuple[str, str], float] = defaultdict(float)
            for movement in flattened:
                pid = movement.get("product_id")
                name = movement.get("product_name") or pid
                change = float(movement.get("quantity") or 0)

             
                raw_ts = None
                for key in ("timestamp", "time", "created_at", "createdAt", "created", "date"):
                    raw = movement.get("raw") or {}
                    if key in raw and raw.get(key) is not None:
                        raw_ts = raw.get(key)
                        break
                time_str = _format_ts(raw_ts or movement.get("timestamp"))

           
                def resolve_loc(mov: Dict, side: str) -> Optional[str]:
                    if side == "from":
                        candidates = (mov.get("from"), mov.get("quelle"), mov.get("von"), mov.get("source"), mov.get("origin"))
                        id_candidates = (mov.get("lager_id"), mov.get("source_lager"), mov.get("from_warehouse"), mov.get("lager"))
                    else:
                        candidates = (mov.get("to"), mov.get("ziel"), mov.get("zu"), mov.get("target"), mov.get("destination"))
                        id_candidates = (mov.get("ziel_lager"), mov.get("target_lager"), mov.get("to_warehouse"), mov.get("lager_id"), mov.get("lager"))

                    for v in candidates:
                        if v:
                            return str(v)
                    for v in id_candidates:
                        if v is not None:
                            try:
                                mapped = report_a.warehouses.get(str(v)) if getattr(report_a, "warehouses", None) else None
                                return str(mapped or v)
                            except Exception:
                                return str(v)
                    raw = mov.get("raw") or {}
                    for k in ("from", "quelle", "von", "source", "origin", "from_location") if side == "from" else ("to", "ziel", "zu", "target", "destination", "to_location"):
                        if raw.get(k):
                            return str(raw.get(k))
                    return None

                src = resolve_loc(movement, "from")
                dst = resolve_loc(movement, "to")

                if change >= 0:
                    loc = dst or src or "(nicht angegeben)"
                else:
                    loc = src or dst or "(nicht angegeben)"

                key = (pid, str(loc))
                prev = running_totals.get(key, 0.0)
                curr = prev + change
                running_totals[key] = curr

                movement_direction = report_a._movement_direction(movement.get("raw", {}), change)
                prev_disp = max(0.0, float(prev))
                curr_disp = max(0.0, float(curr))
                table_rows.append([time_str, name, movement_direction, f"{prev_disp:g}", f"{change:g}", f"{curr_disp:g}"])

        headers = ["Datum", "Produkt", "Von -> Zu", "Menge", "Änderung", "Neue Menge"]


        with PdfPages(output_path) as pdf:
            meta = {"Erstellt": datetime.now().strftime("%Y-%m-%d %H:%M")}
            create_cover_page(pdf, "Produktstatistiken (Bewegungen)", "Report B — Bewegungen pro Produkt", meta)

      
            sales = defaultdict(float)
            for m in flattened:
                qty = float(m.get("quantity") or 0)
                if qty < 0:
                    sales[m.get("product_name") or m.get("product_id")] += abs(qty)

            top_sales = sorted(sales.items(), key=lambda x: x[1], reverse=True)[:10]
            if top_sales:
                names, values = zip(*top_sales)
                create_bar_chart(pdf, list(names), list(values), "Top 10 Produkte nach Verkaufszahlen")

          
            if sales:
                bottom_sales = sorted(sales.items(), key=lambda x: x[1])[:10]
                if bottom_sales:
                    b_names, b_values = zip(*bottom_sales)
                    create_bar_chart(pdf, list(b_names), list(b_values), "Bottom 10 Produkte nach Verkaufszahlen")

            total_in = sum(float(m.get("quantity") or 0) for m in flattened if float(m.get("quantity") or 0) >= 0)
            total_out = sum(abs(float(m.get("quantity") or 0)) for m in flattened if float(m.get("quantity") or 0) < 0)
            summary = {"Total Bewegungen": len(flattened), "Total eingegangen": int(total_in), "Total verkauft/ausgang": int(total_out)}
            create_summary_page(pdf, summary)

        return {"output": str(output_path), "summary": {"total_movements": len(flattened), "total_in": total_in, "total_out": total_out}, "generated": datetime.now().isoformat()}


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
