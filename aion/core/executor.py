from typing import Any

from aion.core.registry import ServiceRegistry


class ServiceExecutor:
    """Executes registered services."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def execute(self, service_name: str, payload: dict[str, Any] | None = None) -> str:
        service = self.registry.get(service_name)

        if service is None:
            return f"Service inconnu : {service_name}"

        return service.execute(payload or {})
