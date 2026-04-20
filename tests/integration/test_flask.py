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
    """Tests for the /ui/produkt* endpoints."""

    def test_list_returns_200(self, flask_client, mock_db):
        """GET /ui/produkte renders the product list page.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): find_all returns empty list.
        """
        mock_db.find_all.return_value = []
        response = flask_client.get("/ui/produkte")
        assert response.status_code == 200

    def test_create_valid_redirects(self, flask_client, mock_db):
        """POST /ui/produkt/neu with valid data redirects to the product list.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): Mock adapter; insert is called once.
        """
        mock_db.insert.return_value = FAKE_ID
        mock_db.find_all.return_value = []
        response = flask_client.post(
            "/ui/produkt/neu",
            data={"name": "Schraube", "beschreibung": "M6", "gewicht": "0.05", "preis": "1.99"},
        )
        assert response.status_code == 302
        assert "/ui/produkte" in response.headers["Location"]
        # First insert must target the "produkte" collection (product creation).
        assert mock_db.insert.call_args_list[0][0][0] == "produkte"

    def test_create_empty_name_redirects_with_flash(self, flask_client, mock_db):
        """POST /ui/produkt/neu with an empty name does not insert and redirects.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): Mock adapter; insert must not be called.
        """
        response = flask_client.post(
            "/ui/produkt/neu",
            data={"name": "   ", "beschreibung": "", "gewicht": "1.0", "preis": "1.00"},
        )
        assert response.status_code == 302
        mock_db.insert.assert_not_called()

    def test_create_negative_weight_redirects_with_flash(self, flask_client, mock_db):
        """POST /ui/produkt/neu with negative gewicht does not insert.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): Mock adapter; insert must not be called.
        """
        response = flask_client.post(
            "/ui/produkt/neu",
            data={"name": "Test", "beschreibung": "", "gewicht": "-5", "preis": ""},
        )
        assert response.status_code == 302
        mock_db.insert.assert_not_called()

    def test_update_missing_redirects(self, flask_client, mock_db):
        """POST /ui/produkt/<id>/speichern for unknown id does not crash.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): Mock adapter returning None for find_by_id.
        """
        mock_db.find_by_id.return_value = None
        response = flask_client.post(
            f"/ui/produkt/{FAKE_ID}/speichern",
            data={"name": "X", "beschreibung": "", "gewicht": "1"},
        )
        assert response.status_code == 302

    def test_delete_missing_redirects(self, flask_client, mock_db):
        """POST /ui/produkt/<id>/loeschen for unknown id redirects gracefully.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): Mock adapter returning None for find_by_id.
        """
        mock_db.find_by_id.return_value = None
        mock_db.find_all.return_value = []
        response = flask_client.post(f"/ui/produkt/{FAKE_ID}/loeschen")
        assert response.status_code == 302

