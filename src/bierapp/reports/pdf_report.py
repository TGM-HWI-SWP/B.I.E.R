"""PDF report helpers for the B.I.E.R web interface.

This module centralizes PDF rendering so Flask routes can stay focused on
input/output handling. Exports include KPI blocks and chart visualizations.
"""

from datetime import datetime
from io import BytesIO
from typing import Dict, List

from reportlab.graphics import renderPDF
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

_PAGE_WIDTH, _PAGE_HEIGHT = A4


def _draw_header(canvas: Canvas, title: str) -> None:
    """Draw the report header at the top of the current PDF page.

    Args:
        canvas: Target PDF canvas.
        title: Main headline shown on the page.
    """
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawString(20 * mm, _PAGE_HEIGHT - 18 * mm, "B.I.E.R - Lagerverwaltung")

    canvas.setFont("Helvetica", 11)
    canvas.drawString(20 * mm, _PAGE_HEIGHT - 26 * mm, title)

    canvas.setLineWidth(0.5)
    canvas.setStrokeColor(colors.HexColor("#9ca3af"))
    canvas.line(20 * mm, _PAGE_HEIGHT - 29 * mm, _PAGE_WIDTH - 20 * mm, _PAGE_HEIGHT - 29 * mm)


def _draw_footer(canvas: Canvas, page_number: int) -> None:
    """Draw a small page footer.

    Args:
        canvas: Target PDF canvas.
        page_number: Current page number.
    """
    footer = f"Seite {page_number}"
    canvas.setFont("Helvetica", 9)
    width = stringWidth(footer, "Helvetica", 9)
    canvas.drawString(_PAGE_WIDTH - 20 * mm - width, 10 * mm, footer)


def _write_wrapped_line(
    canvas: Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    font_name: str = "Helvetica",
    font_size: int = 10,
) -> float:
    """Write wrapped text and return the next Y position.

    Args:
        canvas: Target PDF canvas.
        text: Text to write.
        x: Left X coordinate.
        y: Baseline Y coordinate.
        max_width: Maximum text width before wrapping.
        font_name: Font to use.
        font_size: Font size to use.

    Returns:
        New Y coordinate after writing all wrapped lines.
    """
    canvas.setFont(font_name, font_size)

    words = (text or "").split()
    if not words:
        canvas.drawString(x, y, "")
        return y - 5 * mm

    current = []
    lines = []
    for word in words:
        probe = " ".join(current + [word]).strip()
        probe_width = stringWidth(probe, font_name, font_size)
        if probe_width <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]

    if current:
        lines.append(" ".join(current))

    for line in lines:
        canvas.drawString(x, y, line)
        y -= 5 * mm

    return y


def _finalize_page(canvas: Canvas, page_number: int) -> int:
    """Render footer, flush page, and return incremented page number.

    Args:
        canvas: Target PDF canvas.
        page_number: Current page number.

    Returns:
        Incremented page number.
    """
    _draw_footer(canvas, page_number)
    canvas.showPage()
    return page_number + 1


def _safe_int(value, default: int = 0) -> int:
    """Safely parse integer values used in chart data."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default: float = 0.0) -> float:
    """Safely parse float values used in chart data."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _truncate_label(label: str, length: int = 14) -> str:
    """Reduce overly long chart labels for readability."""
    text = str(label or "-").strip()
    if len(text) <= length:
        return text
    return text[: max(3, length - 1)] + "~"


def _draw_bar_chart(
    canvas: Canvas,
    title: str,
    labels: List[str],
    values: List[float],
    x: float,
    y: float,
    width: float,
    height: float,
    bar_color=colors.HexColor("#2563eb"),
) -> None:
    """Draw a vertical bar chart on a PDF canvas.

    Args:
        canvas: Target PDF canvas.
        title: Section title.
        labels: Category labels.
        values: Numeric values.
        x: Drawing origin X.
        y: Drawing origin Y.
        width: Drawing width.
        height: Drawing height.
        bar_color: Color of the bars.
    """
    drawing = Drawing(width, height)
    drawing.add(String(4, height - 14, title, fontName="Helvetica-Bold", fontSize=10))

    if not labels or not values:
        drawing.add(String(4, height / 2, "Keine Diagrammdaten vorhanden.", fontName="Helvetica-Oblique", fontSize=9))
        renderPDF.draw(drawing, canvas, x, y)
        return

    chart = VerticalBarChart()
    chart.x = 36
    chart.y = 30
    chart.width = max(80, width - 50)
    chart.height = max(60, height - 56)
    chart.data = [[max(0.0, _safe_float(value)) for value in values]]
    chart.barWidth = 10
    chart.barSpacing = 4
    chart.groupSpacing = 8

    max_value = max(chart.data[0]) if chart.data and chart.data[0] else 0.0
    y_max = max(1.0, max_value * 1.2)
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = y_max
    chart.valueAxis.valueStep = max(1.0, round(y_max / 5.0, 2))
    chart.valueAxis.strokeColor = colors.HexColor("#9ca3af")
    chart.valueAxis.labels.fontSize = 7

    chart.categoryAxis.categoryNames = [_truncate_label(label) for label in labels]
    chart.categoryAxis.labels.boxAnchor = "ne"
    chart.categoryAxis.labels.angle = 28
    chart.categoryAxis.labels.dx = -2
    chart.categoryAxis.labels.dy = -2
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.strokeColor = colors.HexColor("#9ca3af")

    chart.bars[0].fillColor = bar_color
    chart.bars[0].strokeColor = bar_color

    drawing.add(chart)
    renderPDF.draw(drawing, canvas, x, y)


