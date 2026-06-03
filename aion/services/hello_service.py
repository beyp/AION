from typing import Any

from aion.services.base_service import BaseService


class HelloService(BaseService):
    name = "hello"
    description = "Service de démonstration qui salue l'utilisateur."
    permissions = []

    def execute(self, payload: dict[str, Any]) -> str:
        return "Bonjour Pascal. Je suis AION, ton orchestrateur IA local."
