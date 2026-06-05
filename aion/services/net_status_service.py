"""Service net_status - statut reseau complet."""
from typing import Any
import getpass
import platform
import socket
import requests

from aion.services.base_service import BaseService


class NetStatusService(BaseService):
    """Affiche les informations reseau completes de la machine."""

    name = "net_status"
    description = "Affiche les informations reseau completes (IP locale, publique, hostname)"
    permissions = ["read_system_info", "internet_access"]
    domain = "net"

    def execute(self, payload: dict[str, Any]) -> str:
        hostname = socket.gethostname()
        username = getpass.getuser()
        os_name = f"{platform.system()} {platform.release()}"
        local_ip = self._get_local_ip()
        public_ip = self._get_public_ip()

        return (
            f"net_status\n"
            f"  Machine   : {hostname}\n"
            f"  User      : {username}\n"
            f"  OS        : {os_name}\n"
            f"  IP locale : {local_ip}\n"
            f"  IP public : {public_ip}"
        )

    def _get_local_ip(self) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "indisponible"

    def _get_public_ip(self) -> str:
        try:
            r = requests.get("https://api.ipify.org?format=json", timeout=5)
            r.raise_for_status()
            return r.json().get("ip", "indisponible")
        except Exception:
            return "indisponible"
