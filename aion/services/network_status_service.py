from typing import Any
import getpass
import platform
import socket

import requests

from aion.services.base_service import BaseService


class NetworkStatusService(BaseService):
    name = "network_status"
    description = "Affiche les informations réseau principales de la machine."
    permissions = ["read_system_info", "internet_access"]

    def execute(self, payload: dict[str, Any]) -> str:
        hostname = socket.gethostname()
        username = getpass.getuser()
        os_name = f"{platform.system()} {platform.release()}"

        local_ip = self._get_local_ip()
        public_ip = self._get_public_ip()

        return (
            "AION Network Status\n\n"
            f"Machine : {hostname}\n"
            f"Utilisateur : {username}\n"
            f"OS : {os_name}\n"
            f"IP locale : {local_ip}\n"
            f"IP publique : {public_ip}"
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
            response = requests.get(
                "https://api.ipify.org?format=json",
                timeout=5
            )
            response.raise_for_status()
            return response.json().get("ip", "indisponible")
        except Exception:
            return "indisponible"