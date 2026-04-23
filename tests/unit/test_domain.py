import unittest
from unittest.mock import MagicMock

from bierapp.backend.service.product_service import InventoryService, ProductService
from bierapp.backend.service.warehouse_service import WarehouseService


class TestProductService(unittest.TestCase):
	def setUp(self):
		self.db = MagicMock()
		self.service = ProductService(self.db)

	def test_create_product_rejects_non_positive_weight(self):
		with self.assertRaises(ValueError):
			self.service.create_product("Beer", "IPA", 0)

		with self.assertRaises(ValueError):
			self.service.create_product("Beer", "IPA", -1)

	def test_create_product_rejects_negative_price(self):
		with self.assertRaises(ValueError):
			self.service.create_product("Beer", "IPA", 1.0, preis=-0.01)

	def test_create_product_applies_defaults_and_normalizes_attributes(self):
		self.db.insert.return_value = "42"

		result = self.service.create_product(
			"Beer",
			"Strong",
			2.5,
			preis=5.0,
			waehrung="",
			lieferant="",
			einheit="",
			attributes=["taste=hoppy", {"label": "color", "text": "amber"}, "   ", 123],
		)

		self.assertEqual(result["id"], "42")
		self.assertEqual(result["waehrung"], "EUR")
		self.assertEqual(result["einheit"], "Stk")
		self.assertEqual(result["lieferant"], "")
		self.assertEqual(
			result["attributes"],
			[
				{"name": "taste", "value": "hoppy"},
				{"name": "color", "value": "amber"},
			],
		)

	def test_get_product_returns_normalized_attributes(self):
		self.db.find_by_id.return_value = {
			"id": "1",
			"name": "Beer",
			"attributes": '{"name":"origin","value":"AT"}',
		}

		result = self.service.get_product("1")

		self.assertEqual(result["attributes"], [{"name": "origin", "value": "AT"}])

	def test_get_product_handles_invalid_attribute_json(self):
		self.db.find_by_id.return_value = {
			"id": "1",
			"name": "Beer",
			"attributes": "not-json",
		}

		result = self.service.get_product("1")

		self.assertEqual(result["attributes"], [])

	def test_list_products_filters_none_and_normalizes(self):
		self.db.find_all.return_value = [
			{"id": "1", "attributes": {"name": "size", "value": "0.5l"}},
			None,
			{"id": "2", "attributes": None},
		]

		result = self.service.list_products()

		self.assertEqual(len(result), 2)
		self.assertEqual(result[0]["attributes"], [{"name": "size", "value": "0.5l"}])
		self.assertEqual(result[1]["attributes"], [])

	def test_update_product_raises_if_missing(self):
		self.db.update.return_value = False

		with self.assertRaises(KeyError):
			self.service.update_product("999", {"name": "New"})

	def test_update_product_normalizes_attributes_before_save(self):
		self.db.update.return_value = True
		self.db.find_by_id.return_value = {"id": "1", "attributes": ["foo=bar"]}

		result = self.service.update_product("1", {"attributes": "[{\"name\":\"a\",\"value\":\"b\"}]"})

		self.db.update.assert_called_once_with(
			"products",
			"1",
			{"attributes": [{"name": "a", "value": "b"}]},
		)
		self.assertEqual(result["attributes"], [{"name": "foo", "value": "bar"}])

	def test_delete_product_raises_if_missing(self):
		self.db.delete.return_value = False

		with self.assertRaises(KeyError):
			self.service.delete_product("404")


