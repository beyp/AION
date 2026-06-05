"""Service net_myip - adresse IP publique."""
from typing import Any
import requests

from aion.services.base_service import BaseService


class NetMyipService(BaseService):
    """Retourne l adresse IP publique de la machine."""

    name = "net_myip"
    description = "Affiche l adresse IP publique de la machine"
    permissions = ["internet_access"]
    domain = "net"

    def execute(self, payload: dict[str, Any]) -> str:
        try:
            response = requests.get("https://api.ipify.org?format=json", timeout=5)
            response.raise_for_status()
            ip = response.json()["ip"]
            return f"net_myip : IP publique = {ip}"
        except Exception as exc:
            return f"net_myip : erreur -> {exc}"
