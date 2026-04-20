"""Abstract base class (port) for product-related business logic."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class ProductServicePort(ABC):
    """Abstract interface for product-related business logic."""

    @abstractmethod
    def create_product(
        self,
        name: str,
        description: str,
        weight: float,
        price: float = 0.0,
        performed_by: str = "system",
    ) -> Dict:
        """Create a new product and persist it.

        Args:
            name: Human-readable product name.
            description: Short description of the product.
            weight: Weight of the product in kilograms. Must be >= 0.
            price: Unit price of the product. Must be >= 0.
            performed_by: Name or identifier of the user performing the action.

        Returns:
            A dictionary representing the newly created product.

        Raises:
            ValueError: If any argument fails domain validation.
        """
        ...

    @abstractmethod
    def get_product(self, product_id: str) -> Optional[Dict]:
        """Retrieve a single product by its unique identifier.

        Args:
            product_id: Unique product identifier.

        Returns:
            Product data if found, otherwise None.
        """
        ...

    @abstractmethod
    def list_products(self) -> List[Dict]:
        """Return all known products.

        Returns:
            A list of all product representations.
        """
        ...

    @abstractmethod
    def update_product(self, product_id: str, data: Dict, performed_by: str = "system") -> Dict:
        """Update fields of an existing product.

        Args:
            product_id: Unique product identifier.
            data: Dictionary of fields to update.
            performed_by: Name or identifier of the user performing the action.

        Returns:
            The updated product representation.

        Raises:
            KeyError: If no product with the given ID exists.
            ValueError: If any updated field fails domain validation.
        """
        ...

    @abstractmethod
    def delete_product(self, product_id: str, performed_by: str = "system") -> None:
        """Permanently delete a product.

        Args:
            product_id: Unique product identifier.
            performed_by: Name or identifier of the user performing the action.

        Raises:
            KeyError: If no product with the given ID exists.
        """
        ...
