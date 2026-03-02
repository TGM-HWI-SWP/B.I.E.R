"""Helper functions for the Flask UI layer.

These functions contain the computation logic that supports the route
handlers in gui.py. Keeping the computation separate from the HTTP
layer makes each piece easier to read and test independently.
"""

from collections import defaultdict
from typing import Dict, List

def enrich_warehouses(warehouse_list: List[Dict], all_inventory: List[Dict]) -> List[Dict]:
    """Attach aggregated stock quantity and product count to each warehouse.

    Args:
        warehouse_list: Raw warehouse documents from the database.
        all_inventory: All inventory entries from the database.

    Returns:
        A copy of the warehouse list where each document has two extra fields:
        - menge: total units stocked in that warehouse
        - num_produkte: number of distinct products stored in that warehouse
    """
    # Build aggregate totals per warehouse from the full inventory list
    quantity_per_warehouse: Dict[str, int] = defaultdict(int)
    products_per_warehouse: Dict[str, set] = defaultdict(set)

    for entry in all_inventory:
        warehouse_id = entry.get("lager_id", "")
        product_id = entry.get("produkt_id", "")
        quantity = entry.get("menge", 0)
        quantity_per_warehouse[warehouse_id] += quantity
        products_per_warehouse[warehouse_id].add(product_id)

    enriched = []
    for warehouse in warehouse_list:
        warehouse_id = warehouse["_id"]
        enriched_warehouse = dict(warehouse)
        enriched_warehouse["menge"] = quantity_per_warehouse.get(warehouse_id, 0)
        enriched_warehouse["num_produkte"] = len(products_per_warehouse.get(warehouse_id, set()))
        enriched.append(enriched_warehouse)

    return enriched

def compute_warehouse_aggregates(
    warehouses: List[Dict],
    inventory: List[Dict],
) -> tuple:
    """Compute per-warehouse quantity and distinct product counts.

    Args:
        warehouses: All warehouse documents.
        inventory: All inventory entries.

    Returns:
        A tuple of four items:
        - quantity_per_warehouse: dict mapping warehouse _id to total units stored
        - products_per_warehouse: dict mapping warehouse _id to a set of product IDs
        - warehouse_labels: list of warehouse display names
        - warehouse_quantities: list of total unit counts matching warehouse_labels order
    """
    quantity_per_warehouse: Dict[str, int] = defaultdict(int)
    products_per_warehouse: Dict[str, set] = defaultdict(set)

    for entry in inventory:
        warehouse_id = entry.get("lager_id", "")
        product_id = entry.get("produkt_id", "")
        quantity = entry.get("menge", 0)
        quantity_per_warehouse[warehouse_id] += quantity
        products_per_warehouse[warehouse_id].add(product_id)

    warehouse_labels = []
    warehouse_quantities = []
    for warehouse in warehouses:
        warehouse_labels.append(warehouse.get("lagername", warehouse["_id"]))
        warehouse_quantities.append(quantity_per_warehouse.get(warehouse["_id"], 0))

    return (
        quantity_per_warehouse,
        products_per_warehouse,
        warehouse_labels,
        warehouse_quantities,
    )

def compute_warehouse_stats(
    warehouses: List[Dict],
    quantity_per_warehouse: Dict[str, int],
    products_per_warehouse: Dict[str, set],
) -> List[Dict]:
    """Build a list of warehouse summary dictionaries for template rendering.

    Args:
        warehouses: All warehouse documents.
        quantity_per_warehouse: Total units per warehouse ID.
        products_per_warehouse: Set of product IDs per warehouse ID.

    Returns:
        A list of dictionaries, one per warehouse, with keys:
        lagername, num_produkte, menge, max_plaetze.
    """
    warehouse_stats = []
    for warehouse in warehouses:
        warehouse_id = warehouse["_id"]
        stat = {
            "lagername": warehouse.get("lagername", warehouse_id),
            "num_produkte": len(products_per_warehouse.get(warehouse_id, set())),
            "menge": quantity_per_warehouse.get(warehouse_id, 0),
            "max_plaetze": warehouse.get("max_plaetze", 1),
        }
        warehouse_stats.append(stat)
    return warehouse_stats

def compute_utilisation(warehouse_stats: List[Dict]) -> tuple:
    """Calculate storage utilisation as a percentage per warehouse.

    Utilisation is measured as the number of distinct product types stored
    divided by the maximum number of product slots, capped at 100%.

    Args:
        warehouse_stats: List of warehouse stat dicts (from compute_warehouse_stats).

    Returns:
        A tuple of:
        - utilisation_labels: list of warehouse names
        - utilisation_pct: list of percentage values (0.0 to 100.0) in the same order
    """
    utilisation_labels = []
    utilisation_pct = []

    for stat in warehouse_stats:
        warehouse_name = stat["lagername"]
        num_products = stat["num_produkte"]
        max_slots = max(stat["max_plaetze"], 1)  # Avoid division by zero

        raw_percentage = num_products / max_slots * 100
        capped_percentage = min(raw_percentage, 100)
        rounded_percentage = round(capped_percentage, 1)

        utilisation_labels.append(warehouse_name)
        utilisation_pct.append(rounded_percentage)

    return utilisation_labels, utilisation_pct

