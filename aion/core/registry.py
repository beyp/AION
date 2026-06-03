from aion.services.base_service import BaseService
from aion.services.hello_service import HelloService
from aion.services.system_info_service import SystemInfoService


class ServiceRegistry:
    """Keeps track of all available AION services."""

    def __init__(self) -> None:
        self._services: dict[str, BaseService] = {}

    def register(self, service: BaseService) -> None:
        self._services[service.name] = service

    def register_default_services(self) -> None:
        self.register(HelloService())
        self.register(SystemInfoService())

    def list_services(self) -> list[BaseService]:
        return list(self._services.values())

    def get(self, service_name: str) -> BaseService | None:
        return self._services.get(service_name)
