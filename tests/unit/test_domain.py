"""Tests - Unit Tests für die Geschäftslogik"""

import pytest
from src.domain.product import Product
from src.adapters.repository import InMemoryRepository
from src.services import WarehouseService


class TestProduct:
    """Tests für die Product-Klasse"""

    def test_product_creation(self):
        """Test: Produkt erstellen"""
        product = Product(
            id="P001",
            name="Test Produkt",
            description="Ein Test",
            price=10.0,
            quantity=5,
        )
        assert product.id == "P001"
        assert product.name == "Test Produkt"
        assert product.quantity == 5

    def test_product_validation_negative_price(self):
        """Test: Produkt mit negativem Preis sollte fehlschlagen"""
        with pytest.raises(ValueError):
            Product(
                id="P001",
                name="Test",
                description="Test",
                price=-10.0,
            )

    def test_update_quantity(self):
        """Test: Bestand aktualisieren"""
        product = Product(
            id="P001",
            name="Test",
            description="Test",
            price=10.0,
            quantity=10,
        )
        product.update_quantity(5)
        assert product.quantity == 15

        product.update_quantity(-5)
        assert product.quantity == 10

    def test_update_quantity_insufficient(self):
        """Test: Bestand kann nicht negativ werden"""
        product = Product(
            id="P001",
            name="Test",
            description="Test",
            price=10.0,
            quantity=5,
        )
        with pytest.raises(ValueError):
            product.update_quantity(-10)

    def test_get_total_value(self):
        """Test: Gesamtwert berechnen"""
        product = Product(
            id="P001",
            name="Test",
            description="Test",
            price=10.0,
            quantity=5,
        )
        assert product.get_total_value() == 50.0


class TestWarehouseService:
    """Tests für WarehouseService"""

    @pytest.fixture
    def service(self):
        """Fixture für WarehouseService mit In-Memory Repository"""
        repository = InMemoryRepository()
        return WarehouseService(repository)

    def test_create_product(self, service):
        """Test: Produkt über Service erstellen"""
        product = service.create_product(
            product_id="P001",
            name="Test Produkt",
            description="Ein Test",
            price=15.0,
            category="Test",
            initial_quantity=10,
        )
        assert product.id == "P001"
        assert product.quantity == 10

    def test_add_to_stock(self, service):
        """Test: Bestand erhöhen"""
        service.create_product("P001", "Test", "Test", 10.0, initial_quantity=5)
        service.add_to_stock("P001", 3, reason="Neuer Einkauf")

        product = service.get_product("P001")
        assert product.quantity == 8

    def test_remove_from_stock(self, service):
        """Test: Bestand verringern"""
        service.create_product("P001", "Test", "Test", 10.0, initial_quantity=10)
        service.remove_from_stock("P001", 3, reason="Verkauf")

        product = service.get_product("P001")
        assert product.quantity == 7

    def test_remove_from_stock_insufficient(self, service):
        """Test: Nicht genug Bestand zum Entnehmen"""
        service.create_product("P001", "Test", "Test", 10.0, initial_quantity=5)

        with pytest.raises(ValueError):
            service.remove_from_stock("P001", 10)

    def test_get_all_products(self, service):
        """Test: Alle Produkte abrufen"""
        service.create_product("P001", "Produkt 1", "Test", 10.0)
        service.create_product("P002", "Produkt 2", "Test", 20.0)

        products = service.get_all_products()
        assert len(products) == 2

    def test_get_total_inventory_value(self, service):
        """Test: Gesamtwert des Lagers berechnen"""
        service.create_product("P001", "Test 1", "Test", 10.0, initial_quantity=5)
        service.create_product("P002", "Test 2", "Test", 20.0, initial_quantity=3)

        total = service.get_total_inventory_value()
        assert total == 110.0  # (10*5) + (20*3)

    def test_get_movements(self, service):
        """Test: Lagerbewegungen abrufen"""
        service.create_product("P001", "Test", "Test", 10.0, initial_quantity=5)
        service.add_to_stock("P001", 3)
        service.remove_from_stock("P001", 2)

        movements = service.get_movements()
        assert len(movements) == 2
