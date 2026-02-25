"""Shared pytest fixtures for the B.I.E.R test suite."""

from unittest.mock import MagicMock

import pytest

from bierapp.backend.services import InventoryService, ProductService, WarehouseService
from bierapp.frontend.flask.gui import app as flask_app


@pytest.fixture
def mock_db():
    """Return a MagicMock that mimics MongoDBAdapter.

    Returns:
        MagicMock: Pre-configured mock database adapter.
    """
    db = MagicMock()
    db.find_all.return_value = []
    db.find_by_id.return_value = None
    db.find_inventar_entry.return_value = None
    db.find_inventar_by_lager.return_value = []
    db.insert.return_value = "507f1f77bcf86cd799439011"
    db.update.return_value = True
    db.delete.return_value = True
    return db


@pytest.fixture
def product_service(mock_db):
    """Return a ProductService wired to the mock database.

    Args:
        mock_db (MagicMock): Injected mock database adapter.

    Returns:
        ProductService: Service under test.
    """
    return ProductService(mock_db)


@pytest.fixture
def warehouse_service(mock_db):
    """Return a WarehouseService wired to the mock database.

    Args:
        mock_db (MagicMock): Injected mock database adapter.

    Returns:
        WarehouseService: Service under test.
    """
    return WarehouseService(mock_db)


@pytest.fixture
def inventory_service(mock_db):
    """Return an InventoryService wired to the mock database.

    Args:
        mock_db (MagicMock): Injected mock database adapter.

    Returns:
        InventoryService: Service under test.
    """
    return InventoryService(mock_db)


@pytest.fixture
def flask_client(mock_db, monkeypatch):
    """Return a Flask test client with all services mocked.

    Args:
        mock_db (MagicMock): Injected mock database adapter.
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        FlaskClient: Test client for the B.I.E.R Flask application.
    """
    import bierapp.frontend.flask.gui as gui_module
    monkeypatch.setattr(gui_module, "_db", mock_db)
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    with flask_app.test_client() as client:
        yield client
