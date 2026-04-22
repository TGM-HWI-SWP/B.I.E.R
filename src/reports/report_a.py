from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import pathlib
import shlex
from datetime import datetime
from bierapp.contracts import ReportPort

from matplotlib.backends.backend_pdf import PdfPages

from bierapp.db.postgress import PostgresRepository
from reports.report_format import create_cover_page, create_table_pages, create_summary_page


DEFAULT_OUTPUT_FILE = pathlib.Path("report_a.pdf")


class ReportAHelpers:
    """Container for parsing and table-building helpers previously at module level.

    All methods are `@staticmethod` so they can be used without instantiating.
    """

    @staticmethod
    def find_int_after_key(details: str, key: str, allow_negative: bool = False) -> Optional[int]:
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

    @staticmethod
    def find_all_ints_after_key(details: str, key: str) -> List[int]:
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
            val = ReportAHelpers.find_int_after_key(details[pos + len(k):], '', allow_negative=False)
            if val is not None:
                result.append(val)
            start = pos + len(k)
        return result

    @staticmethod
    def first_int_in_slice(s: str) -> Optional[int]:
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

    @staticmethod
    def find_von_nach_numbers(details: str) -> Optional[Tuple[Optional[int], Optional[int]]]:
        if not details:
            return None
        low = details.lower()
        vpos = low.find('von')
        npos = low.find('nach')
        if vpos == -1 or npos == -1 or npos <= vpos:
            return None
        between = details[vpos + 3:npos]
        after = details[npos + 4:]
        a = ReportAHelpers.first_int_in_slice(between)
        b = ReportAHelpers.first_int_in_slice(after)
        return (a, b)

    @staticmethod
    def find_lager_numbers(details: str) -> List[int]:
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
            num = ReportAHelpers.first_int_in_slice(tail[i:])
            if num is not None:
                res.append(num)
            start = pos + len('lager')
        return res

    @staticmethod
    def find_text_von_nach(details: str) -> Optional[Tuple[str, str]]:
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

    @staticmethod
    def extract_name(details: str) -> Optional[str]:
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
                    return tok.split('=', 1)[1].strip().strip('"\'')
        except Exception:
            pass
        pos = low.find('name=')
        if pos != -1:
            tail = details[pos + 5:].lstrip()
            if tail and tail[0] in ('"', "'"):
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
                return tail.split()[0].strip() if tail.split() else None
        k = low.find('produktname')
        if k != -1:
            for sep in (':', '='):
                si = details.find(sep, k)
                if si != -1:
                    tail = details[si + 1:]
                    for s in ('\n', ',', ';'):
                        j = tail.find(s)
                        if j != -1:
                            tail = tail[:j]
                    val = tail.strip()
                    if val:
                        return val
        return None

    @staticmethod
    def parse_history_row(row: Dict) -> Dict:
        details = row.get("details") or ""
        action = row.get("action")
        entry_type = row.get("entry_type")
        created_at = row.get("created_at")

        
        pid = None
        lid = None
        menge = None
        try:
            tokens = shlex.split(details)
            for i, tok in enumerate(tokens):
                if '=' in tok:
                    k, v = tok.split('=', 1)
                    k = k.lower().strip()
                    v = v.strip().strip('"\'')
                    if k in ('produkt_id', 'product_id', 'pid') and v.isdigit():
                        pid = v
                    if k in ('lager_id', 'lagerid', 'lid') and v.isdigit():
                        lid = v
                    if k in ('menge', 'quantity', 'qty'):
                        try:
                            menge = int(v)
                        except Exception:
                            pass
                else:
                    low = tok.lower().strip(',:')
                    if low in ('menge', 'quantity', 'qty') and i + 1 < len(tokens):
                        nxt = tokens[i + 1].strip(',:')
                        if nxt.lstrip('-').isdigit():
                            try:
                                menge = int(nxt)
                            except Exception:
                                pass
                    if low in ('produkt', 'product') and i + 1 < len(tokens):
                        nxt = tokens[i + 1].strip(',:')
                        if nxt.isdigit():
                            pid = nxt
        except Exception:
            pass

        
        try:
            if row.get('product_id'):
                pid = pid or str(row.get('product_id'))
            if row.get('lager_id'):
                lid = lid or str(row.get('lager_id'))
            if row.get('quantity') is not None and menge is None:
                menge = int(row.get('quantity'))
        except Exception:
            pass

        qty = menge if menge is not None else None

        raw = dict(row) if isinstance(row, dict) else {"raw": row}
        
        try:
            lids = ReportAHelpers.find_all_ints_after_key(details, "lager_id=")
            if len(lids) >= 2:
                raw.setdefault("source_lager", int(lids[0]))
                raw.setdefault("target_lager", int(lids[1]))
                raw.setdefault("from", int(lids[0]))
                raw.setdefault("to", int(lids[1]))
            else:
                s = ReportAHelpers.find_int_after_key(details, "source_lager=")
                t = ReportAHelpers.find_int_after_key(details, "target_lager=")
                if s is not None:
                    raw.setdefault("source_lager", int(s))
                    raw.setdefault("from", int(s))
                if t is not None:
                    raw.setdefault("target_lager", int(t))
                    raw.setdefault("to", int(t))
                if not raw.get("from") and not raw.get("to"):
                    nums = ReportAHelpers.find_von_nach_numbers(details)
                    if nums:
                        a, b = nums
                        if a is not None:
                            raw.setdefault("from", int(a))
                            raw.setdefault("source_lager", int(a))
                        if b is not None:
                            raw.setdefault("to", int(b))
                            raw.setdefault("target_lager", int(b))
                if not raw.get("from") and not raw.get("to"):
                    lids2 = ReportAHelpers.find_lager_numbers(details)
                    if len(lids2) >= 2:
                        raw.setdefault("from", int(lids2[0]))
                        raw.setdefault("to", int(lids2[1]))
                        raw.setdefault("source_lager", int(lids2[0]))
                        raw.setdefault("target_lager", int(lids2[1]))
                if not raw.get("from") and not raw.get("to"):
                    names = ReportAHelpers.find_text_von_nach(details)
                    if names:
                        left, right = names
                        if left:
                            raw.setdefault("from", left)
                        if right:
                            raw.setdefault("to", right)
        except Exception:
            pass

        return {"timestamp": created_at, "entry_type": entry_type, "action": action, "details": details, "product_id": pid, "lager_id": lid, "quantity": qty, "raw": raw}

    @staticmethod
    def format_ts(ts) -> str:
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

    @staticmethod
    def is_relevant(parsed: Dict) -> bool:
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

    @staticmethod
    def load_warehouses_from_db(db_repo: Optional[object]) -> Dict[str, str]:
        res: Dict[str, str] = {}
        if not db_repo:
            return res
        try:
            rows = db_repo.find_all("warehouses") or []
            for w in rows:
                wid = w.get("id") or w.get("lager_id") or w.get("warehouse_id")
                if wid is None:
                    continue
                name = (
                    w.get("name")
                    or w.get("lagername")
                    or w.get("lager_name")
                    or w.get("bezeichnung")
                    or w.get("label")
                    or w.get("lager")
                    or w.get("warehouse")
                    or wid
                )
                res[str(wid)] = str(name)
        except Exception:
            return {}
        return res

    @staticmethod
    def movement_direction(raw: Dict, quantity: float, warehouses: Dict[str, str]) -> str:
        if not isinstance(raw, dict):
            raw = {}
        keys = {
            "from": ("from", "quelle", "von", "source", "origin", "from_location"),
            "to": ("to", "ziel", "zu", "target", "destination", "to_location"),
            "from_id": ("lager_id", "source_lager", "from_warehouse"),
            "to_id": ("ziel_lager", "target_lager", "to_warehouse"),
        }
        def resolve(side: str):
            for k in keys[side]:
                v = raw.get(k)
                if v:
                    return str(v)
            return None
        src = resolve("from") or None
        dst = resolve("to") or None
        try:
            if src and isinstance(warehouses, dict):
                mapped = warehouses.get(str(src))
                if mapped:
                    src = mapped
            if dst and isinstance(warehouses, dict):
                mapped = warehouses.get(str(dst))
                if mapped:
                    dst = mapped
        except Exception:
            pass
        if not src:
            src_id = resolve("from_id")
            if src_id:
                src = warehouses.get(str(src_id)) or str(src_id)
        if not dst:
            dst_id = resolve("to_id")
            if dst_id:
                dst = warehouses.get(str(dst_id)) or str(dst_id)
        if not src and not dst:
            return "Nicht angegeben"
        src = src or "(nicht angegeben)"
        dst = dst or "(nicht angegeben)"
        return f"{src} -> {dst}"

    @staticmethod
    def build_table_rows(filtered: List[Dict], warehouses: Dict[str, str], product_names: Dict[str, str]) -> Tuple[List[str], List[List[str]]]:
        rows: List[List[str]] = []
        running: Dict[Tuple[str, str], float] = {}

        def _resolve_loc(p: Dict) -> str:
            raw = p.get('raw') or {}
            for k in ('from', 'quelle', 'von', 'source', 'origin', 'from_location'):
                v = p.get(k) or raw.get(k)
                if v:
                    return str(v)
            for k in ('to', 'ziel', 'zu', 'target', 'destination', 'to_location'):
                v = p.get(k) or raw.get(k)
                if v:
                    return str(v)
            for k in ('lager_id', 'source_lager', 'from_warehouse', 'ziel_lager', 'target_lager', 'to_warehouse'):
                v = p.get(k) or raw.get(k)
                if v is not None:
                    try:
                        return warehouses.get(str(v)) or str(v)
                    except Exception:
                        return str(v)
            return '(nicht angegeben)'

        for p in filtered:
            t = ReportAHelpers.format_ts(p.get('timestamp'))
            pid = p.get('product_id') or ''
            pname = (product_names.get(str(pid)) if pid else None) or (p.get('raw') or {}).get('product_name') or (p.get('raw') or {}).get('produkt_name') or ReportAHelpers.extract_name(p.get('details') or '') or (f'Produkt {pid}' if pid else '')
            qty = float(p.get('quantity') or 0)
            loc = _resolve_loc(p)
            key = (str(pid), str(loc))
            prev = running.get(key, 0.0)
            curr = prev + qty
            running[key] = curr
            prev_disp = max(0.0, float(prev)); curr_disp = max(0.0, float(curr))
            try:
                direction = ReportAHelpers.movement_direction(p.get('raw', {}), qty, warehouses)
                if isinstance(direction, str):
                    if '->' in direction:
                        l, r = [s.strip() for s in direction.split('->', 1)]
                        if l in ('(nicht angegeben)', 'Nicht angegeben', '') and r:
                            direction = r
                        elif r in ('(nicht angegeben)', 'Nicht angegeben', '') and l:
                            direction = l
                    elif direction in ('(nicht angegeben)', 'Nicht angegeben', '') and loc and loc not in ('(nicht angegeben)', ''):
                        direction = loc
            except Exception:
                direction = loc
            rows.append([t, direction, pname, f"{prev_disp:g}", f"{qty:g}", f"{curr_disp:g}"])
        headers = ['Datum', 'Von->Zu', 'Produkt', 'Vorher', 'Änderung', 'Nachher']
        return headers, rows