class TestLager:
    """Tests for the /ui/lager* endpoints."""

    def test_list_returns_200(self, flask_client, mock_db):
        """GET /ui/lager renders the warehouse list page.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): find_all returns empty list.
        """
        mock_db.find_all.return_value = []
        response = flask_client.get("/ui/lager")
        assert response.status_code == 200

    def test_create_valid_redirects(self, flask_client, mock_db):
        """POST /ui/lager/neu with valid data redirects to the list page.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): Mock adapter; insert is called once.
        """
        mock_db.insert.return_value = FAKE_ID
        mock_db.find_all.return_value = []
        response = flask_client.post(
            "/ui/lager/neu",
            data={"lagername": "Lager West", "adresse": "Wien", "max_plaetze": "100"},
        )
        assert response.status_code == 302
        assert "/ui/lager" in response.headers["Location"]
        # First insert must target the "lager" collection.
        assert mock_db.insert.call_args_list[0][0][0] == "lager"

    def test_create_empty_name_redirects_without_insert(self, flask_client, mock_db):
        """POST /ui/lager/neu with empty lagername does not insert.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): insert must not be called.
        """
        response = flask_client.post(
            "/ui/lager/neu",
            data={"lagername": "  ", "adresse": "", "max_plaetze": "10"},
        )
        assert response.status_code == 302
        mock_db.insert.assert_not_called()

    def test_create_zero_plaetze_redirects_without_insert(self, flask_client, mock_db):
        """POST /ui/lager/neu with max_plaetze=0 does not insert.

        Args:
            flask_client (FlaskClient): Test client with mocked DB.
            mock_db (MagicMock): insert must not be called.
        """
        response = flask_client.post(
            "/ui/lager/neu",
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
        mock_db.find_inventory_by_warehouse.return_value = []
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
            mock_db (MagicMock): find_by_id returns lager, find_inventory_entry None.
        """
        mock_db.find_by_id.return_value = {"_id": FAKE_ID}
        mock_db.find_inventory_entry.return_value = None
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
            mock_db (MagicMock): find_inventory_entry returns existing entry.
        """
        mock_db.find_inventory_entry.return_value = {"_id": "eid", "menge": 10}
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
            mock_db (MagicMock): find_inventory_entry returns existing entry.
        """
        mock_db.find_inventory_entry.return_value = {"_id": "eid", "menge": 3}
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

    def test_page5_history_returns_200(self, flask_client, mock_db):
        """GET /ui/historie renders Page 5 - History list."""
        mock_db.find_all.return_value = []
        response = flask_client.get("/ui/historie")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "Historie" in body

    def test_page8_settings_returns_200(self, flask_client, mock_db):
        """GET /ui/einstellungen renders the settings workspace."""
        mock_db.find_all.return_value = []
        response = flask_client.get("/ui/einstellungen")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "Einstellungen" in body

    def test_page9_user_admin_returns_200_for_manager(self, flask_client, mock_db):
        """GET /ui/admin/benutzer renders user admin page for manager sessions."""
        flask_client.application.config["AUTH_REQUIRED"] = True
        try:
            with flask_client.session_transaction() as session_store:
                session_store["user_name"] = "admin"
                session_store["display_name"] = "Administrator"
                session_store["user_role"] = "manager"

            def find_all_by_collection(collection_name):
                if collection_name == "users":
                    return [
                        {
                            "_id": FAKE_ID,
                            "username": "admin",
                            "display_name": "Administrator",
                            "role": "manager",
                            "active": True,
                        }
                    ]
                if collection_name == "events":
                    return [
                        {
                            "timestamp": "2026-04-20T12:00:00Z",
                            "entity_type": "user_admin",
                            "action": "update_role",
                            "summary": "Rolle für admin geändert.",
                            "performed_by": "admin",
                            "details": {"target_username": "admin"},
                        }
                    ]
                return []

            mock_db.find_all.side_effect = find_all_by_collection
            response = flask_client.get("/ui/admin/benutzer")
            assert response.status_code == 200
            body = response.data.decode("utf-8")
            assert "User-Administration" in body
            assert "Audit-Log" in body
        finally:
            flask_client.application.config["AUTH_REQUIRED"] = False

    def test_page9_user_admin_redirects_for_clerk(self, flask_client, mock_db):
        """GET /ui/admin/benutzer redirects when user is not manager."""
        flask_client.application.config["AUTH_REQUIRED"] = True
        try:
            with flask_client.session_transaction() as session_store:
                session_store["user_name"] = "lager"
                session_store["display_name"] = "Lager Team"
                session_store["user_role"] = "clerk"

            response = flask_client.get("/ui/admin/benutzer")
            assert response.status_code == 302
            assert "/ui/produkte" in response.headers["Location"]
        finally:
            flask_client.application.config["AUTH_REQUIRED"] = False

    def test_page9_user_create_redirects(self, flask_client, mock_db):
        """POST /ui/admin/benutzer/neu creates a new user and redirects."""
        flask_client.application.config["AUTH_REQUIRED"] = True
        try:
            with flask_client.session_transaction() as session_store:
                session_store["user_name"] = "admin"
                session_store["display_name"] = "Administrator"
                session_store["user_role"] = "manager"

            mock_db.find_all.return_value = []
            response = flask_client.post(
                "/ui/admin/benutzer/neu",
                data={
                    "username": "newuser",
                    "display_name": "Neuer User",
                    "role": "clerk",
                    "password": "pw1234",
                    "active": "1",
                },
            )
            assert response.status_code == 302
            assert "/ui/admin/benutzer" in response.headers["Location"]
            insert_calls = mock_db.insert.call_args_list
            user_insert = next(call_item for call_item in insert_calls if call_item[0][0] == "users")
            inserted_user = user_insert[0][1]
            assert inserted_user["username"] == "newuser"
            assert inserted_user["role"] == "clerk"
            assert inserted_user["active"] is True
            assert inserted_user["password_hash"] != "pw1234"

            event_insert = next(call_item for call_item in insert_calls if call_item[0][0] == "events")
            inserted_event = event_insert[0][1]
            assert inserted_event["entity_type"] == "user_admin"
            assert inserted_event["action"] == "create"
            assert inserted_event["details"]["target_username"] == "newuser"
        finally:
            flask_client.application.config["AUTH_REQUIRED"] = False


class TestAuthAndPdfExport:
    """Tests for authentication flow and PDF export endpoints."""

    def test_auth_redirects_to_login_when_enabled(self, flask_client, mock_db):
        """GET /ui/produkte redirects to /login when auth is enabled and user is anonymous."""
        flask_client.application.config["AUTH_REQUIRED"] = True
        try:
            response = flask_client.get("/ui/produkte")
            assert response.status_code == 302
            assert "/login" in response.headers["Location"]
        finally:
            flask_client.application.config["AUTH_REQUIRED"] = False

    def test_login_page_returns_200(self, flask_client):
        """GET /login renders the login form."""
        flask_client.application.config["AUTH_REQUIRED"] = True
        try:
            response = flask_client.get("/login")
            assert response.status_code == 200
            assert "Anmelden" in response.data.decode("utf-8")
        finally:
            flask_client.application.config["AUTH_REQUIRED"] = False

    def test_history_pdf_export_returns_pdf(self, flask_client, mock_db):
        """POST /ui/historie/export-pdf returns a PDF response."""
        mock_db.find_all.return_value = [
            {
                "timestamp": "2026-04-20T12:00:00Z",
                "entity_type": "produkt",
                "action": "create",
                "summary": "Produkt X angelegt",
                "performed_by": "admin",
            }
        ]
        response = flask_client.post("/ui/historie/export-pdf")
        assert response.status_code == 200
        assert response.mimetype == "application/pdf"

    def test_statistics_pdf_export_returns_pdf(self, flask_client, mock_db):
        """POST /ui/statistik/export-pdf returns a PDF response."""
        mock_db.find_all.return_value = []
        response = flask_client.post("/ui/statistik/export-pdf")
        assert response.status_code == 200
        assert response.mimetype == "application/pdf"

    def test_inventory_pdf_export_returns_pdf(self, flask_client, mock_db):
        """POST /ui/produkte/export-pdf returns a PDF response."""
        mock_db.find_all.return_value = []
        response = flask_client.post("/ui/produkte/export-pdf", data={"lager_id": ""})
        assert response.status_code == 200
        assert response.mimetype == "application/pdf"


class TestProcurementRoutes:
    """Tests for procurement suggestions and reorder actions."""

    def test_page6_procurement_returns_200(self, flask_client, mock_db):
        """GET /ui/bestellungen renders the procurement suggestions page."""
        mock_db.find_all.return_value = []
        response = flask_client.get("/ui/bestellungen")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "Bestellvorschläge" in body

    def test_page6_execute_reorder_redirects(self, flask_client, mock_db):
        """POST /ui/bestellungen/<produkt_id>/ausfuehren redirects after action."""
        mock_db.find_by_id.return_value = {"_id": FAKE_ID}
        mock_db.find_inventory_entry.return_value = None
        response = flask_client.post(
            f"/ui/bestellungen/{FAKE_ID}/ausfuehren",
            data={"lager_id": FAKE_ID, "menge": "8"},
        )
        assert response.status_code == 302
        assert "/ui/bestellungen" in response.headers["Location"]

    def test_create_supplier_redirects(self, flask_client, mock_db):
        """POST /ui/lieferanten/neu creates a supplier and redirects."""
        response = flask_client.post(
            "/ui/lieferanten/neu",
            data={
                "name": "OfficeSupply GmbH",
                "email": "kontakt@example.org",
                "bewertung": "4.6",
                "mindestbestellwert": "50",
                "sla_tage": "3",
            },
        )
        assert response.status_code == 302
        assert "/ui/bestellungen" in response.headers["Location"]
        inserted_supplier = mock_db.insert.call_args[0][1]
        assert inserted_supplier["bewertung"] == 4.6
        assert inserted_supplier["mindestbestellwert"] == 50.0
        assert inserted_supplier["sla_tage"] == 3

    def test_create_department_redirects(self, flask_client, mock_db):
        """POST /ui/abteilungen/neu creates a department and redirects."""
        response = flask_client.post(
            "/ui/abteilungen/neu",
            data={"name": "IT", "kostenstelle": "KST-100", "budget_limit": "10000"},
        )
        assert response.status_code == 302
        assert "/ui/bestellungen" in response.headers["Location"]

    def test_create_order_redirects(self, flask_client, mock_db):
        """POST /ui/bestellungen/neu creates an order and redirects."""
        mock_db.find_by_id.side_effect = [
            {"_id": "s1", "mindestbestellwert": 0},
            {"_id": "dep1", "budget_limit": 10000, "budget_used": 0},
        ]
        response = flask_client.post(
            "/ui/bestellungen/neu",
            data={
                "produkt_id": "p1",
                "lieferant_id": "s1",
                "lager_id": "l1",
                "abteilung_id": "dep1",
                "bestellmenge": "5",
                "einzelpreis": "10.5",
            },
        )
        assert response.status_code == 302
        assert "/ui/bestellungen" in response.headers["Location"]

    def test_create_order_rejects_below_supplier_minimum(self, flask_client, mock_db):
        """POST /ui/bestellungen/neu rejects orders below supplier minimum order value."""
        mock_db.find_by_id.side_effect = [
            {"_id": "s1", "mindestbestellwert": 100.0},
            {"_id": "dep1", "budget_limit": 10000, "budget_used": 0},
        ]
        response = flask_client.post(
            "/ui/bestellungen/neu",
            data={
                "produkt_id": "p1",
                "lieferant_id": "s1",
                "lager_id": "l1",
                "abteilung_id": "dep1",
                "bestellmenge": "2",
                "einzelpreis": "10",
            },
        )
        assert response.status_code == 302
        assert "/ui/bestellungen" in response.headers["Location"]
        mock_db.insert.assert_not_called()

    def test_approve_order_redirects(self, flask_client, mock_db):
        """POST /ui/bestellungen/<id>/freigeben approves waiting orders and updates budget."""
        mock_db.find_by_id.side_effect = [
            {
                "_id": "o1",
                "status": "warte_freigabe",
                "abteilung_id": "dep1",
                "bestellmenge": 10,
                "einzelpreis": 5,
            },
            {"_id": "dep1", "budget_limit": 10000, "budget_used": 100},
        ]
        response = flask_client.post("/ui/bestellungen/o1/freigeben")
        assert response.status_code == 302
        assert "/ui/bestellungen" in response.headers["Location"]
        assert mock_db.update.call_count >= 2

    def test_goods_receipt_redirects(self, flask_client, mock_db):
        """POST /ui/bestellungen/<id>/wareneingang books partial receipt and redirects."""
        mock_db.find_by_id.side_effect = [
            {
                "_id": "o1",
                "status": "bestellt",
                "bestellmenge": 10,
                "geliefert": 4,
                "lager_id": "l1",
                "produkt_id": "p1",
            },
            {"_id": "l1"},
            {"_id": "p1"},
        ]
        mock_db.find_inventory_entry.return_value = None
        response = flask_client.post("/ui/bestellungen/o1/wareneingang", data={"menge": "3"})
        assert response.status_code == 302
        assert "/ui/bestellungen" in response.headers["Location"]


class TestPickingRoutes:
    """Tests for picking list workflow endpoints."""

    def test_page7_picking_returns_200(self, flask_client, mock_db):
        """GET /ui/kommissionierung renders picking page."""
        mock_db.find_all.return_value = []
        response = flask_client.get("/ui/kommissionierung")
        assert response.status_code == 200
        assert "Kommissionierung" in response.data.decode("utf-8")

    def test_create_picklist_redirects(self, flask_client, mock_db):
        """POST /ui/kommissionierung/neu creates pick list and redirects."""
        mock_db.find_all.return_value = [{"_id": "p1", "name": "Marker", "lagerzone": "B"}]
        response = flask_client.post(
            "/ui/kommissionierung/neu",
            data={
                "lager_id": "l1",
                "abteilung_id": "d1",
                "bereich": "A",
                "produkt_id[]": ["p1"],
                "menge[]": ["2"],
            },
        )
        assert response.status_code == 302
        assert "/ui/kommissionierung" in response.headers["Location"]
        inserted_picklist = mock_db.insert.call_args[0][1]
        assert "weglaenge_m" in inserted_picklist
        assert inserted_picklist["weglaenge_m"] > 0

    def test_print_picklist_returns_200(self, flask_client, mock_db):
        """GET /ui/kommissionierung/<id>/druck renders print template."""
        mock_db.find_by_id.return_value = {
            "_id": "pk1",
            "lager_id": "l1",
            "abteilung_id": "d1",
            "bereich": "A",
            "pick_route": "Ablage -> Marker",
            "items": [{"produkt_id": "p1", "menge": 1, "lagerbereich": "A"}],
        }
        mock_db.find_all.side_effect = [
            [{"_id": "p1", "name": "Marker", "sku": "M-1"}],
            [{"_id": "l1", "lagername": "Halle 1"}],
            [{"_id": "d1", "name": "IT", "kostenstelle": "KST-1"}],
        ]
        response = flask_client.get("/ui/kommissionierung/pk1/druck")
        assert response.status_code == 200
        assert "Kommissionierliste" in response.data.decode("utf-8")
