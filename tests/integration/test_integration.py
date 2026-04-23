def test_create_product_and_get_by_id(client):
	create_response = client.post(
		"/products",
		json={"name": "Lagerbier", "beschreibung": "Hell", "gewicht": 1.2, "preis": 2.5},
	)

	assert create_response.status_code == 201
	created = create_response.get_json()
	assert created["name"] == "Lagerbier"
	assert "id" in created

	get_response = client.get(f"/products/{created['id']}")
	assert get_response.status_code == 200
	assert get_response.get_json()["id"] == created["id"]


def test_create_product_rejects_missing_required_fields(client):
	response = client.post("/products", json={"beschreibung": "Oops"})

	assert response.status_code == 400
	assert "Missing required fields" in response.get_json()["error"]


def test_update_unknown_product_returns_404(client):
	response = client.put("/products/9999", json={"name": "Neu"})

	assert response.status_code == 404
	assert response.get_json()["error"] == "Product not found"


def test_delete_unknown_product_returns_404(client):
	response = client.delete("/products/404")

	assert response.status_code == 404


def test_create_warehouse_and_list_contains_products_count(client):
	warehouse_response = client.post(
		"/warehouses",
		json={"lagername": "Halle A", "adresse": "Wien", "max_plaetze": 50, "firma_id": 1},
	)
	product_response = client.post(
		"/products",
		json={"name": "Pale Ale", "beschreibung": "Hopfig", "gewicht": 1.0},
	)

	assert warehouse_response.status_code == 201
	assert product_response.status_code == 201

	warehouse_id = warehouse_response.get_json()["id"]
	product_id = product_response.get_json()["id"]

	add_inventory = client.post(
		"/inventory",
		json={"lager_id": int(warehouse_id), "produkt_id": int(product_id), "menge": 7},
	)
	assert add_inventory.status_code == 201

	warehouses_response = client.get("/warehouses")
	assert warehouses_response.status_code == 200
	warehouses = warehouses_response.get_json()
	assert len(warehouses) == 1
	assert warehouses[0]["products"] == 7


def test_create_warehouse_rejects_invalid_payload(client):
	response = client.post(
		"/warehouses",
		json={"lagername": "X", "adresse": "Y", "max_plaetze": "kein-int"},
	)

	assert response.status_code == 400
	assert response.get_json()["error"] == "Invalid data type"


def test_set_inventory_to_zero_removes_item(client):
	warehouse = client.post(
		"/warehouses",
		json={"lagername": "Halle B", "adresse": "Linz", "max_plaetze": 10},
	).get_json()
	product = client.post(
		"/products",
		json={"name": "Pils", "beschreibung": "Klar", "gewicht": 1.0},
	).get_json()

	create_response = client.put(
		"/inventory",
		json={"lager_id": int(warehouse["id"]), "produkt_id": int(product["id"]), "menge": 3},
	)
	assert create_response.status_code == 200

	remove_response = client.put(
		"/inventory",
		json={"lager_id": int(warehouse["id"]), "produkt_id": int(product["id"]), "menge": 0},
	)
	assert remove_response.status_code == 200

	inventory_response = client.get(f"/inventory/{warehouse['id']}/products")
	assert inventory_response.status_code == 200
	assert inventory_response.get_json() == []


def test_move_inventory_returns_error_when_source_equals_target(client):
	response = client.post(
		"/inventory/move",
		json={"source_lager_id": 1, "target_lager_id": 1, "produkt_id": 5, "menge": 1},
	)

	assert response.status_code == 400
	assert response.get_json()["error"] == "Source and target warehouse must be different"


def test_move_inventory_returns_error_when_stock_is_insufficient(client):
	source = client.post(
		"/warehouses",
		json={"lagername": "Q1", "adresse": "A", "max_plaetze": 10},
	).get_json()
	target = client.post(
		"/warehouses",
		json={"lagername": "Q2", "adresse": "B", "max_plaetze": 10},
	).get_json()
	product = client.post(
		"/products",
		json={"name": "Stout", "beschreibung": "Dark", "gewicht": 1.0},
	).get_json()

	client.put(
		"/inventory",
		json={"lager_id": int(source["id"]), "produkt_id": int(product["id"]), "menge": 2},
	)

	move_response = client.post(
		"/inventory/move",
		json={
			"source_lager_id": int(source["id"]),
			"target_lager_id": int(target["id"]),
			"produkt_id": int(product["id"]),
			"menge": 5,
		},
	)
	assert move_response.status_code == 400
	assert move_response.get_json()["error"] == "Not enough stock in source warehouse"


def test_move_inventory_successfully_updates_both_warehouses(client):
	source = client.post(
		"/warehouses",
		json={"lagername": "S", "adresse": "A", "max_plaetze": 10},
	).get_json()
	target = client.post(
		"/warehouses",
		json={"lagername": "T", "adresse": "B", "max_plaetze": 10},
	).get_json()
	product = client.post(
		"/products",
		json={"name": "Weizen", "beschreibung": "Mild", "gewicht": 1.0},
	).get_json()

	client.put(
		"/inventory",
		json={"lager_id": int(source["id"]), "produkt_id": int(product["id"]), "menge": 8},
	)
	client.put(
		"/inventory",
		json={"lager_id": int(target["id"]), "produkt_id": int(product["id"]), "menge": 1},
	)

	move_response = client.post(
		"/inventory/move",
		json={
			"source_lager_id": int(source["id"]),
			"target_lager_id": int(target["id"]),
			"produkt_id": int(product["id"]),
			"menge": 3,
		},
	)
	assert move_response.status_code == 200
	payload = move_response.get_json()
	assert payload["source_qty"] == 5
	assert payload["target_qty"] == 4
