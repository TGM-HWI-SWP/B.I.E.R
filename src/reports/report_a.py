from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from ..bierapp.contracts import ReportPort
from ..bierapp.backend.service import ProductService, WarehouseService, InventoryService

class ReportA(ReportPort):
    ...