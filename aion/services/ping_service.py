from typing import Any

from aion.services.base_service import BaseService


class PingService(BaseService):
    name = "ping"
    description = "Service de test pour vérifier le chargement automatique."
    permissions = []

    def execute(self, payload: dict[str, Any]) -> str:
        return "pong"