from typing import List, Dict, Optional, Tuple
from matplotlib.backends.backend_pdf import PdfPages
from collections import defaultdict
import pathlib
import shlex
import json
from datetime import datetime
from matplotlib import pyplot as plt

from bierapp.db.postgress import PostgresRepository
from reports.report_format import create_cover_page, create_table_pages, create_bar_chart, create_summary_page
from reports.report_a import ReportA


DEFAULT_OUTPUT_FILE = pathlib.Path("report_b_neu.pdf")


def _find_int_after_key(details: str, key: str, allow_negative: bool = False) -> Optional[int]:
    if not details:
        return None
    low = details.lower()
    k = key.lower()
    pos = low.find(k)
    if pos == -1:
        return None
    
    start = pos + len(k)
    s = details[start:]
   
   
   
    i = 0
    while i < len(s) and not (s[i].isdigit() or (allow_negative and s[i] == '-')):
        i += 1
    if i >= len(s):
        return None
    num_chars = []
    if allow_negative and s[i] == '-':
        num_chars.append('-')
        i += 1
    while i < len(s) and s[i].isdigit():
        num_chars.append(s[i])
        i += 1
    if not num_chars or (num_chars == ['-']):
        return None
    try:
        return int(''.join(num_chars))
    except Exception:
        return None


def _find_all_ints_after_key(details: str, key: str) -> List[int]:
    result: List[int] = []
    if not details:
        return result
    low = details.lower()
    k = key.lower()
    start = 0
    while True:
        pos = low.find(k, start)
        if pos == -1:
            break
        val = _find_int_after_key(details[pos + len(k):], '', allow_negative=False)
        if val is not None:
            result.append(val)
        start = pos + len(k)
    return result


def _first_int_in_slice(s: str) -> Optional[int]:
    if not s:
        return None
    i = 0
    while i < len(s) and not (s[i].isdigit() or s[i] == '-'):
        i += 1
    if i >= len(s):
        return None
    num_chars = []
    if s[i] == '-':
        num_chars.append('-')
        i += 1
    while i < len(s) and s[i].isdigit():
        num_chars.append(s[i])
        i += 1
    try:
        return int(''.join(num_chars))
    except Exception:
        return None


def _find_von_nach_numbers(details: str) -> Optional[Tuple[Optional[int], Optional[int]]]:
    if not details:
        return None
    low = details.lower()
    vpos = low.find('von')
    npos = low.find('nach')
    if vpos == -1 or npos == -1 or npos <= vpos:
        return None
    between = details[vpos + 3:npos]
    after = details[npos + 4:]
    a = _first_int_in_slice(between)
    b = _first_int_in_slice(after)
    return (a, b)


def _find_lager_numbers(details: str) -> List[int]:
    res: List[int] = []
    if not details:
        return res
    low = details.lower()
    start = 0
    while True:
        pos = low.find('lager', start)
        if pos == -1:
            break
        tail = details[pos + len('lager'):]
        i = 0
        while i < len(tail) and tail[i] in ' :#-\t':
            i += 1
        num = _first_int_in_slice(tail[i:])
        if num is not None:
            res.append(num)
        start = pos + len('lager')
    return res


def _find_text_von_nach(details: str) -> Optional[Tuple[str, str]]:
    if not details:
        return None
    low = details.lower()
    vpos = low.find('von')
    npos = low.find('nach')
    if vpos == -1 or npos == -1 or npos <= vpos:
        return None
    left = details[vpos + 3:npos].strip()
    for sep in (',', ';', '\n'):
        si = left.find(sep)
        if si != -1:
            left = left[:si]
    right = details[npos + 4:].strip()
    for sep in (',', ';', '\n'):
        si = right.find(sep)
        if si != -1:
            right = right[:si]
    if left or right:
        return (left.strip(), right.strip())
    return None


