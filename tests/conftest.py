"""Shared pytest fixtures for the B.I.E.R test suite."""

from os import path
from unittest.mock import MagicMock

from bierapp.backend.services import InventoryService, ProductService, WarehouseService
from bierapp.frontend.flask.gui import app as flask_app
from pytest import fixture


@fixture
def mock_db():
    """Return a MagicMock that mimics MongoDBAdapter.

    Returns:
        MagicMock: Pre-configured mock database adapter.
    """
    db = MagicMock()
    db.find_all.return_value = []
    db.find_by_id.return_value = None
    db.find_inventory_entry.return_value = None
    db.find_inventory_by_warehouse.return_value = []
    db.insert.return_value = "507f1f77bcf86cd799439011"
    db.update.return_value = True
    db.delete.return_value = True
    return db


@fixture
def product_service(mock_db):
    """Return a ProductService wired to the mock database.

    Args:
        mock_db (MagicMock): Injected mock database adapter.

    Returns:
        ProductService: Service under test.
    """
    return ProductService(mock_db)


@fixture
def warehouse_service(mock_db):
    """Return a WarehouseService wired to the mock database.

    Args:
        mock_db (MagicMock): Injected mock database adapter.

    Returns:
        WarehouseService: Service under test.
    """
    return WarehouseService(mock_db)


@fixture
def inventory_service(mock_db):
    """Return an InventoryService wired to the mock database.

    Args:
        mock_db (MagicMock): Injected mock database adapter.

    Returns:
        InventoryService: Service under test.
    """
    return InventoryService(mock_db)


@fixture
def flask_client(mock_db, monkeypatch):
    """Return a Flask test client with all services mocked.

    In addition to monkeypatching the database adapter, this fixture also
    points the Flask app to the project-local template and static resource
    directories so that TemplateNotFound errors do not depend on the
    installed wheel layout during tests.

    Args:
        mock_db (MagicMock): Injected mock database adapter.
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        FlaskClient: Test client for the B.I.E.R Flask application.
    """
    import bierapp.frontend.flask.gui as gui_module

    # Wire mock DB into the GUI module
    monkeypatch.setattr(gui_module, "_db", mock_db)

    # Point templates/resources to the source-tree paths instead of the
    # installed package location so Jinja2 can find the HTML files.
    project_root = path.abspath(path.join(path.dirname(__file__), ".."))
    resources_dir = path.join(project_root, "src", "resources")
    pictures_dir = path.join(resources_dir, "pictures")
    templates_dir = path.join(resources_dir, "templates")

    gui_module.RESOURCES_DIR = pictures_dir
    gui_module.TEMPLATES_DIR = templates_dir
    flask_app.template_folder = templates_dir

    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    with flask_app.test_client() as client:
        yield client
