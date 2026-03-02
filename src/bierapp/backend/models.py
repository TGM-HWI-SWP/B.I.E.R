"""Domain model dataclasses for the B.I.E.R application.

Each dataclass represents a core business entity. Validation is centralised in
``__post_init__`` so that no service code needs to duplicate the same checks.
``to_doc()`` converts an instance to the plain dict expected by MongoDBAdapter.
"""

from dataclasses import dataclass

@dataclass
class Product:
    """A product stored in the catalogue.

    Attributes:
        name: Human-readable product name. Must not be empty.
        description: Short description of the product.
        weight: Weight in kilograms. Must be >= 0.
        price: Unit price. Must be >= 0. Defaults to 0.0.
    """

    name: str
    description: str
    weight: float
    price: float = 0.0

    def __post_init__(self) -> None:
        """Strip whitespace and validate all fields after construction."""
        self.name = self.name.strip()
        self.description = self.description.strip()
        self.weight = float(self.weight)
        self.price = float(self.price)

        if not self.name:
            raise ValueError("Produktname darf nicht leer sein.")
        if self.weight < 0:
            raise ValueError("Gewicht muss >= 0 sein.")
        if self.price < 0:
            raise ValueError("Preis muss >= 0 sein.")

    def to_doc(self) -> dict:
        """Return a MongoDB-compatible document representation.

        Returns:
            Dictionary with German field names used in the database schema.
        """
        return {
            "name": self.name,
            "beschreibung": self.description,
            "gewicht": self.weight,
            "preis": self.price,
        }

@dataclass
class Warehouse:
    """A warehouse that can store products.

    Attributes:
        name: Human-readable warehouse name. Must not be empty.
        address: Physical address of the warehouse.
        max_slots: Maximum number of distinct product slots. Must be > 0.
    """

    name: str
    address: str
    max_slots: int

    def __post_init__(self) -> None:
        """Strip whitespace and validate all fields after construction."""
        self.name = self.name.strip()
        self.address = self.address.strip()

        if not self.name:
            raise ValueError("Lagername darf nicht leer sein.")
        if not isinstance(self.max_slots, int) or self.max_slots <= 0:
            raise ValueError("max_plaetze muss eine positive ganze Zahl sein.")

    def to_doc(self) -> dict:
        """Return a MongoDB-compatible document representation.

        Returns:
            Dictionary with German field names used in the database schema.
        """
        return {
            "lagername": self.name,
            "adresse": self.address,
            "max_plaetze": self.max_slots,
        }

@dataclass
class InventoryEntry:
    """A single product-in-warehouse stock record.

    Attributes:
        warehouse_id: ID of the warehouse holding the stock.
        product_id: ID of the product being stocked.
        quantity: Number of units. Must be a non-negative integer.
    """

    warehouse_id: str
    product_id: str
    quantity: int

    def __post_init__(self) -> None:
        """Validate quantity after construction."""
        if not isinstance(self.quantity, int) or self.quantity < 0:
            raise ValueError("Menge muss eine nicht-negative ganze Zahl sein.")

    def to_doc(self) -> dict:
        """Return a MongoDB-compatible document representation.

        Returns:
            Dictionary with German field names used in the database schema.
        """
        return {
            "lager_id": self.warehouse_id,
            "produkt_id": self.product_id,
            "menge": self.quantity,
        }

@dataclass
class Event:
    """An audit log entry recording a domain action.

    Attributes:
        timestamp: ISO 8601 timestamp string of when the action occurred.
        entity_type: Category of the affected entity (e.g. 'produkt', 'lager').
        action: Name of the action performed (e.g. 'create', 'update').
        entity_id: Unique identifier of the affected entity.
        summary: Human-readable description of what happened.
        performed_by: Name or identifier of the acting user. Defaults to 'system'.
    """

    timestamp: str
    entity_type: str
    action: str
    entity_id: str
    summary: str
    performed_by: str = "system"

    def to_doc(self) -> dict:
        """Return a MongoDB-compatible document representation.

        Returns:
            Dictionary ready to be inserted into the events collection.
        """
        return {
            "timestamp": self.timestamp,
            "entity_type": self.entity_type,
            "action": self.action,
            "entity_id": self.entity_id,
            "performed_by": self.performed_by,
            "summary": self.summary,
        }