def compute_category_counts(products: List[Dict]) -> tuple:
    """Count how many products belong to each category.

    Args:
        products: All product documents.

    Returns:
        A tuple of:
        - category_labels: list of category names
        - category_counts: list of counts matching the labels order
    """
    counts_by_category: Dict[str, int] = defaultdict(int)

    for product in products:
        category = product.get("kategorie") or "Sonstige"
        counts_by_category[category] += 1

    category_labels = list(counts_by_category.keys())
    category_counts = list(counts_by_category.values())

    return category_labels, category_counts

def compute_top10_products(products: List[Dict], inventory: List[Dict]) -> tuple:
    """Find the 10 most-stocked products across all warehouses.

    Args:
        products: All product documents.
        inventory: All inventory entries.

    Returns:
        A tuple of:
        - top10_labels: display names of the top-10 products
        - top10_values: total units stocked for each product in the same order
    """
    # Build a name lookup map
    product_name_by_id: Dict[str, str] = {}
    for product in products:
        product_name_by_id[product["_id"]] = product.get("name", product["_id"])

    # Sum quantities per product across all warehouses
    quantity_per_product: Dict[str, int] = defaultdict(int)
    for entry in inventory:
        product_id = entry.get("produkt_id", "")
        quantity = entry.get("menge", 0)
        quantity_per_product[product_id] += quantity

    # Sort descending and take the top 10
    all_products_sorted = sorted(
        quantity_per_product.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    top10 = all_products_sorted[:10]

    top10_labels = []
    top10_values = []
    for product_id, quantity in top10:
        top10_labels.append(product_name_by_id.get(product_id, product_id))
        top10_values.append(quantity)

    return top10_labels, top10_values

def compute_warehouse_top_products(
    warehouses: List[Dict],
    products: List[Dict],
    inventory: List[Dict],
) -> tuple:
    """Find the top-10 most-stocked products for each individual warehouse.

    Args:
        warehouses: All warehouse documents.
        products: All product documents.
        inventory: All inventory entries.

    Returns:
        A tuple of:
        - warehouse_top_labels: list of lists, one inner list per warehouse
        - warehouse_top_values: matching quantities, same structure
    """
    product_name_by_id: Dict[str, str] = {}
    for product in products:
        product_name_by_id[product["_id"]] = product.get("name", product["_id"])

    # Build per-warehouse quantity maps
    qty_per_warehouse_product: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for entry in inventory:
        warehouse_id = entry.get("lager_id", "")
        product_id = entry.get("produkt_id", "")
        quantity = entry.get("menge", 0)
        qty_per_warehouse_product[warehouse_id][product_id] += quantity

    warehouse_top_labels = []
    warehouse_top_values = []

    for warehouse in warehouses:
        warehouse_id = warehouse["_id"]
        product_quantities = qty_per_warehouse_product.get(warehouse_id, {})

        if product_quantities:
            sorted_products = sorted(
                product_quantities.items(),
                key=lambda item: item[1],
                reverse=True,
            )
            top10 = sorted_products[:10]
            labels = [product_name_by_id.get(pid, pid) for pid, _ in top10]
            values = [qty for _, qty in top10]
        else:
            labels = []
            values = []

        warehouse_top_labels.append(labels)
        warehouse_top_values.append(values)

    return warehouse_top_labels, warehouse_top_values

def compute_warehouse_values(
    warehouses: List[Dict],
    products: List[Dict],
    inventory: List[Dict],
) -> tuple:
    """Calculate the total monetary stock value per warehouse.

    Args:
        warehouses: All warehouse documents.
        products: All product documents (must include 'preis' field).
        inventory: All inventory entries.

    Returns:
        A tuple of:
        - warehouse_values: list of euro values in the same order as warehouses
        - total_value: the grand total across all warehouses
    """
    price_by_product_id: Dict[str, float] = {}
    for product in products:
        price_by_product_id[product["_id"]] = float(product.get("preis", 0.0))

    value_per_warehouse: Dict[str, float] = defaultdict(float)
    for entry in inventory:
        warehouse_id = entry.get("lager_id", "")
        product_id = entry.get("produkt_id", "")
        quantity = int(entry.get("menge", 0))
        price = price_by_product_id.get(product_id, 0.0)
        value_per_warehouse[warehouse_id] += quantity * price

    warehouse_values = []
    for warehouse in warehouses:
        value = value_per_warehouse.get(warehouse["_id"], 0.0)
        warehouse_values.append(round(value, 2))

    total_value = sum(warehouse_values)

    return warehouse_values, total_value
