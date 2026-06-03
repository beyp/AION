from abc import ABC, abstractmethod
from typing import Any


class BaseService(ABC):
    """Base class for all AION services."""

    name: str = "base"
    description: str = "Base service"
    permissions: list[str] = []

    @abstractmethod
    def execute(self, payload: dict[str, Any]) -> str:
        """Execute the service and return a text response."""
        raise NotImplementedError