def _extract_name(details: str) -> Optional[str]:
    if not details:
        return None
    low = details.lower()

    idx = low.find('produkt')
    if idx != -1:
        colon = details.find(':', idx)
        if colon != -1:
            tail = details[colon + 1:]
            for sep in ('\n', ',', ';'):
                si = tail.find(sep)
                if si != -1:
                    tail = tail[:si]
            val = tail.strip()
            if val:
                return val

    try:
        for tok in shlex.split(details):
            if tok.lower().startswith('name='):
                val = tok.split('=', 1)[1]
                return val.strip().strip('"\'')
    except ValueError:
        pass

    
    pos = low.find('name=')
    if pos != -1:
        start = pos + len('name=')
        tail = details[start:].lstrip()
        if not tail:
            return None
        if tail[0] in ('"', "'"):
            q = tail[0]
            end = tail.find(q, 1)
            if end != -1:
                return tail[1:end].strip()
            for sep in ('\n', ',', ';'):
                si = tail.find(sep)
                if si != -1:
                    return tail[1:si].strip()
            return tail[1:].strip()
        else:
            for sep in ('\n', ',', ';'):
                si = tail.find(sep)
                if si != -1:
                    return tail[:si].strip()
            return tail.split()[0].strip()

 
    kpos = low.find('produktname')
    if kpos != -1:
        for sep_char in (':', '='):
            sep_idx = details.find(sep_char, kpos + len('produktname'))
            if sep_idx != -1:
                tail = details[sep_idx + 1:]
                for sep in ('\n', ',', ';'):
                    si = tail.find(sep)
                    if si != -1:
                        tail = tail[:si]
                val = tail.strip()
                if val:
                    return val

    return None


def _parse_history_row(row: Dict) -> Dict:
    details = row.get("details") or ""
    action = row.get("action")
    entry_type = row.get("entry_type")
    created_at = row.get("created_at")

    pid = _find_int_after_key(details, "produkt_id=")
    lid = _find_int_after_key(details, "lager_id=")
    menge = _find_int_after_key(details, "menge=", allow_negative=True)

    qty = None
    if menge is not None:
        qty = abs(menge) if action == "assign" else abs(menge)

    
    raw = dict(row) if isinstance(row, dict) else {"raw": row}
    try:
       
        lids = _find_all_ints_after_key(details, "lager_id=")
        if len(lids) >= 2:
            raw.setdefault("source_lager", int(lids[0]))
            raw.setdefault("target_lager", int(lids[1]))
            raw.setdefault("from", int(lids[0]))
            raw.setdefault("to", int(lids[1]))
        else:
            
            s = _find_int_after_key(details, "source_lager=")
            t = _find_int_after_key(details, "target_lager=")
            if s is not None:
                raw.setdefault("source_lager", int(s))
                raw.setdefault("from", int(s))
            if t is not None:
                raw.setdefault("target_lager", int(t))
                raw.setdefault("to", int(t))

           
            if not raw.get("from") and not raw.get("to"):
                nums = _find_von_nach_numbers(details)
                if nums:
                    a, b = nums
                    if a is not None:
                        raw.setdefault("from", int(a))
                        raw.setdefault("source_lager", int(a))
                    if b is not None:
                        raw.setdefault("to", int(b))
                        raw.setdefault("target_lager", int(b))

            if not raw.get("from") and not raw.get("to"):
                lids2 = _find_lager_numbers(details)
                if len(lids2) >= 2:
                    raw.setdefault("from", int(lids2[0]))
                    raw.setdefault("to", int(lids2[1]))
                    raw.setdefault("source_lager", int(lids2[0]))
                    raw.setdefault("target_lager", int(lids2[1]))

        
            if not raw.get("from") and not raw.get("to"):
                names = _find_text_von_nach(details)
                if names:
                    left, right = names
                    if left:
                        raw.setdefault("from", left)
                    if right:
                        raw.setdefault("to", right)
    except Exception:
        pass

    return {"timestamp": created_at, "entry_type": entry_type, "action": action, "details": details, "product_id": pid, "lager_id": lid, "quantity": qty, "raw": raw}


