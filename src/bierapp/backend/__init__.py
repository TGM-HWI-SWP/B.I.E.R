"""Backend package – service implementations for B.I.E.R business logic.

Import the service classes you need directly from this package:

    from bierapp.backend import ProductService, WarehouseService, InventoryService
"""

from bierapp.backend.inventory_service import InventoryService
from bierapp.backend.product_service import ProductService
from bierapp.backend.warehouse_service import WarehouseService

__all__ = [
    "InventoryService",
    "ProductService",
    "WarehouseService",
]
