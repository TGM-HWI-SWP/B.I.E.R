"""UI Layer - Gradio Web Interface"""

import gradio as gr

from src.adapters.repository import RepositoryFactory
from src.services import WarehouseService

repository = RepositoryFactory.create_repository("memory")
service = WarehouseService(repository)

COLS = ["ID", "Name", "Kategorie", "Bestand", "Preis (€)", "Gesamtwert (€)"]


def _rows():
    return [[p.id, p.name, p.category, p.quantity, f"{p.price:.2f}", f"{p.get_total_value():.2f}"]
            for p in service.get_all_products().values()]


def add_product(pid, name, desc, price, qty, cat):
    try:
        service.create_product(pid, name, desc, float(price), cat, int(qty))
        return "Produkt hinzugefügt.", _rows()
    except Exception as e:
        return f"Fehler: {e}", _rows()


def add_stock(pid, qty, reason):
    try:
        service.add_to_stock(pid, int(qty), reason)
        return "Bestand erhöht.", _rows()
    except Exception as e:
        return f"Fehler: {e}", _rows()


def remove_stock(pid, qty, reason):
    try:
        service.remove_from_stock(pid, int(qty), reason)
        return "Bestand verringert.", _rows()
    except Exception as e:
        return f"Fehler: {e}", _rows()


with gr.Blocks(title="Lagerverwaltung") as app:
    gr.Markdown("# Lagerverwaltung – Bürobedarf")

    with gr.Tab("Produkte"):
        tbl = gr.Dataframe(headers=COLS, value=_rows, interactive=False)
        gr.Button("Aktualisieren").click(_rows, outputs=tbl)

    with gr.Tab("Produkt anlegen"):
        pid  = gr.Textbox(label="Produkt-ID")
        name = gr.Textbox(label="Name")
        desc = gr.Textbox(label="Beschreibung")
        pri  = gr.Number(label="Preis (€)", value=0.0)
        qty  = gr.Number(label="Menge", value=0, precision=0)
        cat  = gr.Textbox(label="Kategorie")
        msg  = gr.Textbox(label="Status", interactive=False)
        tbl2 = gr.Dataframe(headers=COLS, interactive=False)
        gr.Button("Anlegen").click(add_product, inputs=[pid, name, desc, pri, qty, cat], outputs=[msg, tbl2])

    with gr.Tab("Wareneingang"):
        wi_id  = gr.Textbox(label="Produkt-ID")
        wi_qty = gr.Number(label="Menge", value=1, precision=0)
        wi_rsn = gr.Textbox(label="Grund")
        wi_msg = gr.Textbox(label="Status", interactive=False)
        tbl3   = gr.Dataframe(headers=COLS, interactive=False)
        gr.Button("Einbuchen").click(add_stock, inputs=[wi_id, wi_qty, wi_rsn], outputs=[wi_msg, tbl3])

    with gr.Tab("Warenausgang"):
        wa_id  = gr.Textbox(label="Produkt-ID")
        wa_qty = gr.Number(label="Menge", value=1, precision=0)
        wa_rsn = gr.Textbox(label="Grund")
        wa_msg = gr.Textbox(label="Status", interactive=False)
        tbl4   = gr.Dataframe(headers=COLS, interactive=False)
        gr.Button("Ausbuchen").click(remove_stock, inputs=[wa_id, wa_qty, wa_rsn], outputs=[wa_msg, tbl4])


app.launch(server_name="0.0.0.0", server_port=7860)
