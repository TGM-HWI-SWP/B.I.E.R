from typing import List, Dict, Optional
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime
from PIL import Image


def create_cover_page(pdf: PdfPages, title: str, subtitle: str, meta: Optional[Dict[str, str]] = None) -> None:
    fig = plt.figure(figsize=(8.27, 11.69))
    img = Image.open("../reports/logo/bierapp_logo.png")
    fig.patch.set_facecolor("#f7f7f7")
    plt.axis("off")
    plt.text(0.5, 0.78, title, ha="center", fontsize=28, weight="bold")
    plt.text(0.5, 0.72, subtitle, ha="center", fontsize=12)
    if meta:
        y = 0.6
        for k, v in meta.items():
            plt.text(0.15, y, f"{k}: {v}", fontsize=10)
            y -= 0.035
    plt.imshow(img, aspect="equal")
    plt.text(0.15, 0.2, "Dieser Bericht wurde automatisch erstellt.", fontsize=8, color="#555555")
    pdf.savefig(fig)
    plt.close(fig)


def create_table_pages(pdf: PdfPages, headers: List[str], rows: List[List[str]], title: Optional[str] = None, rows_per_page: int = 40, fit_one_page: bool = False) -> None:
    """Render table rows into one or more A4 pages.

    If `fit_one_page` is True, try to fit all rows onto a single A4 portrait page by
    reducing font size and spacing. This is a best-effort heuristic suitable for
    text tables (monospace) and works for moderate row counts.
    """

    total_pages = (len(rows) + rows_per_page - 1) // rows_per_page or 1
    for page in range(total_pages):
        start = page * rows_per_page
        end = start + rows_per_page
        page_rows = rows[start:end]

        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")
        if title:
            ax.set_title(title, fontsize=12, loc="left")
        try:
            cell_text = [[str(c) for c in r] for r in page_rows]
            ncols = len(headers)

            if ncols >= 3:
                if ncols == 5:
                    col_widths = [0.18, 0.44, 0.12, 0.13, 0.13]
                else:
                    first = 0.25
                    second = 0.45
                    rest = max(0.05, (1.0 - first - second) / max(1, ncols - 2))
                    col_widths = [first, second] + [rest] * (ncols - 2)
            else:
                col_widths = [1.0 / ncols] * ncols

            table = ax.table(cellText=cell_text, colLabels=headers, loc="center", cellLoc="left", colWidths=col_widths)
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.scale(1, 1.2)
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

        ax.text(0.5, 0.03, f"Seite {page+1} von {total_pages}", ha="center", fontsize=8, color="#666666")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)


def create_barh_chart(pdf: PdfPages, names: List[str], values: List[float], title: str) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 5))
    ax.barh(range(len(names))[::-1], values, color="#2b7bba")
    ax.set_yticks(range(len(names))[::-1])
    ax.set_yticklabels(names)
    ax.set_xlabel("Einheiten")
    ax.set_title(title)
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def create_summary_page(pdf: PdfPages, summary: Dict[str, object]) -> None:
    fig = plt.figure(figsize=(8.27, 11.69))
    plt.axis("off")
    plt.text(0.1, 0.9, "Zusammenfassung", fontsize=16, weight="bold")
    y = 0.82
    for k, v in summary.items():
        plt.text(0.1, y, f"{k}: {v}", fontsize=10)
        y -= 0.035
        if y < 0.1:
            break
    pdf.savefig(fig)
    plt.close(fig)