def _find_all_ints_after_key(details: str, key: str) -> List[int]:
    return ReportAHelpers.find_all_ints_after_key(details, key)


def _first_int_in_slice(s: str) -> Optional[int]:
    return ReportAHelpers.first_int_in_slice(s)


def _find_von_nach_numbers(details: str) -> Optional[Tuple[Optional[int], Optional[int]]]:
    return ReportAHelpers.find_von_nach_numbers(details)


def _find_lager_numbers(details: str) -> List[int]:
    return ReportAHelpers.find_lager_numbers(details)


def _find_text_von_nach(details: str) -> Optional[Tuple[str, str]]:
    return ReportAHelpers.find_text_von_nach(details)


def _extract_name(details: str) -> Optional[str]:
    return ReportAHelpers.extract_name(details)


def _parse_history_row(row: Dict) -> Dict:
    return ReportAHelpers.parse_history_row(row)


def _format_ts(ts) -> str:
    return ReportAHelpers.format_ts(ts)


def _is_relevant(parsed: Dict) -> bool:
    return ReportAHelpers.is_relevant(parsed)


def _load_warehouses_from_db(db_repo: Optional[object]) -> Dict[str, str]:
    return ReportAHelpers.load_warehouses_from_db(db_repo)


def _movement_direction(raw: Dict, quantity: float, warehouses: Dict[str, str]) -> str:
    return ReportAHelpers.movement_direction(raw, quantity, warehouses)


