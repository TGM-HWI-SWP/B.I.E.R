"""UI layer - Flask web interface"""

import os
from flask import Flask, send_from_directory, render_template

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "pictures"))
TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "templates"))

app = Flask(__name__, template_folder=TEMPLATES_DIR)

@app.route("/favicon.ico")
def favicon():
    """Serve the application favicon.

    Returns:
        Response: PNG image response for the browser favicon.
    """
    return send_from_directory(RESOURCES_DIR, "BIER_ICON_COMPRESSED.png", mimetype="image/png")

@app.route("/")
def index():
    """Render the main application page.

    Returns:
        str: Rendered HTML of ``index.html``.
    """
    return render_template("index.html")

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port)
