"""Abstract base class (port) for report generation."""

from abc import ABC, abstractmethod
from typing import Dict, List

class ReportPort(ABC):
    """Abstract interface for report generation."""

    @abstractmethod
    def inventory_report(self, warehouse_id: str) -> List[Dict]:
        """Generate an inventory report for a specific warehouse.

        Args:
            warehouse_id: Unique warehouse identifier.

        Returns:
            An ordered list of inventory entries including product details
            and current stock levels.

        Raises:
            KeyError: If no warehouse with the given ID exists.
        """
        ...

    @abstractmethod
    def statistics_report(self) -> Dict:
        """Generate global statistics across all warehouses and products.

        Returns:
            Aggregated statistics such as total products, total warehouses,
            total stock units and overall capacity usage.
        """
        ...
