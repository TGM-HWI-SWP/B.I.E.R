from typing import List, Dict, Optional
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime
from PIL import Image
from pathlib import Path


def _add_page_border(fig, color: str = "black", linewidth: float = 1.2, margin: float = 0.04):
    try:
        rect = Rectangle((margin, margin), 1 - 2 * margin, 1 - 2 * margin, fill=False, edgecolor=color, linewidth=linewidth)
        rect.set_transform(fig.transFigure)
        fig.patches.append(rect)
    except Exception:
        pass


def create_cover_page(pdf: PdfPages, title: str, subtitle: str, meta: Optional[Dict[str, str]] = None) -> None:
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("#f7f7f7")

    _add_page_border(fig, color="#000000", linewidth=1.2, margin=0.04)

    title_y = 0.78
    try:
        logo_path = Path(__file__).resolve().parents[2] / "resources" / "pictures" / "BIER_LOGO_WEISS_COMPRESSED.png"
        if logo_path.exists():
            img = Image.open(logo_path)
            img_w, img_h = img.size
            width_frac = 0.32
            aspect = img_h / img_w
            img_width = width_frac
            img_height = img_width * aspect
            bottom = 0.68
            if bottom + img_height > 0.94:
                bottom = 0.94 - img_height
            left = max(0.02, 0.5 - img_width / 2)
            ax_img = fig.add_axes([left, bottom, img_width, img_height])
            ax_img.imshow(img, aspect='auto', alpha=0.95)
            ax_img.axis('off')
            title_y = bottom - 0.06
            
    except Exception:
        pass
    plt.axis("off")
    fig.text(0.5, title_y, title, ha="center", fontsize=28, weight="bold")
    fig.text(0.5, title_y - 0.06, subtitle, ha="center", fontsize=12)
    if meta:
        y = title_y - 0.12
        for k, v in meta.items():
            fig.text(0.15, y, f"{k}: {v}", fontsize=10)
            y -= 0.035
    fig.text(0.15, 0.18, "Dieser Bericht wurde automatisch erstellt.", fontsize=8, color="#555555")
    pdf.savefig(fig)
    plt.close(fig)


def create_table_pages(pdf: PdfPages, headers: List[str], rows: List[List[str]], title: Optional[str] = None, rows_per_page: int = 40, fit_one_page: bool = False) -> None:
    """Render table rows into one or more A4 pages.

    If `fit_one_page` is True, try to fit all rows onto a single A4 portrait page by
    reducing font size and spacing. This is a best-effort heuristic suitable for
    text tables (monospace) and works for moderate row counts.
    """

    total_pages = (len(rows) + rows_per_page - 1) // rows_per_page or 1
    margin = 0.06
    # keep table drawing area large; draw a thinner frame instead of shrinking the table
    frame_margin = 0.02
    for page in range(total_pages):
        start = page * rows_per_page
        end = start + rows_per_page
        page_rows = rows[start:end]

        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        _add_page_border(fig, margin=frame_margin)
        ax.axis("off")
        if title:
            ax.set_title(title, fontsize=12, loc="left")
        try:
            cell_text = [[str(c) for c in r] for r in page_rows]
            ncols = len(headers)

            if ncols >= 3:
                if ncols == 5:
                    col_widths = [0.18, 0.44, 0.12, 0.13, 0.13]
                elif ncols == 6:
                    col_widths = [0.14, 0.34, 0.20, 0.10, 0.11, 0.11]
                else:
                    first = 0.14
                    second = 0.34
                    rest = max(0.03, (1.0 - first - second) / max(1, ncols - 2))
                    col_widths = [first, second] + [rest] * (ncols - 2)
            else:
                col_widths = [1.0 / ncols] * ncols

            table = ax.table(cellText=cell_text, colLabels=headers, loc="center", cellLoc="left", colWidths=col_widths, bbox=[0.0, 0.02, 1.0, 0.96])
            table.auto_set_font_size(False)

            # choose a sensible font size depending on column count
            font_size = 9 if ncols <= 4 else (8 if ncols == 5 else 7)
            table.set_fontsize(font_size)

            # scale the table conservatively so it fits A4; reduce vertical scale if many rows
            vscale = 1.15
            if len(page_rows) > rows_per_page:
                vscale = max(0.8, 1.15 * rows_per_page / max(1, len(page_rows)))
            table.scale(1, vscale)
        except Exception:

            y = 0.92
            header_line = "  ".join([h.ljust(30) for h in headers])
            ax.text(0.05, y, header_line, fontfamily="monospace", fontsize=9)
            y -= 0.03
            for r in page_rows:
                line = "  ".join([str(c)[:30].ljust(30) for c in r])
                ax.text(0.05, y, line, fontfamily="monospace", fontsize=8)
                y -= 0.025
                if y < 0.05:
                    break

        fig.text(0.5, margin / 2, f"Seite {page+1} von {total_pages}", ha="center", fontsize=8, color="#666666")
        try:
            fig.tight_layout(rect=[margin, margin, 1 - margin, 1 - margin])
        except Exception:
            pass
        pdf.savefig(fig)
        plt.close(fig)


