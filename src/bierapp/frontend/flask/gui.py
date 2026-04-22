"""B.I.E.R Flask GUI - Route handlers for the inventory management system."""

import os
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

    def _format_value(value) -> str:
        if value is None:
            return "-"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    def _format_changes(data: dict, labels: dict[str, str]) -> str:
        if not isinstance(data, dict) or not data:
            return "Keine Detailangaben"
        parts = []
        for key, value in data.items():
            label = labels.get(key, key.replace("_", " ").capitalize())
            parts.append(f"{label}: {_format_value(value)}")
        return ", ".join(parts)

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

    def _build_stats() -> dict:
        warehouses = warehouse_service.list_warehouses()
        products = product_service.list_products()
        inventory_rows = inventory_service.db.find_all("inventory")

        product_meta = {
            str(product.get("id")): {
                "name": product.get("name") or f"Produkt {product.get('id')}",
                "preis": float(product.get("preis") or 0),
                "waehrung": product.get("waehrung") or "EUR",
                "lieferant": product.get("lieferant") or "Unbekannt",
                "einheit": product.get("einheit") or "Stk",
            }
            for product in products
        }

        warehouse_rows = []
        product_totals: dict[str, int] = {}
        currency_totals: dict[str, float] = {}
        unit_totals: dict[str, int] = {}
        supplier_totals: dict[str, int] = {}

        for warehouse in warehouses:
            wid = str(warehouse.get("id"))
            items = [row for row in inventory_rows if str(row.get("lager_id")) == wid]
            total_products = sum(int(row.get("menge") or 0) for row in items)
            capacity = int(warehouse.get("max_plaetze") or 0)
            util = (total_products / capacity) if capacity > 0 else 0

            warehouse_rows.append(
                {
                    "id": warehouse.get("id"),
                    "name": warehouse.get("lagername") or f"Lager {warehouse.get('id')}",
                    "products": total_products,
                    "capacity": capacity,
                    "util": util,
                }
            )

            for row in items:
                product_id = str(row.get("produkt_id"))
                qty = int(row.get("menge") or 0)
                product_totals[product_id] = product_totals.get(product_id, 0) + qty

                meta = product_meta.get(product_id, {
                    "name": f"Produkt {product_id}",
                    "preis": 0.0,
                    "waehrung": "EUR",
                    "lieferant": "Unbekannt",
                    "einheit": "Stk",
                })
                currency_totals[meta["waehrung"]] = currency_totals.get(meta["waehrung"], 0.0) + meta["preis"] * qty
                unit_totals[meta["einheit"]] = unit_totals.get(meta["einheit"], 0) + qty
                supplier_totals[meta["lieferant"]] = supplier_totals.get(meta["lieferant"], 0) + qty

        warehouse_rows.sort(key=lambda item: item["products"], reverse=True)
        utilization_rows = sorted(warehouse_rows, key=lambda item: item["util"], reverse=True)
        top_products = sorted(
            (
                {
                    "name": product_meta.get(product_id, {}).get("name", f"Produkt {product_id}"),
                    "qty": qty,
                }
                for product_id, qty in product_totals.items()
            ),
            key=lambda item: item["qty"],
            reverse=True,
        )
        currency_rows = sorted(currency_totals.items(), key=lambda item: item[1], reverse=True)
        unit_rows = sorted(unit_totals.items(), key=lambda item: item[1], reverse=True)
        supplier_rows = sorted(supplier_totals.items(), key=lambda item: item[1], reverse=True)

        total_warehouses = len(warehouses)
        total_products = sum(item["products"] for item in warehouse_rows)
        total_capacity = sum(item["capacity"] for item in warehouse_rows)
        free_capacity = max(0, total_capacity - total_products)
        avg_util = sum(item["util"] for item in warehouse_rows) / total_warehouses if total_warehouses else 0
        active_warehouses = sum(1 for item in warehouse_rows if item["products"] > 0)
        top_product = top_products[0] if top_products else None
        max_util = utilization_rows[0] if utilization_rows else None
        total_inventory_value = sum(value for _, value in currency_rows)
        main_currency = currency_rows[0][0] if currency_rows else "-"
        top_supplier = supplier_rows[0] if supplier_rows else None

        return {
            "warehouses": total_warehouses,
            "products": total_products,
            "capacity": total_capacity,
            "free_capacity": free_capacity,
            "avg_util": avg_util,
            "active_warehouses": active_warehouses,
            "total_inventory_value": total_inventory_value,
            "main_currency": main_currency,
            "top_product": top_product,
            "max_util": max_util,
            "top_supplier": top_supplier,
            "warehouse_rows": warehouse_rows,
            "utilization_rows": utilization_rows,
            "top_products": top_products,
            "currency_rows": currency_rows,
            "unit_rows": unit_rows,
            "supplier_rows": supplier_rows,
        }

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

    @app.route("/pictures/<path:filename>", endpoint="picture", methods=["GET"])
    def picture(filename: str):
        """Serve image assets from the resources pictures directory."""
        pictures_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "pictures"))
        return send_from_directory(pictures_dir, filename)

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
        stats = _build_stats()
        return render_template("page3.html", selected_theme=selected_theme, theme_options=_theme_options(), stats=stats)

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
                preis=float(data.get("preis", 0)),
                waehrung=data.get("waehrung", "EUR"),
                lieferant=data.get("lieferant", ""),
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
            changes = _format_changes(
                data,
                {
                    "name": "Name",
                    "beschreibung": "Beschreibung",
                    "gewicht": "Gewicht",
                    "preis": "Preis",
                    "waehrung": "Währung",
                    "lieferant": "Lieferant",
                    "einheit": "Einheit",
                },
            )
            _log_history("product", "update", f"Produkt {produkt_id}: {changes}")
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
            if not data or not all(k in data for k in ["lagername", "adresse", "max_plaetze"]):
                return jsonify({"error": "Missing required fields: lagername, adresse, max_plaetze"}), 400
            firma_id = int(data.get("firma_id", 1))
            warehouse = warehouse_service.create_warehouse(lagername=data["lagername"], adresse=data["adresse"], max_plaetze=int(data["max_plaetze"]), firma_id=firma_id)
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

    @app.route("/warehouses/<lager_id>", methods=["PUT"])
    def update_warehouse(lager_id):
        """Update a warehouse."""

        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body must be JSON"}), 400

            payload = {}
            if "lagername" in data:
                payload["lagername"] = str(data.get("lagername") or "").strip()
                if not payload["lagername"]:
                    return jsonify({"error": "lagername must not be empty"}), 400
            if "adresse" in data:
                payload["adresse"] = str(data.get("adresse") or "").strip()
            if "max_plaetze" in data:
                payload["max_plaetze"] = int(data.get("max_plaetze"))
            if "firma_id" in data:
                payload["firma_id"] = int(data.get("firma_id"))

            if not payload:
                return jsonify({"error": "No updatable fields provided"}), 400

            updated = warehouse_service.update_warehouse(str(lager_id), payload)
            changes = _format_changes(
                payload,
                {
                    "lagername": "Lagername",
                    "adresse": "Adresse",
                    "max_plaetze": "Max. Plätze",
                    "firma_id": "Firma-ID",
                },
            )
            _log_history("warehouse", "update", f"Lager {lager_id}: {changes}")
            return jsonify(updated), 200
        except ValueError as exc:
            return jsonify({"error": "Invalid data type", "details": str(exc)}), 400
        except KeyError:
            return jsonify({"error": "Warehouse not found"}), 404
        except Exception as exc:
            return jsonify({"error": "Failed to update warehouse", "details": str(exc)}), 500

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
            _log_history(
                "inventory",
                "add",
                f"Produkt {data.get('produkt_id')} in Lager {data.get('lager_id')}: +{data.get('menge')}",
            )
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
            _log_history("inventory", "set", f"Produkt {produkt_id} in Lager {lager_id}: Menge auf {menge} gesetzt")
            return jsonify({"status": "ok"}), 200
        except ValueError as exc:
            return jsonify({"error": "Invalid data type", "details": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": "Failed to set inventory", "details": str(exc)}), 500

    @app.route("/inventory/move", methods=["POST"])
    def move_inventory_quantity():
        """Move quantity of a product from one warehouse to another.

        Body: {source_lager_id, target_lager_id, produkt_id, menge}
        - subtracts menge from source
        - adds menge to target (never overwrite)
        """

        try:
            data = request.get_json()
            required = ["source_lager_id", "target_lager_id", "produkt_id", "menge"]
            if not data or not all(k in data for k in required):
                return jsonify({"error": "Missing required fields: source_lager_id, target_lager_id, produkt_id, menge"}), 400

            source_lager_id = int(data["source_lager_id"])
            target_lager_id = int(data["target_lager_id"])
            produkt_id = int(data["produkt_id"])
            menge = int(data["menge"])

            if source_lager_id == target_lager_id:
                return jsonify({"error": "Source and target warehouse must be different"}), 400
            if menge <= 0:
                return jsonify({"error": "menge must be a positive integer"}), 400

            source_rows = inventory_service.list_inventory(source_lager_id)
            source_item = next((item for item in source_rows if int(item.get("produkt_id")) == produkt_id), None)
            source_qty = int(source_item.get("menge", 0)) if source_item else 0
            if source_qty < menge:
                return jsonify({"error": "Not enough stock in source warehouse"}), 400

            target_rows = inventory_service.list_inventory(target_lager_id)
            target_item = next((item for item in target_rows if int(item.get("produkt_id")) == produkt_id), None)
            target_qty = int(target_item.get("menge", 0)) if target_item else 0

            inventory_service.set_quantity(source_lager_id, produkt_id, source_qty - menge)
            inventory_service.set_quantity(target_lager_id, produkt_id, target_qty + menge)

            _log_history(
                "inventory",
                "move",
                f"Produkt {produkt_id}: {menge} von Lager {source_lager_id} nach Lager {target_lager_id} verschoben",
            )
            return jsonify({"status": "ok", "source_qty": source_qty - menge, "target_qty": target_qty + menge}), 200
        except ValueError as exc:
            return jsonify({"error": "Invalid data type", "details": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": "Failed to move inventory", "details": str(exc)}), 500

    @app.route("/inventory/<lager_id>/<produkt_id>", methods=["DELETE"])
    def delete_inventory_entry(lager_id, produkt_id):
        """Remove a product from a warehouse inventory."""

        try:
            inventory_service.remove_product(lager_id=int(lager_id), produkt_id=int(produkt_id))
            _log_history("inventory", "remove", f"Produkt {produkt_id} aus Lager {lager_id} entfernt")
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
            _log_history(
                "inventory",
                "assign",
                f"Produkt {data.get('produkt_id')} in Lager {data.get('lager_id')}: +{data.get('menge')}",
            )
            return jsonify({"status": "ok", "message": "Product assigned to warehouse"}), 201
        except ValueError as exc:
            return jsonify({"error": "Invalid data type", "details": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": "Failed to add product to warehouse", "details": str(exc)}), 500

