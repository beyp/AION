"""ServiceExecutor - execute les services enregistres dans AION."""
import logging
from typing import Any

from aion.core.registry import ServiceRegistry

logger = logging.getLogger(__name__)


class ServiceExecutor:
    """Execute les services enregistres avec gestion d erreurs robuste."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def execute(self, service_name: str, payload: dict[str, Any] | None = None) -> str:
        service = self.registry.get(service_name)

        if service is None:
            logger.warning("ServiceExecutor: unknown service '%s'", service_name)
            return f"Service inconnu : {service_name}"

        try:
            result = service.execute(payload or {})
            logger.info("ServiceExecutor: '%s' executed successfully", service_name)
            return result
        except Exception as exc:
            logger.error(
                "ServiceExecutor: '%s' raised an error: %s", service_name, exc
            )
            return f"Erreur lors de l'execution de '{service_name}' : {exc}"
