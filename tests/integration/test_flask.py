"""Integration tests for all Flask routes using the built-in test client.

The real MongoDB adapter is replaced by the mock_db fixture so no live
database is required to run these tests.
"""

from unittest.mock import call


FAKE_ID = "507f1f77bcf86cd799439011"


class TestStaticAndDashboard:
    """Tests for the root / and static-file routes."""

    def test_index_returns_200(self, flask_client, mock_db):
        """GET / renders the dashboard page without errors.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): Mock adapter (find_all returns []).
        """
        mock_db.find_all.return_value = []
        response = flask_client.get("/")
        assert response.status_code == 200

    def test_index_contains_stat_cards(self, flask_client, mock_db):
        """GET / response body contains expected dashboard keywords.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): Mock adapter.
        """
        mock_db.find_all.return_value = []
        response = flask_client.get("/")
        body = response.data.decode("utf-8")
        assert "Produkte" in body or "produkte" in body


class TestProdukte:
    """Tests for the /produkte endpoints."""

    def test_list_returns_200(self, flask_client):
        """GET /produkte renders the product list page.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
        """
        response = flask_client.get("/produkte")
        assert response.status_code == 200

    def test_create_valid_redirects(self, flask_client, mock_db):
        """POST /produkte/neu with valid data redirects to the list page.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): Mock adapter; insert is called once.
        """
        mock_db.insert.return_value = FAKE_ID
        response = flask_client.post(
            "/produkte/neu",
            data={"name": "Schraube", "beschreibung": "M6", "gewicht": "0.05"},
        )
        assert response.status_code == 302
        assert "/produkte" in response.headers["Location"]
        mock_db.insert.assert_called_once()

    def test_create_empty_name_redirects_with_flash(self, flask_client, mock_db):
        """POST /produkte/neu with an empty name does not insert and redirects.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): Mock adapter; insert must not be called.
        """
        response = flask_client.post(
            "/produkte/neu",
            data={"name": "   ", "beschreibung": "", "gewicht": "1.0"},
        )
        assert response.status_code == 302
        mock_db.insert.assert_not_called()

    def test_create_negative_weight_redirects_with_flash(self, flask_client, mock_db):
        """POST /produkte/neu with negative gewicht does not insert.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): Mock adapter; insert must not be called.
        """
        response = flask_client.post(
            "/produkte/neu",
            data={"name": "Test", "beschreibung": "", "gewicht": "-5"},
        )
        assert response.status_code == 302
        mock_db.insert.assert_not_called()

    def test_update_missing_redirects(self, flask_client, mock_db):
        """POST /produkte/<id>/bearbeiten for unknown id does not crash.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): Mock adapter returning None for find_by_id.
        """
        mock_db.find_by_id.return_value = None
        response = flask_client.post(
            f"/produkte/{FAKE_ID}/bearbeiten",
            data={"name": "X", "beschreibung": "", "gewicht": "1"},
        )
        assert response.status_code == 302

    def test_delete_missing_redirects(self, flask_client, mock_db):
        """POST /produkte/<id>/loeschen for unknown id redirects gracefully.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): Mock adapter returning None for find_by_id.
        """
        mock_db.find_by_id.return_value = None
        response = flask_client.post(f"/produkte/{FAKE_ID}/loeschen")
        assert response.status_code == 302


class TestLager:
    """Tests for the /lager endpoints."""

    def test_list_returns_200(self, flask_client):
        """GET /lager renders the warehouse list page.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
        """
        response = flask_client.get("/lager")
        assert response.status_code == 200

    def test_create_valid_redirects(self, flask_client, mock_db):
        """POST /lager/neu with valid data redirects to the list page.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): Mock adapter; insert is called once.
        """
        mock_db.insert.return_value = FAKE_ID
        response = flask_client.post(
            "/lager/neu",
            data={"lagername": "Lager West", "adresse": "Wien", "max_plaetze": "100"},
        )
        assert response.status_code == 302
        assert "/lager" in response.headers["Location"]
        mock_db.insert.assert_called_once()

    def test_create_empty_name_redirects_without_insert(self, flask_client, mock_db):
        """POST /lager/neu with empty lagername does not insert.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): insert must not be called.
        """
        response = flask_client.post(
            "/lager/neu",
            data={"lagername": "  ", "adresse": "", "max_plaetze": "10"},
        )
        assert response.status_code == 302
        mock_db.insert.assert_not_called()

    def test_create_zero_plaetze_redirects_without_insert(self, flask_client, mock_db):
        """POST /lager/neu with max_plaetze=0 does not insert.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): insert must not be called.
        """
        response = flask_client.post(
            "/lager/neu",
            data={"lagername": "Lager X", "adresse": "", "max_plaetze": "0"},
        )
        assert response.status_code == 302
        mock_db.insert.assert_not_called()


