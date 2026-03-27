"""Pytest Configuration and Fixtures for B.I.E.R Application Tests."""

import pytest
from bierapp.backend.app import create_app


@pytest.fixture(scope="session")
def app_factory():
    """Create Flask application factory for testing.

    Yields:
        Flask: The Flask application instance.
    """
    app, _, _, _, _ = create_app()
    app.config['TESTING'] = True
    yield app


@pytest.fixture(scope="session")
def client(app_factory):
    """Provide a Flask test client for making requests.

    Args:
        app_factory: The Flask app fixture.

    Returns:
        FlaskClient: The Flask test client.
    """
    return app_factory.test_client()


@pytest.fixture(scope="session")
def services():
    """Provide all application services for testing.

    Yields:
        dict: Dictionary containing all services.
    """
    app, db_service, product_service, warehouse_service, inventory_service = create_app()
    yield {"db": db_service, "products": product_service, "warehouses": warehouse_service, "inventory": inventory_service}

