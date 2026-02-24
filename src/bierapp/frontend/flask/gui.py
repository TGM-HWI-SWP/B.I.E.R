"""UI layer - Flask web interface"""

import os
from flask import Flask, send_from_directory

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "pictures"))

app = Flask(__name__)

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(RESOURCES_DIR, "BIER_ICON_COMPRESSED.png", mimetype="image/png")

@app.route("/")
def index():
    return """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/png" href="/favicon.ico">
    <title>B.I.E.R</title>
</head>
<body>
    <h1>B.I.E.R - Büro-Inventar- und Einkaufs-Register</h1>
    <p>Noch nicht implementiert.</p>
</body>
</html>"""

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port)
