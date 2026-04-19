"""B.I.E.R Flask GUI - Route handlers for the inventory management system."""

import os
import json
import io
import tempfile
import pathlib
from flask import Flask, render_template, jsonify, request, send_from_directory, send_file
from bierapp.backend.service.product_service import ProductService, InventoryService
from bierapp.backend.service.warehouse_service import WarehouseService


def _theme_options() -> list[str]:
    """Return available stylesheet filenames.

    Returns:
        list[str]: Sorted list of available `.css` themes.
    """
    styles_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "stylesheets"))
    return sorted([name for name in os.listdir(styles_dir) if name.endswith(".css")])


def _selected_theme() -> str:
    """Resolve the currently selected theme from the request query.

    Returns:
        str: A valid stylesheet filename.
    """
    options = _theme_options()
    fallback = "common.css" if "common.css" in options else (options[0] if options else "common.css")
    requested = request.args.get("theme", fallback)
    return requested if requested in options else fallback


def register_routes(app: Flask, product_service: ProductService, warehouse_service: WarehouseService, inventory_service: InventoryService) -> None:
    """Register all API routes for the Flask application.

    Args:
        app (Flask): The Flask application instance.
        product_service (ProductService): Service for product management.
        warehouse_service (WarehouseService): Service for warehouse management.
        inventory_service (InventoryService): Service for inventory management.
    """

    def _log_history(entry_type: str, action: str, details: str) -> None:
        """Best-effort history logging.

        The history is not critical for core operations; failures are ignored.
        """

        try:
            inventory_service.db.insert("history", {"entry_type": entry_type, "action": action, "details": details})
        except Exception:
            return

    def _serialize_history_row(row: dict) -> dict:
        created_at = row.get("created_at")
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        return {
            "id": row.get("id"),
            "created_at": created_at,
            "entry_type": row.get("entry_type"),
            "action": row.get("action"),
            "details": row.get("details"),
        }

    def _generate_report_pdf(report_key: str) -> tuple[io.BytesIO, str]:
        report_id = str(report_key or "").lower()
        try:
            if report_id == "a":
                from reports.report_a import ReportA

                report_runner = ReportA(db_repo=inventory_service.db)
                filename = "report_a.pdf"
            elif report_id == "b":
                from reports.report_b import ReportB

                report_runner = ReportB()  # type: ignore[abstract]
                filename = "report_b.pdf"
            else:
                raise ValueError("Unknown report key")
        except ModuleNotFoundError as exc:
            raise RuntimeError("Report dependencies missing: install matplotlib and Pillow") from exc
        except TypeError as exc:
            raise NotImplementedError("Report B is not fully implemented in colleague code") from exc

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output_path = pathlib.Path(tmp.name)

        try:
            raw_data = report_runner.get_data(None)
            processed = report_runner.process_data(raw_data)
            report_runner.generate_report(processed, output_path=output_path)

            pdf_bytes = output_path.read_bytes()
            buffer = io.BytesIO(pdf_bytes)
            buffer.seek(0)
            return buffer, filename
        finally:
            try:
                output_path.unlink(missing_ok=True)
            except Exception:
                pass
    @app.route("/stylesheets/<path:filename>", endpoint="stylesheet", methods=["GET"])
    def stylesheet(filename: str):
        """Serve a stylesheet file from the resources directory.

        Args:
            filename (str): Name of the stylesheet file.

        Returns:
            Response: The requested stylesheet file.
        """
        styles_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "stylesheets"))
        return send_from_directory(styles_dir, filename)

    @app.route("/scripts/app.js", endpoint="app_script", methods=["GET"])
    def app_script():
        """Serve the centralized frontend JavaScript bundle.

        Returns:
            Response: The shared `app.js` frontend script.
        """
        script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "controller"))
        return send_from_directory(script_dir, "app.js")

    @app.route("/", methods=["GET"])
    def index():
        """Render the main index page.

        Returns:
            str: Rendered HTML template for the main dashboard.
        """
        selected_theme = _selected_theme()
        return render_template("index.html", selected_theme=selected_theme, theme_options=_theme_options())

    @app.route("/page1", methods=["GET"])
    def page1():
        """Render the product edit page.

        Returns:
            str: Rendered HTML template for product editing.
        """
        selected_theme = _selected_theme()
        return render_template("page1.html", selected_theme=selected_theme, theme_options=_theme_options())

    @app.route("/page2", methods=["GET"])
    def page2():
        """Render the warehouse list page.

        Returns:
            str: Rendered HTML template for warehouse overview.
        """
        selected_theme = _selected_theme()
        return render_template("page2.html", selected_theme=selected_theme, theme_options=_theme_options())

    @app.route("/page3", methods=["GET"])
    def page3():
        """Render the statistics page.

        Returns:
            str: Rendered HTML template for statistics dashboard.
        """
        selected_theme = _selected_theme()
        return render_template("page3.html", selected_theme=selected_theme, theme_options=_theme_options())

    @app.route("/page4", methods=["GET"])
    def page4():
        """Render the history page.

        Returns:
            str: Rendered HTML template for change history.
        """
        selected_theme = _selected_theme()
        return render_template("page4.html", selected_theme=selected_theme, theme_options=_theme_options())

    @app.route("/page5", methods=["GET"])
    def page5():
        """Render the warehouse detail page.

        Returns:
            str: Rendered HTML template for managing products within a warehouse.
        """
        selected_theme = _selected_theme()
        return render_template("page5.html", selected_theme=selected_theme, theme_options=_theme_options())

    @app.route("/page6", methods=["GET"])
    def page6():
        """Render the reports page.

        Returns:
            str: Rendered HTML template for report preview and download.
        """
        selected_theme = _selected_theme()
        return render_template("page6.html", selected_theme=selected_theme, theme_options=_theme_options())

    @app.route("/reports/<report_key>/preview", methods=["GET"])
    def preview_report(report_key: str):
        """Generate and return a report as inline PDF preview."""
        try:
            stream, filename = _generate_report_pdf(report_key)
            return send_file(stream, mimetype="application/pdf", as_attachment=False, download_name=filename)
        except ValueError as exc:
            return jsonify({"error": "Unknown report", "details": str(exc)}), 404
        except NotImplementedError as exc:
            return jsonify({"error": "Report not implemented", "details": str(exc)}), 501
        except Exception as exc:
            return jsonify({"error": "Failed to generate report", "details": str(exc)}), 500

    @app.route("/reports/<report_key>/download", methods=["GET"])
    def download_report(report_key: str):
        """Generate and return a report as downloadable PDF."""
        try:
            stream, filename = _generate_report_pdf(report_key)
            return send_file(stream, mimetype="application/pdf", as_attachment=True, download_name=filename)
        except ValueError as exc:
            return jsonify({"error": "Unknown report", "details": str(exc)}), 404
        except NotImplementedError as exc:
            return jsonify({"error": "Report not implemented", "details": str(exc)}), 501
        except Exception as exc:
            return jsonify({"error": "Failed to generate report", "details": str(exc)}), 500

    @app.route("/history", methods=["GET"])
    def get_history():
        """Retrieve change history entries.

        Returns:
            tuple: JSON response with history entries and HTTP 200 status.
        """

        try:
            rows = inventory_service.db.find_all("history")
            rows = [_serialize_history_row(row) for row in rows]
            return jsonify(rows), 200
        except Exception as exc:
            return jsonify({"error": "Failed to retrieve history", "details": str(exc)}), 500

    @app.route("/products", methods=["GET"])
    def get_products():
        """Retrieve all products from the inventory.

        Returns:
            tuple: JSON response with products list and HTTP 200 status.
        """
        try:
            products = product_service.list_products()
            return jsonify(products), 200
        except Exception as exc:
            return jsonify({"error": "Failed to retrieve products", "details": str(exc)}), 500

    @app.route("/products", methods=["POST"])
    def create_product():
        """Create a new product in the inventory.

        Returns:
            tuple: JSON response with created product and HTTP 201 status.

        Raises:
            400: If required fields are missing or data type is invalid.
            500: If product creation fails.
        """
        try:
            data = request.get_json()
            if not data or "name" not in data or "gewicht" not in data:
                return jsonify({"error": "Missing required fields: name, gewicht"}), 400
            product = product_service.create_product(
                name=data["name"],
                beschreibung=data.get("beschreibung", ""),
                gewicht=float(data["gewicht"]),
                einheit=data.get("einheit", "Stk"),
            )
            _log_history("product", "create", f"Produkt {product.get('id')}: {product.get('name', '')}")
            return jsonify(product), 201
        except ValueError as exc:
            return jsonify({"error": "Invalid data type", "details": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": "Failed to create product", "details": str(exc)}), 500

    @app.route("/products/<produkt_id>", methods=["GET"])
    def get_product(produkt_id):
        """Retrieve a specific product by its ID.

        Args:
            produkt_id (str): The unique identifier of the product.

        Returns:
            tuple: JSON response with product data and appropriate HTTP status.

        Raises:
            404: If product not found.
            500: If retrieval fails.
        """
        try:
            product = product_service.get_product(str(produkt_id))
            return jsonify(product) if product else jsonify({"error": "Product not found"}), (200 if product else 404)
        except Exception as exc:
            return jsonify({"error": "Failed to retrieve product", "details": str(exc)}), 500

    @app.route("/products/<produkt_id>", methods=["PUT"])
    def update_product(produkt_id):
        """Update an existing product.

        Args:
            produkt_id (str): The unique identifier of the product to update.

        Returns:
            tuple: JSON response with updated product and HTTP 200 status.

        Raises:
            400: If request body is not JSON.
            404: If product not found.
            500: If update fails.
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body must be JSON"}), 400
            updated_product = product_service.update_product(str(produkt_id), data)
            _log_history("product", "update", f"Produkt {produkt_id}: {json.dumps(data, ensure_ascii=False)}")
            return jsonify(updated_product), 200
        except KeyError:
            return jsonify({"error": "Product not found"}), 404
        except Exception as exc:
            return jsonify({"error": "Failed to update product", "details": str(exc)}), 500

    @app.route("/products/<produkt_id>", methods=["DELETE"])
    def delete_product(produkt_id):
        """Delete a product from the inventory.

        Args:
            produkt_id (str): The unique identifier of the product to delete.

        Returns:
            tuple: Empty response and HTTP status code (204 or 404).

        Raises:
            404: If product not found.
            500: If deletion fails.
        """
        try:
            existing = None
            try:
                existing = product_service.get_product(str(produkt_id))
            except Exception:
                existing = None
            product_service.delete_product(str(produkt_id))
            name = existing.get("name") if isinstance(existing, dict) else ""
            _log_history("product", "delete", f"Produkt {produkt_id}: {name}")
            return "", 204
        except KeyError:
            return jsonify({"error": "Product not found"}), 404
        except Exception as exc:
            return jsonify({"error": "Failed to delete product", "details": str(exc)}), 500

    @app.route("/warehouses", methods=["GET"])
    def get_warehouses():
        """Retrieve all warehouses with their inventory counts.

        Returns:
            tuple: JSON response with warehouses list and HTTP 200 status.

        Raises:
            500: If retrieval fails.
        """
        try:
            warehouses = warehouse_service.list_warehouses()
            inventory = inventory_service.db.find_all("inventory")
            for w in warehouses:
                w["products"] = sum(item["menge"] for item in inventory if item["lager_id"] == w["id"])
            return jsonify(warehouses), 200
        except Exception as exc:
            return jsonify({"error": "Failed to retrieve warehouses", "details": str(exc)}), 500

    @app.route("/warehouses", methods=["POST"])
    def create_warehouse():
        """Create a new warehouse.

        Returns:
            tuple: JSON response with created warehouse and HTTP 201 status.

        Raises:
            400: If required fields are missing or data type is invalid.
            500: If warehouse creation fails.
        """
        try:
            data = request.get_json()
            if not data or not all(k in data for k in ["lagername", "adresse", "max_plaetze", "firma_id"]):
                return jsonify({"error": "Missing required fields: lagername, adresse, max_plaetze, firma_id"}), 400
            warehouse = warehouse_service.create_warehouse(lagername=data["lagername"], adresse=data["adresse"], max_plaetze=int(data["max_plaetze"]), firma_id=int(data["firma_id"]))
            _log_history("warehouse", "create", f"Lager {warehouse.get('id')}: {warehouse.get('lagername', '')} ({warehouse.get('adresse', '')})")
            return jsonify(warehouse), 201
        except ValueError as exc:
            return jsonify({"error": "Invalid data type", "details": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": "Failed to create warehouse", "details": str(exc)}), 500

    @app.route("/warehouses/<lager_id>", methods=["DELETE"])
    def delete_warehouse(lager_id):
        """Delete a warehouse from the system.

        Args:
            lager_id (str): The unique identifier of the warehouse to delete.

        Returns:
            tuple: Empty response and HTTP status code (204 or 404).

        Raises:
            404: If warehouse not found.
            500: If deletion fails.
        """
        try:
            existing = None
            try:
                existing = warehouse_service.get_warehouse(str(lager_id))
            except Exception:
                existing = None
            warehouse_service.delete_warehouse(str(lager_id))
            name = existing.get("lagername") if isinstance(existing, dict) else ""
            addr = existing.get("adresse") if isinstance(existing, dict) else ""
            _log_history("warehouse", "delete", f"Lager {lager_id}: {name} ({addr})")
            return "", 204
        except KeyError:
            return jsonify({"error": "Warehouse not found"}), 404
        except Exception as exc:
            return jsonify({"error": "Failed to delete warehouse", "details": str(exc)}), 500

    @app.route("/inventory", methods=["POST"])
    def add_inventory():
        """Add a product to warehouse inventory.

        Returns:
            tuple: JSON response confirming operation and HTTP 201 status.

        Raises:
            400: If required fields are missing or data type is invalid.
            500: If inventory addition fails.
        """
        try:
            data = request.get_json()
            if not data or not all(k in data for k in ["lager_id", "produkt_id", "menge"]):
                return jsonify({"error": "Missing required fields: lager_id, produkt_id, menge"}), 400
            inventory_service.add_product(lager_id=int(data["lager_id"]), produkt_id=int(data["produkt_id"]), menge=int(data["menge"]))
            _log_history("inventory", "add", f"Bestand: produkt_id={data.get('produkt_id')} lager_id={data.get('lager_id')} menge={data.get('menge')}")
            return jsonify({"status": "ok", "message": "Product added to inventory"}), 201
        except ValueError as exc:
            return jsonify({"error": "Invalid data type", "details": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": "Failed to add inventory", "details": str(exc)}), 500

    @app.route("/inventory", methods=["PUT"])
    def set_inventory_quantity():
        """Set (upsert) a product quantity in a warehouse.

        Body: {lager_id, produkt_id, menge}
        - menge > 0: creates or updates the inventory entry
        - menge == 0: removes the inventory entry
        """

        try:
            data = request.get_json()
            if not data or not all(k in data for k in ["lager_id", "produkt_id", "menge"]):
                return jsonify({"error": "Missing required fields: lager_id, produkt_id, menge"}), 400
            lager_id = int(data["lager_id"])
            produkt_id = int(data["produkt_id"])
            menge = int(data["menge"])
            inventory_service.set_quantity(lager_id=lager_id, produkt_id=produkt_id, menge=menge)
            _log_history("inventory", "set", f"Bestand gesetzt: produkt_id={produkt_id} lager_id={lager_id} menge={menge}")
            return jsonify({"status": "ok"}), 200
        except ValueError as exc:
            return jsonify({"error": "Invalid data type", "details": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": "Failed to set inventory", "details": str(exc)}), 500

    @app.route("/inventory/<lager_id>/<produkt_id>", methods=["DELETE"])
    def delete_inventory_entry(lager_id, produkt_id):
        """Remove a product from a warehouse inventory."""

        try:
            inventory_service.remove_product(lager_id=int(lager_id), produkt_id=int(produkt_id))
            _log_history("inventory", "remove", f"Bestand entfernt: produkt_id={produkt_id} lager_id={lager_id}")
            return "", 204
        except KeyError:
            return jsonify({"error": "Inventory entry not found"}), 404
        except Exception as exc:
            return jsonify({"error": "Failed to remove inventory", "details": str(exc)}), 500

    @app.route("/inventory/products/<produkt_id>", methods=["GET"])
    def get_product_inventory(produkt_id):
        """Retrieve all inventory entries for a given product."""

        try:
            inventory = inventory_service.db.find_all("inventory")
            produkt_id_int = int(produkt_id)
            product_inventory = [item for item in inventory if int(item["produkt_id"]) == produkt_id_int]
            return jsonify(product_inventory), 200
        except Exception as exc:
            return jsonify({"error": "Failed to retrieve product inventory", "details": str(exc)}), 500

    @app.route("/inventory/<lager_id>/products", methods=["GET"])
    def get_warehouse_inventory(lager_id):
        """Retrieve all products in a specific warehouse.

        Args:
            lager_id (str): The unique identifier of the warehouse.

        Returns:
            tuple: JSON response with inventory items and HTTP 200 status.

        Raises:
            500: If retrieval fails.
        """
        try:
            inventory = inventory_service.db.find_all("inventory")
            warehouse_inventory = [item for item in inventory if item["lager_id"] == int(lager_id)]
            return jsonify(warehouse_inventory), 200
        except Exception as exc:
            return jsonify({"error": "Failed to retrieve warehouse inventory", "details": str(exc)}), 500

    @app.route("/lagerprodukte", methods=["POST"])
    def add_product_to_warehouse():
        """Assign a product to a warehouse.

        Returns:
            tuple: JSON response confirming operation and HTTP 201 status.

        Raises:
            400: If required fields are missing or data type is invalid.
            500: If product assignment fails.
        """
        try:
            data = request.get_json()
            if not data or not all(k in data for k in ["lager_id", "produkt_id", "menge"]):
                return jsonify({"error": "Missing required fields: lager_id, produkt_id, menge"}), 400
            warehouse_service.add_product_to_warehouse(lager_id=int(data["lager_id"]), produkt_id=int(data["produkt_id"]), menge=int(data["menge"]))
            _log_history("inventory", "assign", f"Buchung: produkt_id={data.get('produkt_id')} lager_id={data.get('lager_id')} menge={data.get('menge')}")
            return jsonify({"status": "ok", "message": "Product assigned to warehouse"}), 201
        except ValueError as exc:
            return jsonify({"error": "Invalid data type", "details": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": "Failed to add product to warehouse", "details": str(exc)}), 500

