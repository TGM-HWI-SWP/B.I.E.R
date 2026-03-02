"""Abstract base class (port) for HTTP response handling."""

from abc import ABC, abstractmethod
from typing import Dict

class HttpResponsePort(ABC):
    """Abstract interface for HTTP response handling (Flask adapter)."""

    @abstractmethod
    def success(self, data: Dict, status: int = 200) -> tuple:
        """Build a successful HTTP JSON response.

        Args:
            data: Payload to include in the response body.
            status: HTTP status code. Defaults to 200.

        Returns:
            A tuple of the JSON-serialisable response body and the HTTP status code.
        """
        ...

    @abstractmethod
    def error(self, message: str, status: int = 400) -> tuple:
        """Build an error HTTP JSON response.

        Args:
            message: Human-readable error description.
            status: HTTP status code. Defaults to 400.

        Returns:
            A tuple of the JSON-serialisable response body and the HTTP status code.
        """
        ...