def build_table_rows(filtered: List[Dict], warehouses: Dict[str, str], product_names: Dict[str, str]) -> Tuple[List[str], List[List[str]]]:
    return ReportAHelpers.build_table_rows(filtered, warehouses, product_names)


class ReportA(ReportPort):
    """Report A (neu): PDF with cover, table pages and a short summary."""

    def __init__(self, db_repo: Optional[object] = None):
        self.db = db_repo or (PostgresRepository() if PostgresRepository else None)
        
        try:
            self.warehouses = _load_warehouses_from_db(self.db)
        except Exception:
            self.warehouses = {}

    def _movement_direction(self, raw: Dict, quantity: float) -> str:
        """Instance wrapper so callers can use `report_a._movement_direction(raw, qty)`.

        Delegates to the module helper but provides the instance's warehouses map.
        """
        try:
            return _movement_direction(raw, quantity, getattr(self, "warehouses", {}) or {})
        except Exception:
            try:
                return _movement_direction(raw, quantity, {})
            except Exception:
                return "Nicht angegeben"

    def generate_report(self, output_path: pathlib.Path = DEFAULT_OUTPUT_FILE) -> Dict:
        try:
            if getattr(self.db, 'connect', None):
                self.db.connect()
        except Exception:
            self.db = None

        try:
            history_rows = self.db.find_all('history') if getattr(self, 'db', None) else []
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

        parsed.sort(key=lambda x: _to_dt(x.get('timestamp')))
        filtered = [p for p in parsed if _is_relevant(p)]

       
        product_names: Dict[str, str] = {}
        pids_to_fetch = set()
        name_keys = ('product_name', 'produkt_name', 'name', 'title', 'product')
        for p in filtered:
            pid = p.get('product_id')
            raw = p.get('raw') or {}
            pname = next((str(raw.get(k)) for k in name_keys if raw.get(k)), None) or _extract_name(p.get('details') or '')
            if not pname and pid:
                pids_to_fetch.add(str(pid))
            if pid and pname:
                product_names[str(pid)] = pname

        if pids_to_fetch and self.db and getattr(self.db, 'find_many_by_ids', None):
            try:
                rows = self.db.find_many_by_ids('products', list(pids_to_fetch))
                for r in rows or []:
                    pid = r.get('id')
                    if pid is None:
                        continue
                    name = r.get('name')
                    if name:
                        product_names[str(pid)] = name
            except Exception:
                pass

        sales = defaultdict(float)
        warehouse_net = defaultdict(float)
        for p in filtered:
            pid = p.get('product_id') or None
            lid = p.get('lager_id') or None
            qty = float(p.get('quantity') or 0)
            if pid and qty < 0:
                sales[pid] += abs(qty)
            if lid:
                warehouse_net[str(lid)] += qty

        top_sales = sorted(sales.items(), key=lambda x: x[1], reverse=True)[:10]
        bottom_sales = sorted(sales.items(), key=lambda x: x[1])[:10]

        
        try:
            self.warehouses = _load_warehouses_from_db(self.db)
        except Exception:
            self.warehouses = {}
        warehouses = self.warehouses

        headers, table_rows = build_table_rows(filtered, warehouses, product_names)

      
        try:
            with PdfPages(output_path) as pdf:
                meta = {"Erstellt": datetime.now().strftime("%Y-%m-%d %H:%M")}
                create_cover_page(pdf, "Lagerbewegungen", "", meta)
                create_table_pages(pdf, headers, table_rows, title="Lagerbewegungen", fit_one_page=False)
                create_summary_page(pdf, {"Gefilterte Einträge": len(table_rows), "Top-Produkte": len(top_sales)})
        except Exception as e:
            return {"output": None, "error": str(e), "generated": datetime.now().isoformat()}

        return {"output": str(output_path), "summary": {"total_filtered": len(table_rows), "top_count": len(top_sales), "bottom_count": len(bottom_sales)}, "generated": datetime.now().isoformat()}

    def inventory_report(self, lager_id: str) -> List[Dict]:
        """Return current inventory for a given warehouse id.

        Builds running totals from history and aggregates by product for the
        specified `lager_id`.
        """
        try:
            rows = self.db.find_all('history') if getattr(self, 'db', None) else []
        except Exception:
            rows = []

        parsed = [_parse_history_row(r) for r in rows]

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

        parsed.sort(key=lambda x: _to_dt(x.get('timestamp')))
        filtered = [p for p in parsed if _is_relevant(p)]

        inv: Dict[str, float] = {}
        lid_str = str(lager_id)
        for p in filtered:
            pid = p.get('product_id')
            if not pid:
                continue
            qty = float(p.get('quantity') or 0)
            raw = p.get('raw') or {}

           
            if str(p.get('lager_id')) == lid_str:
                inv[pid] = inv.get(pid, 0.0) + qty
                continue

            try:
                src = raw.get('from') or raw.get('source_lager') or raw.get('source')
                dst = raw.get('to') or raw.get('target_lager') or raw.get('target')
                if src is not None and str(src) == lid_str:
                    inv[pid] = inv.get(pid, 0.0) - qty
                    continue
                if dst is not None and str(dst) == lid_str:
                    inv[pid] = inv.get(pid, 0.0) + qty
                    continue
            except Exception:
                pass

          
            try:
                lids = _find_all_ints_after_key(p.get('details') or '', 'lager_id=')
                for ids in lids:
                    if str(ids) == lid_str:
                        inv[pid] = inv.get(pid, 0.0) + qty
                        break
            except Exception:
                pass

        product_names: Dict[str, str] = {}
        try:
            if getattr(self, 'db', None) and getattr(self.db, 'find_many_by_ids', None):
                rows = self.db.find_many_by_ids('products', list(inv.keys()))
                for r in rows or []:
                    pid = r.get('id')
                    if pid is None:
                        continue
                    name = r.get('name')
                    if name:
                        product_names[str(pid)] = name
        except Exception:
            pass

        out: List[Dict] = []
        for pid, amt in inv.items():
            out.append({'product_id': str(pid), 'product_name': product_names.get(str(pid)) or f'Produkt {pid}', 'menge': amt})
        return out

    def statistics_report(self) -> Dict:
        """Return aggregated statistics matching `ReportPort` expectations."""
        stats = {'total_products': 0, 'total_warehouses': 0, 'total_stock_units': 0}
        try:
            if getattr(self, 'db', None):
                prods = self.db.find_all('products') or []
                whs = self.db.find_all('warehouses') or []
                stats['total_products'] = len(prods)
                stats['total_warehouses'] = len(whs)
        except Exception:
            pass

        try:
            total = 0.0
            wh_ids = []
            try:
                whs = self.db.find_all('warehouses') or []
                for w in whs:
                    wid = w.get('id') or w.get('lager_id')
                    if wid is not None:
                        wh_ids.append(str(wid))
            except Exception:
                wh_ids = []

            for wid in wh_ids:
                inv = self.inventory_report(wid)
                for item in inv:
                    try:
                        total += float(item.get('menge') or 0)
                    except Exception:
                        pass
            stats['total_stock_units'] = total
        except Exception:
            pass

        return stats


if __name__ == "__main__":
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    r = ReportA()
    out = r.generate_report(pathlib.Path(arg) if arg else DEFAULT_OUTPUT_FILE)
    import json
    print(json.dumps(out, indent=2))
