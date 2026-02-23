"""UI Layer - Gradio Web Interface"""

import gradio as gr

with gr.Blocks(title="Lagerverwaltung") as app:
    gr.Markdown("# Lagerverwaltung – Bürobedarf")
    gr.Markdown("🚧 Businesslogik wird noch implementiert.")

app.launch(server_name="0.0.0.0", server_port=7860)
