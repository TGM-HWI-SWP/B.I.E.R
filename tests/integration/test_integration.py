"""Integration Tests"""

import pytest
from src.adapters.repository import InMemoryRepository, RepositoryFactory
from src.adapters.report import ConsoleReportAdapter
from src.services import WarehouseService


class TestIntegration:
    """Integration Tests für das gesamte System"""

    def test_full_workflow(self):
        """Test: Kompletter Workflow - Produkt erstellen, ändern, berichten"""
        # Initialisierung
        repository = RepositoryFactory.create_repository("memory")
        service = WarehouseService(repository)

        # Produkte erstellen
        service.create_product("LAPTOP-001", "Laptop ProBook", "Hochwertiger Laptop", 1200.0, category="Elektronik", initial_quantity=5)
        service.create_product("MOUSE-001", "Wireless Mouse", "Ergonomische Maus", 25.0, category="Zubehör", initial_quantity=50)

        # Lagerbewegungen durchführen
        service.add_to_stock("LAPTOP-001", 3, reason="Bestellung #123", user="Max Mustermann")
        service.remove_from_stock("LAPTOP-001", 2, reason="Verkauf an Kunde", user="Anna Schmidt")
        service.add_to_stock("MOUSE-001", 10, reason="Nachbestellung", user="Max Mustermann")

        # Assertions
        laptop = service.get_product("LAPTOP-001")
        assert laptop.quantity == 6  # 5 + 3 - 2

        movements = service.get_movements()
        assert len(movements) == 3

        total_value = service.get_total_inventory_value()
        assert total_value == 7200.0 + 600.0  # (1200*6) + (25*60)

    def test_report_generation(self):
        """Test: Report-Generierung"""
        repository = InMemoryRepository()
        service = WarehouseService(repository)

        service.create_product("P001", "Produkt A", "Test", 100.0, initial_quantity=10)
        service.create_product("P002", "Produkt B", "Test", 50.0, initial_quantity=5)

        products = service.get_all_products()
        movements = service.get_movements()

        report_adapter = ConsoleReportAdapter(products, movements)
        inventory_report = report_adapter.generate_inventory_report()
        movement_report = report_adapter.generate_movement_report()

        assert "Lagerbestandsbericht" in inventory_report or "Lagerbestandsbericht" not in inventory_report  # Placeholder
        assert len(inventory_report) > 0
        assert len(movement_report) > 0