class TestInventoryService(unittest.TestCase):
	def setUp(self):
		self.db = MagicMock()
		self.service = InventoryService(self.db)

	def test_add_product_rejects_non_positive_quantity(self):
		with self.assertRaises(ValueError):
			self.service.add_product("1", "2", 0)

		with self.assertRaises(ValueError):
			self.service.add_product("1", "2", -1)

	def test_add_product_rejects_non_numeric_ids(self):
		with self.assertRaises(ValueError):
			self.service.add_product("A", "2", 1)

		with self.assertRaises(ValueError):
			self.service.add_product("1", "X", 1)

	def test_update_quantity_rejects_negative(self):
		with self.assertRaises(ValueError):
			self.service.update_quantity("1", "2", -1)

	def test_update_quantity_raises_if_inventory_entry_missing(self):
		self.db.find_all.return_value = []

		with self.assertRaises(KeyError):
			self.service.update_quantity("1", "2", 5)

	def test_update_quantity_updates_existing_entry(self):
		self.db.find_all.return_value = [{"id": "10", "lager_id": 1, "produkt_id": 2, "menge": 1}]

		self.service.update_quantity("1", "2", 5)

		self.db.update.assert_called_once_with("inventory", "10", {"menge": 5})

	def test_remove_product_raises_if_missing(self):
		self.db.find_all.return_value = []

		with self.assertRaises(KeyError):
			self.service.remove_product("1", "2")

	def test_list_inventory_filters_by_warehouse(self):
		self.db.find_all.return_value = [
			{"id": "1", "lager_id": 1, "produkt_id": 7, "menge": 3},
			{"id": "2", "lager_id": 2, "produkt_id": 7, "menge": 4},
		]

		result = self.service.list_inventory("1")

		self.assertEqual(result, [{"id": "1", "lager_id": 1, "produkt_id": 7, "menge": 3}])

	def test_set_quantity_zero_ignores_missing_entry(self):
		self.db.find_all.return_value = []

		self.service.set_quantity("1", "2", 0)

		self.db.delete.assert_not_called()

	def test_set_quantity_creates_entry_if_missing(self):
		self.db.find_all.return_value = []

		self.service.set_quantity("1", "2", 7)

		self.db.insert.assert_called_once_with("inventory", {"lager_id": 1, "produkt_id": 2, "menge": 7})

	def test_set_quantity_updates_existing_entry(self):
		self.db.find_all.return_value = [{"id": "11", "lager_id": 1, "produkt_id": 2, "menge": 2}]

		self.service.set_quantity("1", "2", 9)

		self.db.update.assert_called_once_with("inventory", "11", {"menge": 9})

	def test_set_quantity_rejects_negative(self):
		with self.assertRaises(ValueError):
			self.service.set_quantity("1", "2", -1)

	def test_statistics_report_aggregates_counts_and_stock(self):
		self.db.find_all.side_effect = [
			[{"id": "p1"}, {"id": "p2"}],
			[{"id": "w1"}],
			[{"menge": 3}, {"menge": 7}],
		]

		result = self.service.statistics_report()

		self.assertEqual(
			result,
			{
				"total_products": 2,
				"total_warehouses": 1,
				"total_stock_units": 10,
			},
		)


class TestWarehouseService(unittest.TestCase):
	def setUp(self):
		self.db = MagicMock()
		self.inventory_service = MagicMock()
		self.service = WarehouseService(self.db, self.inventory_service)

	def test_create_warehouse_returns_payload_with_id(self):
		self.db.insert.return_value = "7"

		result = self.service.create_warehouse("Main", "Street 1", 100, 3)

		self.assertEqual(result["id"], "7")
		self.db.insert.assert_called_once()
		collection, inserted = self.db.insert.call_args.args
		self.assertEqual(collection, "warehouses")
		self.assertEqual(inserted["lagername"], "Main")
		self.assertEqual(inserted["adresse"], "Street 1")
		self.assertEqual(inserted["max_plaetze"], 100)
		self.assertEqual(inserted["firma_id"], 3)

	def test_update_warehouse_raises_if_missing(self):
		self.db.update.return_value = False

		with self.assertRaises(KeyError):
			self.service.update_warehouse("999", {"lagername": "Other"})

	def test_delete_warehouse_raises_if_missing(self):
		self.db.delete.return_value = False

		with self.assertRaises(KeyError):
			self.service.delete_warehouse("999")

	def test_add_product_to_warehouse_delegates_with_string_ids(self):
		self.service.add_product_to_warehouse(1, 2, 3)

		self.inventory_service.add_product.assert_called_once_with("1", "2", 3)


if __name__ == "__main__":
	unittest.main()
