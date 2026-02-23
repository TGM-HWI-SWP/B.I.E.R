"""UI layer - Gradio web interface"""

import gradio as gr

with gr.Blocks(title="Lagerverwaltung") as app:
    gr.Markdown("# Inventory Management - Office Supplies")
    gr.Markdown("Business logic is not yet implemented.")

app.launch(server_name="0.0.0.0", server_port=7860)
