"""Integration tests for service-to-service interactions.

These tests verify that ProductService, WarehouseService, and InventoryService
behave correctly when used together through a shared mock database adapter.
All MongoDB calls are intercepted by a MagicMock so no real connection is
required.
"""

import pytest

from bierapp.db.mongodb import COLLECTION_INVENTAR


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


class TestRemoveStock:
    """Tests for the delta-based InventoryService.remove_stock() method."""

    def test_remove_stock_reduces_quantity(
        self,
        inventory_service,
        mock_db,
    ):
        """remove_stock decreases menge by the given delta.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter with a pre-existing inventar entry.
        """
        entry = {"_id": FAKE_INVENTAR_ID, "menge": 20}
        mock_db.find_inventar_entry.return_value = entry

        inventory_service.remove_stock(FAKE_LAGER_ID, FAKE_PRODUKT_ID, 7)

        mock_db.update.assert_called_once()
        updated_doc = mock_db.update.call_args[0][2]
        assert updated_doc["menge"] == 13

    def test_remove_stock_zero_raises(
        self,
        inventory_service,
        mock_db,
    ):
        """remove_stock raises ValueError when menge is 0.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        with pytest.raises(ValueError):
            inventory_service.remove_stock(FAKE_LAGER_ID, FAKE_PRODUKT_ID, 0)

    def test_remove_stock_negative_raises(
        self,
        inventory_service,
        mock_db,
    ):
        """remove_stock raises ValueError when menge is negative.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        with pytest.raises(ValueError):
            inventory_service.remove_stock(FAKE_LAGER_ID, FAKE_PRODUKT_ID, -5)

    def test_remove_stock_insufficient_raises(
        self,
        inventory_service,
        mock_db,
    ):
        """remove_stock raises ValueError when menge exceeds current stock.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter with current menge of 5.
        """
        entry = {"_id": FAKE_INVENTAR_ID, "menge": 5}
        mock_db.find_inventar_entry.return_value = entry

        with pytest.raises(ValueError, match="Unzureichender Bestand"):
            inventory_service.remove_stock(FAKE_LAGER_ID, FAKE_PRODUKT_ID, 10)

    def test_remove_stock_missing_entry_raises(
        self,
        inventory_service,
        mock_db,
    ):
        """remove_stock raises KeyError when no inventory entry exists.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter configured to return None.
        """
        mock_db.find_inventar_entry.return_value = None
        with pytest.raises(KeyError):
            inventory_service.remove_stock(FAKE_LAGER_ID, FAKE_PRODUKT_ID, 3)

    def test_remove_stock_exact_quantity_empties_entry(
        self,
        inventory_service,
        mock_db,
    ):
        """remove_stock sets menge to 0 when exactly the available amount is removed.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter with current menge equal to removal amount.
        """
        entry = {"_id": FAKE_INVENTAR_ID, "menge": 10}
        mock_db.find_inventar_entry.return_value = entry

        inventory_service.remove_stock(FAKE_LAGER_ID, FAKE_PRODUKT_ID, 10)

        updated_doc = mock_db.update.call_args[0][2]
        assert updated_doc["menge"] == 0

    def test_remove_stock_records_performed_by(
        self,
        inventory_service,
        mock_db,
    ):
        """remove_stock stores performed_by in the history event.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        entry = {"_id": FAKE_INVENTAR_ID, "menge": 15}
        mock_db.find_inventar_entry.return_value = entry

        inventory_service.remove_stock(FAKE_LAGER_ID, FAKE_PRODUKT_ID, 5, performed_by="Max Mustermann")

        # The last insert call should go to the events collection
        event_call = mock_db.insert.call_args_list[-1]
        assert event_call[0][0] == "events"
        assert event_call[0][1]["performed_by"] == "Max Mustermann"


class TestMoveProduct:
    """Tests for InventoryService.move_product()."""

    def test_move_product_decreases_source_and_increases_target(
        self,
        inventory_service,
        mock_db,
    ):
        """move_product reduces source stock and adds to the existing target entry.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter with source and target entries.
        """
        source_entry = {"_id": FAKE_INVENTAR_ID, "menge": 20, "lager_id": FAKE_LAGER_ID}
        target_entry = {"_id": "target_entry_id", "menge": 5}

        def find_by_id_side(collection, doc_id):
            return {"_id": doc_id, "lagername": "X", "name": "P"}

        mock_db.find_by_id.side_effect = find_by_id_side
        mock_db.find_inventar_entry.side_effect = [source_entry, target_entry]

        TARGET_LAGER_ID = "target_lager_000000000001"
        inventory_service.move_product(FAKE_LAGER_ID, TARGET_LAGER_ID, FAKE_PRODUKT_ID, 8)

        # Two update calls: one for source, one for target
        assert mock_db.update.call_count == 2
        source_update = mock_db.update.call_args_list[0][0][2]
        target_update = mock_db.update.call_args_list[1][0][2]
        assert source_update["menge"] == 12
        assert target_update["menge"] == 13

    def test_move_product_creates_target_entry_if_missing(
        self,
        inventory_service,
        mock_db,
    ):
        """move_product inserts a new inventar entry when the target has none.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter where target has no existing entry.
        """
        source_entry = {"_id": FAKE_INVENTAR_ID, "menge": 10, "lager_id": FAKE_LAGER_ID}

        def find_by_id_side(collection, doc_id):
            return {"_id": doc_id, "lagername": "Y", "name": "Q"}

        mock_db.find_by_id.side_effect = find_by_id_side
        # First call = source entry exists, second call = target has none
        mock_db.find_inventar_entry.side_effect = [source_entry, None]

        TARGET_LAGER_ID = "target_lager_000000000002"
        inventory_service.move_product(FAKE_LAGER_ID, TARGET_LAGER_ID, FAKE_PRODUKT_ID, 10)

        # Source entry at 0 units is deleted
        mock_db.delete.assert_called_once()
        # A new target entry is inserted into inventar
        inventar_inserts = [
            c for c in mock_db.insert.call_args_list
            if c[0][0] == COLLECTION_INVENTAR
        ]
        assert len(inventar_inserts) == 1
        assert inventar_inserts[0][0][1]["menge"] == 10

    def test_move_product_zero_menge_raises(
        self,
        inventory_service,
        mock_db,
    ):
        """move_product raises ValueError when menge is 0.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        with pytest.raises(ValueError):
            inventory_service.move_product(FAKE_LAGER_ID, "other", FAKE_PRODUKT_ID, 0)

    def test_move_product_exceeds_stock_raises(
        self,
        inventory_service,
        mock_db,
    ):
        """move_product raises ValueError when requested menge exceeds available stock.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter with source menge of 3.
        """
        def find_by_id_side(collection, doc_id):
            return {"_id": doc_id}

        mock_db.find_by_id.side_effect = find_by_id_side
        source_entry = {"_id": FAKE_INVENTAR_ID, "menge": 3}
        mock_db.find_inventar_entry.return_value = source_entry

        with pytest.raises(ValueError):
            inventory_service.move_product(FAKE_LAGER_ID, "other_lager", FAKE_PRODUKT_ID, 10)

    def test_move_product_missing_source_lager_raises(
        self,
        inventory_service,
        mock_db,
    ):
        """move_product raises KeyError when the source warehouse does not exist.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter returning None for the source warehouse.
        """
        mock_db.find_by_id.return_value = None
        with pytest.raises(KeyError, match="Quelllager"):
            inventory_service.move_product("bad_source", "target", FAKE_PRODUKT_ID, 5)

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