def _format_ts(ts) -> str:
    if ts is None:
        return ""
    try:
        if isinstance(ts, datetime):
            d = ts.astimezone() if ts.tzinfo else ts
        else:
            d = datetime.fromisoformat(str(ts))
        return f"{d.day}.{d.month}.{d.year}, {d.strftime('%H:%M:%S')}"
    except Exception:
        return str(ts)


def _is_relevant(parsed: Dict) -> bool:
    action = (parsed.get("action") or "").lower()
    entry_type = (parsed.get("entry_type") or "").lower()
    details = (parsed.get("details") or "").lower()
    if any(k in entry_type for k in ("warehouse", "lager", "storage")):
        return False
   
    if action == "create" and ("lager" in details or "warehouse" in details):
        return False
    if action in ("create", "assign", "book", "booking", "gebucht"):
        return True
    if parsed.get("quantity") is not None:
        return True
    return False


def _create_pie_chart(pdf: PdfPages, labels: List[str], values: List[float], title: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.axis("equal")
    ax.set_title(title)
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


class ReportBNeu:
    """Report B neu: Top/Bottom-10 Bars and pie distribution across warehouses, based solely on filtered history rows."""

    def __init__(self, db_repo: Optional[object] = None):
        self.db = db_repo or PostgresRepository()
        try:
            if getattr(self.db, "connect", None):
                self.db.connect()
        except Exception:
            self.db = None

    def generate_report(self, output_path: pathlib.Path = DEFAULT_OUTPUT_FILE) -> Dict:
        report_a = ReportA(self.db)

        try:
            history_rows = self.db.find_all("history") if getattr(self, "db", None) else []
        except Exception:
            history_rows = []

       
        parsed = [_parse_history_row(r) for r in history_rows]

        def _to_dt(v):
            if v is None:
                return datetime.max
            if isinstance(v, datetime):
                return v
            try:
                return datetime.fromisoformat(str(v))
            except Exception:
                try:
                    return datetime.fromtimestamp(float(v))
                except Exception:
                    return datetime.max

        parsed.sort(key=lambda x: _to_dt(x.get("timestamp")))
        filtered = [p for p in parsed if _is_relevant(p)]

       
        product_names: Dict[str, str] = {}
        pids_to_fetch = set()
        for p in filtered:
            pid = p.get("product_id")
            raw = p.get("raw") or {}
            pname = None
            for k in ("product_name", "produkt_name", "name", "title", "product"):
                if raw.get(k):
                    pname = str(raw.get(k))
                    break
            if not pname:
                pname = _extract_name(p.get("details") or "")
            if not pname and pid:
                pids_to_fetch.add(str(pid))
            if pid and pname:
                product_names[str(pid)] = pname

        if pids_to_fetch and self.db:
            try:
                rows = self.db.find_many_by_ids("products", list(pids_to_fetch))
                for prod in rows or []:
                    pid = prod.get("id")
                    if pid is None:
                        continue
                    name = prod.get("name")
                    if name:
                        product_names[str(pid)] = name
            except Exception:
                pass

        sales = defaultdict(float)
        warehouse_net = defaultdict(float)
        for p in filtered:
            pid = p.get("product_id") or None
            lid = p.get("lager_id") or None
            qty = float(p.get("quantity") or 0)
            if pid and qty < 0:
                sales[pid] += abs(qty)
            if lid:
                warehouse_net[str(lid)] += qty

        top_sales = sorted(sales.items(), key=lambda x: x[1], reverse=True)[:10]
        bottom_sales = sorted(sales.items(), key=lambda x: x[1])[:10]

        
        table_rows: List[List[str]] = []
        running: Dict[Tuple[str, str], float] = defaultdict(float)

        def _resolve_loc(p: Dict) -> str:
            raw = p.get("raw") or {}
            
            for k in ("from", "quelle", "von", "source", "origin", "from_location"):
                v = p.get(k) or raw.get(k)
                if v:
                    return str(v)
            for k in ("to", "ziel", "zu", "target", "destination", "to_location"):
                v = p.get(k) or raw.get(k)
                if v:
                    return str(v)
            
            for k in ("lager_id", "source_lager", "from_warehouse", "ziel_lager", "target_lager", "to_warehouse"):
                v = p.get(k) or raw.get(k)
                if v is not None:
                    try:
                        return report_a.warehouses.get(str(v)) or str(v)
                    except Exception:
                        return str(v)
            return "(nicht angegeben)"

        for p in filtered:
            time_str = _format_ts(p.get("timestamp"))
            pid = p.get("product_id") or ""

          
            pname = None
            if pid:
                pname = product_names.get(str(pid))
            if not pname:
                raw = p.get("raw") or {}
                for k in ("product_name", "produkt_name", "product", "name", "title"):
                    v = raw.get(k)
                    if v:
                        pname = str(v)
                        break
            if not pname:
                pname = _extract_name(p.get("details") or "")
            pname = pname or (f"Produkt {pid}" if pid else "")

            qty = float(p.get("quantity") or 0)
            loc = _resolve_loc(p)
            key = (str(pid), str(loc))
            prev = running.get(key, 0.0)
            curr = prev + qty
            running[key] = curr

            prev_disp = max(0.0, float(prev))
            curr_disp = max(0.0, float(curr))

            try:
                direction = report_a._movement_direction(p.get("raw", {}), qty)
               
                try:
                    if isinstance(direction, str):
                        if "->" in direction:
                            left, right = [s.strip() for s in direction.split("->", 1)]
                            if left in ("(nicht angegeben)", "Nicht angegeben", "") and right:
                                direction = right
                            elif right in ("(nicht angegeben)", "Nicht angegeben", "") and left:
                                direction = left
                        elif direction in ("(nicht angegeben)", "Nicht angegeben", ""):
                            if loc and loc not in ("(nicht angegeben)", ""):
                                direction = loc
                except Exception:
                    pass
            except Exception:
                direction = loc

            table_rows.append([time_str, direction, pname, f"{prev_disp:g}", f"{qty:g}", f"{curr_disp:g}"])

        headers = ["Datum", "Von->Zu", "Produkt", "Vorher", "Änderung", "Nachher"]


        top_names = [product_names.get(pid) or pid for pid, _ in top_sales]
        top_values = [v for _, v in top_sales]
        bottom_names = [product_names.get(pid) or pid for pid, _ in bottom_sales]
        bottom_values = [v for _, v in bottom_sales]

  
        wh_labels: List[str] = []
        wh_values: List[float] = []
        for wid, net in warehouse_net.items():
            val = max(0.0, float(net))
            if val > 0:
                label = None
                try:
                    label = report_a.warehouses.get(str(wid)) if getattr(report_a, "warehouses", None) else None
                except Exception:
                    label = None
                wh_labels.append(label or f"Lager {wid}")
                wh_values.append(val)

        with PdfPages(output_path) as pdf:
            meta = {"Erstellt": datetime.now().strftime("%Y-%m-%d %H:%M")}
            create_cover_page(pdf, "History-Report B (gefiltert)", "Top/Bottom Produkte + Lagerverteilung", meta)

            if top_sales:
                create_bar_chart(pdf, top_names, top_values, "Top 10 Produkte nach Verkaufszahlen")
            if bottom_sales:
                create_bar_chart(pdf, bottom_names, bottom_values, "Bottom 10 Produkte nach Verkaufszahlen")

            if wh_values:
                _create_pie_chart(pdf, wh_labels, wh_values, "Anteil Produkte pro Lager (Netto)")

            create_table_pages(pdf, headers, table_rows, title="Gefilterte History-Einträge (Detail)", fit_one_page=False)
            create_summary_page(pdf, {"Gefilterte Einträge": len(table_rows), "Top-Produkte": len(top_sales)})

        return {"output": str(output_path), "summary": {"total_filtered": len(table_rows), "top_count": len(top_sales), "bottom_count": len(bottom_sales)}, "generated": datetime.now().isoformat()}


if __name__ == "__main__":
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    r = ReportBNeu()
    out = r.generate_report(pathlib.Path(arg) if arg else DEFAULT_OUTPUT_FILE)
    print(json.dumps(out, indent=2))