def create_bar_chart(pdf: PdfPages, names: List[str], values: List[float], title: str) -> None:
    # If no data present, render a clear placeholder page instead of an empty chart.
    if not names or not values or all((v == 0 or v is None) for v in values):
        fig = plt.figure(figsize=(8.27, 11.69))
        plt.axis("off")
        _add_page_border(fig)
        fig.suptitle(title, fontsize=14, weight="bold", y=0.9)
        plt.text(0.5, 0.6, "Keine Daten verfügbar", ha="center", va="center", fontsize=12, color="#333333")
        plt.text(0.5, 0.55, "Für diesen Zeitraum wurden keine Werte gefunden.", ha="center", va="center", fontsize=10, color="#666666")
        pdf.savefig(fig)
        plt.close(fig)
        return

    fig = plt.figure(figsize=(8.27, 11.69))
    _add_page_border(fig)
    fig.suptitle(title, fontsize=14, weight="bold", y=0.92)
    ax = fig.add_axes([0.12, 0.32, 0.76, 0.55])
    ax.barh(range(len(names))[::-1], values, color="#2b7bba")
    ax.set_yticks(range(len(names))[::-1])
    ax.set_yticklabels(names)
    ax.set_xlabel("Einheiten")
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def create_pie_chart(pdf: PdfPages, labels: List[str], values: List[float], title: str) -> None:
    # Render a placeholder when no meaningful data present
    if not labels or not values or all((v == 0 or v is None) for v in values):
        fig = plt.figure(figsize=(8.27, 11.69))
        plt.axis("off")
        _add_page_border(fig)
        fig.suptitle(title, fontsize=14, weight="bold", y=0.9)
        plt.text(0.5, 0.6, "Keine Daten verfügbar", ha="center", va="center", fontsize=12, color="#333333")
        plt.text(0.5, 0.55, "Für dieses Lager wurden keine Bestände gefunden.", ha="center", va="center", fontsize=10, color="#666666")
        pdf.savefig(fig)
        plt.close(fig)
        return

    fig = plt.figure(figsize=(8.27, 11.69))
    _add_page_border(fig)
    fig.suptitle(title, fontsize=14, weight="bold", y=0.92)
    ax = fig.add_axes([0.18, 0.3, 0.64, 0.5])
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.axis("equal")
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def create_summary_page(pdf: PdfPages, summary: Dict[str, object]) -> None:
    fig = plt.figure(figsize=(8.27, 11.69))
    plt.axis("off")
    _add_page_border(fig)
    plt.text(0.1, 0.9, "Zusammenfassung", fontsize=16, weight="bold")
    y = 0.82
    for k, v in summary.items():
        plt.text(0.1, y, f"{k}: {v}", fontsize=10)
        y -= 0.035
        if y < 0.1:
            break
    pdf.savefig(fig)
    plt.close(fig)
