"""Contracts package – abstract port interfaces for the B.I.E.R application.

Each port is defined in its own module and re-exported here so that the
rest of the application can import from a single location:

    from bierapp.contracts import DatabasePort, ProductServicePort, ...
"""

from bierapp.contracts.database_port import DatabasePort
from bierapp.contracts.http_port import HttpResponsePort
from bierapp.contracts.inventory_port import InventoryServicePort
from bierapp.contracts.product_port import ProductServicePort
from bierapp.contracts.report_port import ReportPort
from bierapp.contracts.warehouse_port import WarehouseServicePort

__all__ = [
    "DatabasePort",
    "HttpResponsePort",
    "InventoryServicePort",
    "ProductServicePort",
    "ReportPort",
    "WarehouseServicePort",
]
