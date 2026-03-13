"""UI layer - Flask web interface"""

import os
from flask import Flask, send_from_directory, render_template

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "pictures"))
TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "templates"))
STYLESHEETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "stylesheet"))

app = Flask(__name__, template_folder=TEMPLATES_DIR)

@app.route("/favicon.ico")
def favicon():
    """Serve the application favicon.

    Returns:
        Response: PNG image response for the browser favicon.
    """
    return send_from_directory(RESOURCES_DIR, "BIER_ICON_COMPRESSED.png", mimetype="image/png")


@app.route("/stylesheets/<path:filename>")
def stylesheet(filename: str):
    """Serve shared CSS stylesheets.

    Args:
        filename: Relative path inside the stylesheets directory.

    Returns:
        Response: CSS file response.
    """
    return send_from_directory(STYLESHEETS_DIR, filename, mimetype="text/css")

@app.route("/")
def index():
    """Render the main application page.

    Returns:
        str: Rendered HTML of ``index.html``.
    """
    return render_template("index.html")

@app.route("/page1")
def page1():
    """Render the second application page.

    Returns:
        str: Rendered HTML of ``page1.html``.
    """
    return render_template("page1.html")


@app.route("/page2")
def page2():
    """Render the third application page.

    Returns:
        str: Rendered HTML of ``page2.html``.
    """
    return render_template("page2.html")


@app.route("/page3")
def page3():
    """Render the statistics page (UI demo).

    Returns:
        str: Rendered HTML of ``page3.html``.
    """
    return render_template("page3.html")

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port)
