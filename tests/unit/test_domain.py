"""Unit tests for ProductService, WarehouseService and InventoryService.

All MongoDB interactions are replaced by a MagicMock so no real database
connection is required.
"""

from pytest import raises


class TestProductService:
    """Tests for ProductService business logic."""

    def test_create_product_returns_doc_with_id(self, product_service, mock_db):
        """create_product inserts a document and returns it with _id set.

        Args:
            product_service (ProductService): Service under test.
            mock_db (MagicMock): Mock adapter (checks insert was called).
        """
        result = product_service.create_product("Tisch", "Bürotisch", 15.5)
        assert mock_db.insert.call_args_list[0][0][0] == "produkte"
        assert result["name"] == "Tisch"
        assert result["beschreibung"] == "Bürotisch"
        assert result["gewicht"] == 15.5
        assert "_id" in result

    def test_create_product_strips_whitespace(self, product_service):
        """create_product trims leading/trailing whitespace from name.

        Args:
            product_service (ProductService): Service under test.
        """
        result = product_service.create_product("  Stuhl  ", "", 0.0)
        assert result["name"] == "Stuhl"

    def test_create_product_empty_name_raises(self, product_service):
        """create_product raises ValueError for an empty name.

        Args:
            product_service (ProductService): Service under test.
        """
        with raises(ValueError, match="leer"):
            product_service.create_product("   ", "", 1.0)

    def test_create_product_negative_price_raises(self, product_service):
        """create_product raises ValueError when preis is negative.

        Args:
            product_service (ProductService): Service under test.
        """
        with raises(ValueError, match="Preis"):
            product_service.create_product("Regal", "", 1.0, price=-5.0)

    def test_create_product_stores_preis(self, product_service, mock_db):
        """create_product persists the preis field in the product document.

        Args:
            product_service (ProductService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        result = product_service.create_product("Stuhl", "Bürostuhl", 8.5, price=129.99)
        # The doc inserted into the DB must contain preis
        inserted_doc = mock_db.insert.call_args_list[0][0][1]
        assert inserted_doc["preis"] == 129.99
        assert result["preis"] == 129.99

    def test_create_product_default_preis_is_zero(self, product_service, mock_db):
        """create_product defaults preis to 0.0 when not specified.

        Args:
            product_service (ProductService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        result = product_service.create_product("Haken", "", 0.1)
        assert result["preis"] == 0.0


    def test_get_product_delegates_to_db(self, product_service, mock_db):
        """get_product forwards the call to find_by_id.

        Args:
            product_service (ProductService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        mock_db.find_by_id.return_value = {"_id": "abc", "name": "X"}
        result = product_service.get_product("abc")
        mock_db.find_by_id.assert_called_once()
        assert result["name"] == "X"

    def test_list_products_delegates_to_db(self, product_service, mock_db):
        """list_products returns whatever find_all returns.

        Args:
            product_service (ProductService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        mock_db.find_all.return_value = [{"name": "A"}, {"name": "B"}]
        result = product_service.list_products()
        assert len(result) == 2

    def test_update_product_raises_for_missing(self, product_service, mock_db):
        """update_product raises KeyError when the product does not exist.

        Args:
            product_service (ProductService): Service under test.
            mock_db (MagicMock): Mock adapter configured to return None.
        """
        mock_db.find_by_id.return_value = None
        with raises(KeyError):
            product_service.update_product("nonexistent", {"name": "X"})

    def test_update_product_calls_db_update(self, product_service, mock_db):
        """update_product calls db.update and returns the refreshed doc.

        Args:
            product_service (ProductService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        mock_db.find_by_id.return_value = {"_id": "abc", "name": "Alt", "beschreibung": "", "gewicht": 1.0}
        product_service.update_product("abc", {"name": "Neu"})
        mock_db.update.assert_called_once()

    def test_delete_product_calls_db_delete(self, product_service, mock_db):
        """delete_product deletes the document when it exists.

        Args:
            product_service (ProductService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        mock_db.find_by_id.return_value = {"_id": "abc", "name": "X"}
        product_service.delete_product("abc")
        mock_db.delete.assert_called_once()

    def test_delete_product_raises_for_missing(self, product_service, mock_db):
        """delete_product raises KeyError when the product does not exist.

        Args:
            product_service (ProductService): Service under test.
            mock_db (MagicMock): Mock adapter configured to return None.
        """
        mock_db.find_by_id.return_value = None
        with raises(KeyError):
            product_service.delete_product("gone")


class TestWarehouseService:
    """Tests for WarehouseService business logic."""

    def test_create_warehouse_returns_doc(self, warehouse_service, mock_db):
        """create_warehouse persists and returns the new warehouse document.

        Args:
            warehouse_service (WarehouseService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        result = warehouse_service.create_warehouse("Lager A", "Wien 1010", 50)
        assert mock_db.insert.call_args_list[0][0][0] == "lager"
        assert result["lagername"] == "Lager A"
        assert result["max_plaetze"] == 50

    def test_create_warehouse_empty_name_raises(self, warehouse_service):
        """create_warehouse raises ValueError for an empty lagername.

        Args:
            warehouse_service (WarehouseService): Service under test.
        """
        with raises(ValueError, match="leer"):
            warehouse_service.create_warehouse("  ", "Adresse", 10)

    def test_create_warehouse_zero_plaetze_raises(self, warehouse_service):
        """create_warehouse raises ValueError when max_plaetze is zero.

        Args:
            warehouse_service (WarehouseService): Service under test.
        """
        with raises(ValueError, match="positiv"):
            warehouse_service.create_warehouse("Lager B", "", 0)

    def test_create_warehouse_negative_plaetze_raises(self, warehouse_service):
        """create_warehouse raises ValueError when max_plaetze is negative.

        Args:
            warehouse_service (WarehouseService): Service under test.
        """
        with raises(ValueError, match="positiv"):
            warehouse_service.create_warehouse("Lager C", "", -5)

    def test_update_warehouse_raises_for_missing(self, warehouse_service, mock_db):
        """update_warehouse raises KeyError when the warehouse does not exist.

        Args:
            warehouse_service (WarehouseService): Service under test.
            mock_db (MagicMock): Mock adapter configured to return None.
        """
        mock_db.find_by_id.return_value = None
        with raises(KeyError):
            warehouse_service.update_warehouse("x", {"lagername": "Y"})

    def test_delete_warehouse_raises_for_missing(self, warehouse_service, mock_db):
        """delete_warehouse raises KeyError when the warehouse does not exist.

        Args:
            warehouse_service (WarehouseService): Service under test.
            mock_db (MagicMock): Mock adapter configured to return None.
        """
        mock_db.find_by_id.return_value = None
        with raises(KeyError):
            warehouse_service.delete_warehouse("missing")


class TestInventoryService:
    """Tests for InventoryService business logic."""

    def test_add_product_inserts_new_entry(self, inventory_service, mock_db):
        """add_product creates a new inventar entry when none exists.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        mock_db.find_by_id.return_value = {"_id": "lid"}
        mock_db.find_inventory_entry.return_value = None
        inventory_service.add_product("lid", "pid", 5)
        assert any(call[0][0] == "inventar" for call in mock_db.insert.call_args_list)

    def test_add_product_merges_existing(self, inventory_service, mock_db):
        """add_product increases menge when an entry already exists.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        mock_db.find_by_id.return_value = {"_id": "lid"}
        mock_db.find_inventory_entry.return_value = {"_id": "eid", "menge": 10}
        inventory_service.add_product("lid", "pid", 3)
        mock_db.update.assert_called_once()
        args = mock_db.update.call_args[0]
        assert args[2]["menge"] == 13

    def test_add_product_negative_menge_raises(self, inventory_service):
        """add_product raises ValueError for a negative menge.

        Args:
            inventory_service (InventoryService): Service under test.
        """
        with raises(ValueError, match="Menge"):
            inventory_service.add_product("lid", "pid", -1)

    def test_update_quantity_raises_for_missing_entry(self, inventory_service, mock_db):
        """update_quantity raises KeyError when the inventar entry does not exist.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter configured to return None.
        """
        mock_db.find_inventory_entry.return_value = None
        with raises(KeyError):
            inventory_service.update_quantity("lid", "pid", 5)

    def test_update_quantity_negative_raises(self, inventory_service, mock_db):
        """update_quantity raises ValueError when menge is negative.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        with raises(ValueError, match="negativ"):
            inventory_service.update_quantity("lid", "pid", -1)

    def test_remove_product_calls_delete(self, inventory_service, mock_db):
        """remove_product deletes the inventar entry.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        mock_db.find_inventory_entry.return_value = {"_id": "eid", "menge": 3}
        inventory_service.remove_product("lid", "pid")
        mock_db.delete.assert_called_once()

    def test_remove_product_raises_for_missing(self, inventory_service, mock_db):
        """remove_product raises KeyError when the entry does not exist.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter configured to return None.
        """
        mock_db.find_inventory_entry.return_value = None
        with raises(KeyError):
            inventory_service.remove_product("lid", "pid")

    def test_list_inventory_raises_for_missing_lager(self, inventory_service, mock_db):
        """list_inventory raises KeyError when the warehouse does not exist.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter configured to return None for lager.
        """
        mock_db.find_by_id.return_value = None
        with raises(KeyError):
            inventory_service.list_inventory("nonexistent")

    def test_list_inventory_enriches_entries(self, inventory_service, mock_db):
        """list_inventory annotates each entry with product name and description.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        mock_db.find_by_id.side_effect = [
            {"_id": "lid", "lagername": "L"},
            {"_id": "pid", "name": "Stift", "beschreibung": "Kugelschreiber"},
        ]
        mock_db.find_inventory_by_warehouse.return_value = [
            {"_id": "eid", "produkt_id": "pid", "menge": 7}
        ]
        result = inventory_service.list_inventory("lid")
        assert len(result) == 1
        assert result[0]["produkt_name"] == "Stift"
        assert result[0]["menge"] == 7

    def test_get_total_inventory_value_sums_preis_times_menge(self, inventory_service, mock_db):
        """get_total_inventory_value multiplies preis by menge for each entry and sums.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter returning two inventory entries.
        """
        mock_db.find_all.return_value = [
            {"produkt_id": "p1", "menge": 10},
            {"produkt_id": "p2", "menge": 5},
        ]
        mock_db.find_by_id.side_effect = [
            {"_id": "p1", "preis": 20.0},
            {"_id": "p2", "preis": 50.0},
        ]

        total = inventory_service.get_total_inventory_value()
        # 10 * 20.0 + 5 * 50.0 = 200 + 250 = 450
        assert abs(total - 450.0) < 1e-9

    def test_get_total_inventory_value_missing_preis_counts_zero(self, inventory_service, mock_db):
        """get_total_inventory_value treats products without preis as 0 contribution.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter returning a product without preis field.
        """
        mock_db.find_all.return_value = [
            {"produkt_id": "p1", "menge": 100},
        ]
        mock_db.find_by_id.return_value = {"_id": "p1", "name": "OhnePreis"}

        total = inventory_service.get_total_inventory_value()
        assert total == 0.0

    def test_add_product_stores_performed_by_in_event(self, inventory_service, mock_db):
        """add_product stores the performed_by value in the history event.

        Args:
            inventory_service (InventoryService): Service under test.
            mock_db (MagicMock): Mock adapter.
        """
        mock_db.find_by_id.return_value = {"_id": "lid", "lagername": "L"}
        mock_db.find_inventory_entry.return_value = None

        inventory_service.add_product("lid", "pid", 3, performed_by="Anna Schmidt")

        event_call = mock_db.insert.call_args_list[-1]
        assert event_call[0][0] == "events"
        assert event_call[0][1]["performed_by"] == "Anna Schmidt"