class TestInventar:
    """Tests for the /inventar endpoints."""

    def test_inventar_empty_lager_returns_200(self, flask_client, mock_db):
        """GET /inventar with no warehouses renders the empty-state page.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): find_all returns empty list.
        """
        mock_db.find_all.return_value = []
        response = flask_client.get("/inventar")
        assert response.status_code == 200

    def test_inventar_redirects_to_first_lager(self, flask_client, mock_db):
        """GET /inventar redirects to the first warehouse when one exists.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): find_all returns one warehouse.
        """
        mock_db.find_all.return_value = [{"_id": FAKE_ID, "lagername": "L1"}]
        response = flask_client.get("/inventar")
        assert response.status_code == 302
        assert FAKE_ID in response.headers["Location"]

    def test_inventar_detail_returns_200(self, flask_client, mock_db):
        """GET /inventar/<lager_id> renders the detail page.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): find_by_id returns lager, then product docs.
        """
        lager_doc = {"_id": FAKE_ID, "lagername": "L1", "adresse": "", "max_plaetze": 50}
        mock_db.find_by_id.return_value = lager_doc
        mock_db.find_inventar_by_lager.return_value = []
        mock_db.find_all.return_value = []
        response = flask_client.get(f"/inventar/{FAKE_ID}")
        assert response.status_code == 200

    def test_inventar_detail_unknown_lager_redirects(self, flask_client, mock_db):
        """GET /inventar/<lager_id> redirects when the warehouse is not found.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): find_by_id returns None.
        """
        mock_db.find_by_id.return_value = None
        mock_db.find_all.return_value = []
        response = flask_client.get(f"/inventar/{FAKE_ID}")
        assert response.status_code == 302

    def test_inventar_add_valid_redirects(self, flask_client, mock_db):
        """POST /inventar/<lager_id>/hinzufuegen inserts and redirects.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): find_by_id returns lager, find_inventar_entry None.
        """
        mock_db.find_by_id.return_value = {"_id": FAKE_ID}
        mock_db.find_inventar_entry.return_value = None
        mock_db.insert.return_value = "newid"
        response = flask_client.post(
            f"/inventar/{FAKE_ID}/hinzufuegen",
            data={"produkt_id": "pid123", "menge": "5"},
        )
        assert response.status_code == 302

    def test_inventar_update_quantity_redirects(self, flask_client, mock_db):
        """POST /inventar/<lager_id>/<produkt_id>/aktualisieren updates and redirects.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): find_inventar_entry returns existing entry.
        """
        mock_db.find_inventar_entry.return_value = {"_id": "eid", "menge": 10}
        response = flask_client.post(
            f"/inventar/{FAKE_ID}/pid123/aktualisieren",
            data={"menge": "15"},
        )
        assert response.status_code == 302
        mock_db.update.assert_called_once()

    def test_inventar_remove_redirects(self, flask_client, mock_db):
        """POST /inventar/<lager_id>/<produkt_id>/entfernen deletes and redirects.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): find_inventar_entry returns existing entry.
        """
        mock_db.find_inventar_entry.return_value = {"_id": "eid", "menge": 3}
        response = flask_client.post(f"/inventar/{FAKE_ID}/pid123/entfernen")
        assert response.status_code == 302
        mock_db.delete.assert_called_once()


