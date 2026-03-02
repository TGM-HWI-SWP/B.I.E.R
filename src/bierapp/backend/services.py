"""Aggregates all service classes for convenient top-level imports.

Import any service class directly from this module:

    from bierapp.backend.services import ProductService
    from bierapp.backend.services import WarehouseService
    from bierapp.backend.services import InventoryService
"""

from bierapp.backend.inventory_service import InventoryService
from bierapp.backend.product_service import ProductService
from bierapp.backend.warehouse_service import WarehouseService

__all__ = [
    "InventoryService",
    "ProductService",
    "WarehouseService",
]
