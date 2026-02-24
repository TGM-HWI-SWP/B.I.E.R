"""UI layer - Flask web interface"""

import os
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "<h1>Lagerverwaltung Bürobedarf</h1><p>Noch nicht implementiert.</p>"

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port)