class TestNewUIRoutes:
    """Tests for the new 4-page UI routes (/ui/*)."""

    def test_page1_products_returns_200(self, flask_client, mock_db):
        """GET /ui/produkte renders Page 1 - Product Management."""
        mock_db.find_all.return_value = []
        response = flask_client.get("/ui/produkte")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "Produktverwaltung" in body

    def test_page2_new_product_returns_200(self, flask_client, mock_db):
        """GET /ui/produkt/neu renders Page 2 - New Product form."""
        mock_db.find_all.return_value = []
        response = flask_client.get("/ui/produkt/neu")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "Neues Produkt" in body

    def test_page2_edit_product_returns_200(self, flask_client, mock_db):
        """GET /ui/produkt/<id>/bearbeiten renders Page 2 - Edit Product form."""
        product_doc = {"_id": FAKE_ID, "name": "TestProdukt", "beschreibung": "Test"}
        mock_db.find_by_id.return_value = product_doc
        mock_db.find_all.return_value = [{"_id": "lager1", "lagername": "Lager A"}]
        response = flask_client.get(f"/ui/produkt/{FAKE_ID}/bearbeiten")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "TestProdukt" in body

    def test_page2_create_product_redirects(self, flask_client, mock_db):
        """POST /ui/produkt/neu with valid data creates product and redirects."""
        mock_db.insert.return_value = FAKE_ID
        mock_db.find_all.return_value = []
        response = flask_client.post(
            "/ui/produkt/neu",
            data={
                "name": "Neues Produkt",
                "beschreibung": "Beschreibung",
                "gewicht": "1.5",
                "preis": "10.00",
                "waehrung": "EUR",
                "lieferant": "Lieferant X",
                "menge": "100",
            },
        )
        assert response.status_code == 302
        assert "/ui/produkte" in response.headers["Location"]

    def test_page2_save_product_redirects(self, flask_client, mock_db):
        """POST /ui/produkt/<id>/speichern updates product and redirects."""
        product_doc = {"_id": FAKE_ID, "name": "TestProdukt"}
        mock_db.find_by_id.return_value = product_doc
        mock_db.find_all.return_value = []
        response = flask_client.post(
            f"/ui/produkt/{FAKE_ID}/speichern",
            data={
                "name": "Geändertes Produkt",
                "beschreibung": "Neue Beschreibung",
                "gewicht": "2.0",
                "preis": "15.00",
                "waehrung": "USD",
                "lieferant": "Neuer Lieferant",
                "menge": "50",
            },
        )
        assert response.status_code == 302
        assert "/ui/produkte" in response.headers["Location"]

    def test_page3_warehouse_list_returns_200(self, flask_client, mock_db):
        """GET /ui/lager renders Page 3 - Warehouse List."""
        mock_db.find_all.return_value = []
        response = flask_client.get("/ui/lager")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "Lagerliste" in body

    def test_page3_create_warehouse_redirects(self, flask_client, mock_db):
        """POST /ui/lager/neu creates warehouse and redirects."""
        mock_db.insert.return_value = FAKE_ID
        mock_db.find_all.return_value = []
        response = flask_client.post(
            "/ui/lager/neu",
            data={"lagername": "Neues Lager", "adresse": "Wien", "max_plaetze": "200"},
        )
        assert response.status_code == 302
        assert "/ui/lager" in response.headers["Location"]

    def test_page3_delete_warehouse_redirects(self, flask_client, mock_db):
        """POST /ui/lager/<id>/loeschen deletes warehouse and redirects."""
        lager_doc = {"_id": FAKE_ID, "lagername": "TestLager"}
        mock_db.find_by_id.return_value = lager_doc
        mock_db.find_all.return_value = [{"_id": FAKE_ID, "lagername": "TestLager"}]
        response = flask_client.post(f"/ui/lager/{FAKE_ID}/loeschen")
        assert response.status_code == 302
        assert "/ui/lager" in response.headers["Location"]

    def test_page4_statistics_returns_200(self, flask_client, mock_db):
        """GET /ui/statistik renders Page 4 - Statistics Dashboard."""
        mock_db.find_all.return_value = []
        response = flask_client.get("/ui/statistik")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "Statistik" in body

    def test_page4_statistics_contains_charts(self, flask_client, mock_db):
        """GET /ui/statistik renders chart canvas elements."""
        mock_db.find_all.return_value = []
        response = flask_client.get("/ui/statistik")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        # Check for Chart.js canvas elements
        assert "donutChart" in body
        assert "barChart" in body
        assert "ausChart" in body
        assert "katChart" in body
