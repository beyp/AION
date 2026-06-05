"""Service demo_hello - demonstration."""
from typing import Any

from aion.services.base_service import BaseService


class DemoHelloService(BaseService):
    """Service de demonstration qui salue l utilisateur."""

    name = "demo_hello"
    description = "Service de demonstration - salue l utilisateur"
    permissions = []
    domain = "demo"

    def execute(self, payload: dict[str, Any]) -> str:
        return "Bonjour ! Je suis AION, votre orchestrateur IA local. 🤖"
