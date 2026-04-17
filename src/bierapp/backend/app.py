"""B.I.E.R Application - Main Flask Application Entry Point."""

import os
from typing import Tuple
from flask import Flask
from bierapp.db.postgress import PostgresRepository
from bierapp.backend.service.db_Service import DbService
from bierapp.backend.service.product_service import ProductService, InventoryService
from bierapp.backend.service.warehouse_service import WarehouseService


def create_app() -> Tuple[Flask, DbService, ProductService, WarehouseService, InventoryService]:
    """Initialize Flask application and all service layers with database connection.

    Returns:
        Tuple[Flask, DbService, ProductService, WarehouseService, InventoryService]: Flask app instance and all initialized services.

    Raises:
        ConnectionError: If database connection fails.
    """
    app = Flask(__name__, template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "resources", "templates")))
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    database_repository = PostgresRepository()
    database_repository.connect()
    database_service = DbService(database_repository)
    product_service = ProductService(database_service)
    inventory_service = InventoryService(database_service)
    warehouse_service = WarehouseService(database_service, inventory_service)
    from bierapp.frontend.flask.gui import register_routes
    register_routes(app, product_service, warehouse_service, inventory_service)

    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle HTTP 400 Bad Request errors.

        Args:
            error: The error object from Flask.

        Returns:
            tuple: JSON error response and HTTP 400 status code.
        """
        from flask import jsonify
        return jsonify({"error": "Bad request", "message": str(error)}), 400

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle HTTP 404 Not Found errors.

        Args:
            error: The error object from Flask.

        Returns:
            tuple: JSON error response and HTTP 404 status code.
        """
        from flask import jsonify
        return jsonify({"error": "Not found", "message": str(error)}), 404

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle HTTP 500 Internal Server errors.

        Args:
            error: The error object from Flask.

        Returns:
            tuple: JSON error response and HTTP 500 status code.
        """
        from flask import jsonify
        return jsonify({"error": "Internal server error", "message": str(error)}), 500

    return app, database_service, product_service, warehouse_service, inventory_service


if __name__ == "__main__":
    app_instance, _, _, _, _ = create_app()
    app_instance.run(debug=True, host="0.0.0.0", port=5000)

