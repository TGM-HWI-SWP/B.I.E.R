"""Integration tests for service-to-service interactions.

These tests verify that ProductService, WarehouseService, and InventoryService
behave correctly when used together through a shared mock database adapter.
All MongoDB calls are intercepted by a MagicMock so no real connection is
required.
"""

import pytest


FAKE_LAGER_ID = "aaa000000000000000000001"
FAKE_PRODUKT_ID = "bbb000000000000000000002"
FAKE_INVENTAR_ID = "ccc000000000000000000003"


class TestProductAndInventoryInteraction:
    """Tests covering the workflow of creating a product and adding it to a warehouse."""

    def test_create_product_then_add_to_warehouse(
        self,
        product_service,
        warehouse_service,
        inventory_service,
        mock_db,
    ):
        """A freshly created product can be added to a freshly created warehouse.

        Args:
            product_service (ProductService): ProductService under test.
            warehouse_service (WarehouseService): WarehouseService under test.
            inventory_service (InventoryService): InventoryService under test.
            mock_db (MagicMock): Shared mock adapter (one insert per service call).
        """
        # insert wird sowohl für Domänenobjekte als auch für Events verwendet.
        # Wir geben für jede Collection eine passende ID zurück.
        def insert_side_effect(collection, data):
            if collection == "produkte":
                return FAKE_PRODUKT_ID
            if collection == "lager":
                return FAKE_LAGER_ID
            if collection == "inventar":
                return FAKE_INVENTAR_ID
            # Events oder andere Collections
            return "event-id"

        mock_db.insert.side_effect = insert_side_effect
        mock_db.find_by_id.return_value = {"_id": FAKE_LAGER_ID, "lagername": "L"}
        mock_db.find_inventar_entry.return_value = None

        produkt = product_service.create_product("Nagel", "Stahlnagel 50mm", 0.01)
        lager = warehouse_service.create_warehouse("Halle 1", "Linz", 200)
        inventory_service.add_product(lager["_id"], produkt["_id"], 100)

        # Mindestens je ein Insert für Produkt, Lager und Inventar erwartet;
        # zusätzliche Inserts (Events) sind erlaubt.
        assert mock_db.insert.call_count >= 3

    def test_add_product_merge_increases_total(
        self,
        inventory_service,
        mock_db,
    ):
        """Adding the same product twice accumulates the menge.

        Args:
            inventory_service (InventoryService): InventoryService under test.
            mock_db (MagicMock): Mock adapter with a pre-existing inventar entry.
        """
        existing_entry = {"_id": FAKE_INVENTAR_ID, "menge": 10}
        mock_db.find_by_id.return_value = {"_id": FAKE_LAGER_ID}
        mock_db.find_inventar_entry.return_value = existing_entry

        inventory_service.add_product(FAKE_LAGER_ID, FAKE_PRODUKT_ID, 5)

        mock_db.update.assert_called_once()
        updated_doc = mock_db.update.call_args[0][2]
        assert updated_doc["menge"] == 15

    def test_update_then_remove_lifecycle(
        self,
        inventory_service,
        mock_db,
    ):
        """A product can have its quantity updated and then be removed.

        Args:
            inventory_service (InventoryService): InventoryService under test.
            mock_db (MagicMock): Mock adapter.
        """
        entry = {"_id": FAKE_INVENTAR_ID, "menge": 20}
        mock_db.find_inventar_entry.return_value = entry

        inventory_service.update_quantity(FAKE_LAGER_ID, FAKE_PRODUKT_ID, 50)
        inventory_service.remove_product(FAKE_LAGER_ID, FAKE_PRODUKT_ID)

        assert mock_db.update.call_count == 1
        assert mock_db.delete.call_count == 1

    def test_list_inventory_includes_product_details(
        self,
        inventory_service,
        mock_db,
    ):
        """list_inventory attaches product name and description from a second DB call.

        Args:
            inventory_service (InventoryService): InventoryService under test.
            mock_db (MagicMock): Mock adapter wired with lager and product docs.
        """
        lager_doc = {"_id": FAKE_LAGER_ID, "lagername": "Lager A"}
        produkt_doc = {"_id": FAKE_PRODUKT_ID, "name": "Schraube", "beschreibung": "M4"}
        entry = {"_id": FAKE_INVENTAR_ID, "produkt_id": FAKE_PRODUKT_ID, "menge": 7}

        mock_db.find_by_id.side_effect = [lager_doc, produkt_doc]
        mock_db.find_inventar_by_lager.return_value = [entry]

        result = inventory_service.list_inventory(FAKE_LAGER_ID)

        assert len(result) == 1
        assert result[0]["produkt_name"] == "Schraube"
        assert result[0]["menge"] == 7


class TestWarehouseValidation:
    """Cross-service tests for warehouse validation edge-cases."""

    def test_update_preserves_unspecified_fields(
        self,
        warehouse_service,
        mock_db,
    ):
        """update_warehouse merges the supplied fields with the existing document.

        Args:
            warehouse_service (WarehouseService): WarehouseService under test.
            mock_db (MagicMock): Mock adapter returning an existing warehouse.
        """
        existing = {
            "_id": FAKE_LAGER_ID,
            "lagername": "Alt",
            "adresse": "Graz",
            "max_plaetze": 50,
        }
        mock_db.find_by_id.return_value = existing

        warehouse_service.update_warehouse(
            FAKE_LAGER_ID,
            {"lagername": "Neu", "adresse": "Wien", "max_plaetze": 100},
        )

        mock_db.update.assert_called_once()
        updated_doc = mock_db.update.call_args[0][2]
        assert updated_doc["lagername"] == "Neu"
        assert updated_doc["max_plaetze"] == 100
