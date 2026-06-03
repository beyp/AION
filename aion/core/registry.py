import importlib
import inspect
import pkgutil

import aion.services
from aion.services.base_service import BaseService


class ServiceRegistry:
    """Keeps track of all available AION services."""

    def __init__(self) -> None:
        self._services: dict[str, BaseService] = {}

    def register(self, service: BaseService) -> None:
        if service.name in self._services:
            raise ValueError(f"Service already registered: {service.name}")

        self._services[service.name] = service

    def discover_services(self) -> None:
        """Auto-discover services from the aion.services package."""

        package = aion.services

        for _, module_name, is_package in pkgutil.iter_modules(package.__path__):
            if is_package:
                continue

            if not module_name.endswith("_service"):
                continue

            if module_name == "base_service":
                continue

            module = importlib.import_module(f"{package.__name__}.{module_name}")

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj is BaseService:
                    continue

                if not issubclass(obj, BaseService):
                    continue

                service_instance = obj()
                self.register(service_instance)

    def list_services(self) -> list[BaseService]:
        return list(self._services.values())

    def get(self, service_name: str) -> BaseService | None:
        return self._services.get(service_name)

    def count(self) -> int:
        return len(self._services)