def _draw_line_chart(
    canvas: Canvas,
    title: str,
    labels: List[str],
    values: List[float],
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    """Draw a simple trend line chart on a PDF canvas."""
    drawing = Drawing(width, height)
    drawing.add(String(4, height - 14, title, fontName="Helvetica-Bold", fontSize=10))

    if not labels or not values:
        drawing.add(String(4, height / 2, "Keine Diagrammdaten vorhanden.", fontName="Helvetica-Oblique", fontSize=9))
        renderPDF.draw(drawing, canvas, x, y)
        return

    chart = HorizontalLineChart()
    chart.x = 36
    chart.y = 30
    chart.width = max(80, width - 50)
    chart.height = max(60, height - 56)
    chart.data = [[max(0.0, _safe_float(value)) for value in values]]

    max_value = max(chart.data[0]) if chart.data and chart.data[0] else 0.0
    y_max = max(1.0, max_value * 1.2)
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = y_max
    chart.valueAxis.valueStep = max(1.0, round(y_max / 5.0, 2))
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.strokeColor = colors.HexColor("#9ca3af")

    chart.categoryAxis.categoryNames = [_truncate_label(label) for label in labels]
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.boxAnchor = "n"
    chart.categoryAxis.strokeColor = colors.HexColor("#9ca3af")

    chart.lines[0].strokeColor = colors.HexColor("#0ea5e9")
    chart.lines[0].strokeWidth = 2
    chart.lines[0].symbol = None

    drawing.add(chart)
    renderPDF.draw(drawing, canvas, x, y)


def _draw_pie_chart(
    canvas: Canvas,
    title: str,
    labels: List[str],
    values: List[float],
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    """Draw a pie chart for distribution views."""
    drawing = Drawing(width, height)
    drawing.add(String(4, height - 14, title, fontName="Helvetica-Bold", fontSize=10))

    if not labels or not values:
        drawing.add(String(4, height / 2, "Keine Diagrammdaten vorhanden.", fontName="Helvetica-Oblique", fontSize=9))
        renderPDF.draw(drawing, canvas, x, y)
        return

    pie = Pie()
    pie.x = 14
    pie.y = 16
    pie.width = max(80, width - 120)
    pie.height = max(70, height - 48)
    pie.data = [max(0.0, _safe_float(value)) for value in values]
    pie.labels = [_truncate_label(label, 18) for label in labels]
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = colors.white

    palette = [
        colors.HexColor("#2563eb"),
        colors.HexColor("#16a34a"),
        colors.HexColor("#f59e0b"),
        colors.HexColor("#ef4444"),
        colors.HexColor("#8b5cf6"),
        colors.HexColor("#0ea5e9"),
    ]
    for idx, _value in enumerate(pie.data):
        pie.slices[idx].fillColor = palette[idx % len(palette)]

    drawing.add(pie)
    renderPDF.draw(drawing, canvas, x, y)


def _draw_kpi_cards(canvas: Canvas, kpis: List[tuple], y_top: float) -> float:
    """Draw compact KPI cards and return next y position."""
    card_width = (_PAGE_WIDTH - 40 * mm - 10 * mm) / 2
    card_height = 18 * mm
    x_left = 20 * mm
    x_right = x_left + card_width + 10 * mm

    positions = [
        (x_left, y_top - card_height),
        (x_right, y_top - card_height),
        (x_left, y_top - 2 * card_height - 5 * mm),
        (x_right, y_top - 2 * card_height - 5 * mm),
        (x_left, y_top - 3 * card_height - 10 * mm),
        (x_right, y_top - 3 * card_height - 10 * mm),
    ]

    for idx, (label, value) in enumerate(kpis[:6]):
        x, y = positions[idx]
        canvas.setFillColor(colors.HexColor("#f8fafc"))
        canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
        canvas.roundRect(x, y, card_width, card_height, 3 * mm, stroke=1, fill=1)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(x + 4 * mm, y + card_height - 6 * mm, label)
        canvas.setFillColor(colors.HexColor("#0f172a"))
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(x + 4 * mm, y + 5 * mm, str(value))

    return y_top - 3 * card_height - 16 * mm


def build_history_pdf(events: List[Dict]) -> bytes:
    """Build a PDF export for the history page.

    Args:
        events: Event documents to render in chronological order.

    Returns:
        Binary PDF payload.
    """
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=A4)

    page_number = 1
    _draw_header(canvas, "Historienbericht")
    y = _PAGE_HEIGHT - 38 * mm

    if not events:
        y = _write_wrapped_line(
            canvas,
            "Keine Historie-Eintraege vorhanden.",
            20 * mm,
            y,
            _PAGE_WIDTH - 40 * mm,
            "Helvetica-Oblique",
            10,
        )
    else:
        for event in events:
            if y < 25 * mm:
                page_number = _finalize_page(canvas, page_number)
                _draw_header(canvas, "Historienbericht")
                y = _PAGE_HEIGHT - 38 * mm

            timestamp = event.get("display_time") or event.get("timestamp", "-")
            entity = event.get("entity_type", "-")
            action = event.get("action", "-")
            summary = event.get("summary", "")
            actor = event.get("performed_by", "system")

            canvas.setFont("Helvetica-Bold", 10)
            canvas.drawString(20 * mm, y, f"{timestamp} [{entity}/{action}]")
            y -= 5 * mm

            y = _write_wrapped_line(
                canvas,
                f"Akteur: {actor} | {summary}",
                25 * mm,
                y,
                _PAGE_WIDTH - 45 * mm,
            )

    if events:
        page_number = _finalize_page(canvas, page_number)
        _draw_header(canvas, "Historienbericht - Diagramme")

        action_counts = {}
        day_counts = {}
        for event in events:
            action = str(event.get("action", "unknown")).strip() or "unknown"
            action_counts[action] = action_counts.get(action, 0) + 1

            raw_timestamp = str(event.get("timestamp", ""))
            day_key = raw_timestamp[:10] if len(raw_timestamp) >= 10 else "-"
            day_counts[day_key] = day_counts.get(day_key, 0) + 1

        action_labels = list(action_counts.keys())[:8]
        action_values = [action_counts[label] for label in action_labels]

        day_labels = sorted(day_counts.keys())[-7:]
        day_values = [day_counts[label] for label in day_labels]

        _draw_bar_chart(
            canvas,
            "Event-Aktionen (Top)",
            action_labels,
            action_values,
            18 * mm,
            150 * mm,
            174 * mm,
            90 * mm,
            bar_color=colors.HexColor("#7c3aed"),
        )

        _draw_line_chart(
            canvas,
            "Events pro Tag (letzte 7 Tage im Datensatz)",
            day_labels,
            day_values,
            18 * mm,
            40 * mm,
            174 * mm,
            90 * mm,
        )

    _draw_footer(canvas, page_number)
    canvas.save()
    return buffer.getvalue()


def build_statistics_pdf(data: Dict) -> bytes:
    """Build a PDF export for the statistics dashboard.

    Args:
        data: Aggregated KPI and per-warehouse data.

    Returns:
        Binary PDF payload.
    """
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=A4)

    page_number = 1
    _draw_header(canvas, "Statistikbericht")

    kpis = [
        ("Produkte gesamt", data.get("num_produkte", 0)),
        ("Lager gesamt", data.get("num_lager", 0)),
        ("Einheiten gesamt", data.get("total_menge", 0)),
        ("Inventareintraege", data.get("num_inventar", 0)),
        ("Gesamtwert Lager", f"{_safe_float(data.get('total_value', 0.0)):.2f} EUR"),
        ("Niedrigbestand", data.get("low_stock_count", 0)),
    ]

    y_after_cards = _draw_kpi_cards(canvas, kpis, _PAGE_HEIGHT - 40 * mm)

    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(20 * mm, y_after_cards, "Lagerdetails")
    y = y_after_cards - 6 * mm

    warehouse_rows = data.get("lager_stats", [])
    if not warehouse_rows:
        y = _write_wrapped_line(canvas, "- Keine Lagerdaten vorhanden.", 24 * mm, y, _PAGE_WIDTH - 44 * mm)
    else:
        for row in warehouse_rows:
            if y < 25 * mm:
                page_number = _finalize_page(canvas, page_number)
                _draw_header(canvas, "Statistikbericht")
                y = _PAGE_HEIGHT - 38 * mm

            name = row.get("lagername", "-")
            product_count = _safe_int(row.get("produkt_anzahl", 0))
            quantity = _safe_int(row.get("gesamtmenge", 0))
            utilization = _safe_float(row.get("auslastung_pct", 0.0))
            text = (
                f"- {name}: {product_count} Produkte, {quantity} Einheiten, "
                f"Auslastung {utilization:.1f}%"
            )
            y = _write_wrapped_line(canvas, text, 24 * mm, y, _PAGE_WIDTH - 44 * mm)

    if warehouse_rows:
        page_number = _finalize_page(canvas, page_number)
        _draw_header(canvas, "Statistikbericht - Diagramme")

        top_rows = sorted(
            warehouse_rows,
            key=lambda row: _safe_int(row.get("gesamtmenge", 0)),
            reverse=True,
        )[:8]

        qty_labels = [row.get("lagername", "-") for row in top_rows]
        qty_values = [_safe_int(row.get("gesamtmenge", 0)) for row in top_rows]

        util_labels = [row.get("lagername", "-") for row in top_rows]
        util_values = [_safe_float(row.get("auslastung_pct", 0.0)) for row in top_rows]

        _draw_bar_chart(
            canvas,
            "Einheiten je Lager (Top)",
            qty_labels,
            qty_values,
            18 * mm,
            150 * mm,
            174 * mm,
            90 * mm,
            bar_color=colors.HexColor("#0ea5e9"),
        )

        _draw_bar_chart(
            canvas,
            "Auslastung je Lager (%)",
            util_labels,
            util_values,
            18 * mm,
            40 * mm,
            174 * mm,
            90 * mm,
            bar_color=colors.HexColor("#f59e0b"),
        )

    _draw_footer(canvas, page_number)
    canvas.save()
    return buffer.getvalue()


