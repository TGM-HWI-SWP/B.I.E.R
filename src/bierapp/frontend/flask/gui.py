"""UI layer - Flask web interface"""

import os
from flask import Flask, send_from_directory, render_template, jsonify, request

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "pictures"))
TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "templates"))

app = Flask(__name__, template_folder=TEMPLATES_DIR)

@app.route("/products", methods=["GET"])
def get_products():
    # TODO: echte DB später
    return jsonify([
        {"id": 1, "name": "Bier 1"},
        {"id": 2, "name": "Bier 2"}
    ])

@app.route("/products", methods=["POST"])
def create_product():
    data = request.json
    print("Produkt erhalten:", data)
    return jsonify({"status": "ok"}), 201

@app.route("/warehouses", methods=["GET"])
def get_warehouses():
    return jsonify([
        {
            "id": 1,
            "lagername": "Lager A",
            "adresse": "Wien",
            "products": 10,
            "max_plaetze": 100
        }
    ])

@app.route("/warehouses/<int:id>", methods=["DELETE"])
def delete_warehouse(id):
    print("Lösche Lager:", id)
    return "", 204


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

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port)
