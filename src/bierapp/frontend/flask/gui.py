"""UI layer - Flask web interface"""

import os
from flask import Flask, send_from_directory, render_template, request

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "pictures"))
TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "templates"))
STYLESHEETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "stylesheet"))

app = Flask(__name__, template_folder=TEMPLATES_DIR)


def _list_stylesheets() -> list[str]:
    """Return available stylesheet files from the stylesheet directory.
    
    Returns:
        list[str]: Sorted list of stylesheet filenames (CSS files) available for selection.
    """
    names = [
        name for name in os.listdir(STYLESHEETS_DIR)
        if name.lower().endswith(".css") and os.path.isfile(os.path.join(STYLESHEETS_DIR, name))
    ]
    names.sort(key=lambda name: (name != "common.css", name.lower()))
    return names


def _selected_stylesheet(stylesheets: list[str]) -> str:
    """Resolve selected stylesheet from query params with validation.
    
    Args:
        stylesheets: List of available stylesheet filenames for validation.
    
    Returns:
        str: Validated stylesheet filename to use for rendering."""
    requested = request.args.get("theme", "", type=str).strip()
    if requested in stylesheets:
        return requested
    if "common.css" in stylesheets:
        return "common.css"
    return stylesheets[0] if stylesheets else "common.css"


def _render_page(template_name: str):
    """Render a template with shared stylesheet selection context.
    Args:
        template_name: Name of the template file to render.
    
    Returns:
        str: Rendered HTML of the specified template.
    """
    stylesheets = _list_stylesheets()
    selected_theme = _selected_stylesheet(stylesheets)
    return render_template(template_name, theme_options=stylesheets, selected_theme=selected_theme)

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
    return _render_page("index.html")

@app.route("/page1")
def page1():
    """Render the second application page.

    Returns:
        str: Rendered HTML of ``page1.html``.
    """
    return _render_page("page1.html")

@app.route("/page2")
def page2():
    """Render the third application page.

    Returns:
        str: Rendered HTML of ``page2.html``.
    """
    return _render_page("page2.html")


@app.route("/page3")
def page3():
    """Render the statistics page (UI demo).

    Returns:
        str: Rendered HTML of ``page3.html``.
    """
    return _render_page("page3.html")

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port)
