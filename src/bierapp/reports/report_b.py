from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from ..contracts import ReportPort
from ..backend.service import ProductService, WarehouseService, InventoryService

class ReportB(ReportPort):
    ...