def build_inventory_pdf(inventory_rows: List[Dict], warehouse_name: str) -> bytes:
    """Build a PDF export for product inventory rows.

    Args:
        inventory_rows: Product rows containing name, quantity and optional threshold.
        warehouse_name: Warehouse filter label used in report header.

    Returns:
        Binary PDF payload.
    """
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=A4)

    page_number = 1
    _draw_header(canvas, f"Inventarbericht - {warehouse_name}")
    y = _PAGE_HEIGHT - 38 * mm

    if not inventory_rows:
        y = _write_wrapped_line(
            canvas,
            "Keine Produktdaten fuer den gewaehlten Filter vorhanden.",
            20 * mm,
            y,
            _PAGE_WIDTH - 40 * mm,
        )
    else:
        for row in inventory_rows:
            if y < 25 * mm:
                page_number = _finalize_page(canvas, page_number)
                _draw_header(canvas, f"Inventarbericht - {warehouse_name}")
                y = _PAGE_HEIGHT - 38 * mm

            name = row.get("name", "-")
            quantity = _safe_int(row.get("menge", 0))
            threshold = _safe_int(row.get("mindestbestand", 0))
            line = f"- {name}: Bestand {quantity}"
            if threshold > 0:
                line += f" | Mindestbestand {threshold}"
                if quantity <= threshold:
                    line += " | Niedrigbestand"

            y = _write_wrapped_line(canvas, line, 20 * mm, y, _PAGE_WIDTH - 40 * mm)

    if inventory_rows:
        page_number = _finalize_page(canvas, page_number)
        _draw_header(canvas, f"Inventarbericht - {warehouse_name} - Diagramme")

        top_rows = sorted(
            inventory_rows,
            key=lambda row: _safe_int(row.get("menge", 0)),
            reverse=True,
        )[:8]

        top_labels = [row.get("name", "-") for row in top_rows]
        top_values = [_safe_int(row.get("menge", 0)) for row in top_rows]

        low_stock = 0
        normal_stock = 0
        for row in inventory_rows:
            quantity = _safe_int(row.get("menge", 0))
            threshold = _safe_int(row.get("mindestbestand", 0))
            if threshold > 0 and quantity <= threshold:
                low_stock += 1
            else:
                normal_stock += 1

        _draw_bar_chart(
            canvas,
            "Top Produkte nach Bestand",
            top_labels,
            top_values,
            18 * mm,
            150 * mm,
            174 * mm,
            90 * mm,
            bar_color=colors.HexColor("#16a34a"),
        )

        _draw_pie_chart(
            canvas,
            "Bestandszustand (Niedrigbestand vs OK)",
            ["Niedrigbestand", "OK"],
            [low_stock, normal_stock],
            18 * mm,
            40 * mm,
            174 * mm,
            90 * mm,
        )

    _draw_footer(canvas, page_number)
    canvas.save()
    return buffer.getvalue()
