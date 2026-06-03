from typing import Any
import requests

from aion.services.base_service import BaseService


class MyIPService(BaseService):
    name = "myip"
    description = "Affiche l'adresse IP publique."
    permissions = ["internet_access"]

    def execute(self, payload: dict[str, Any]) -> str:

        try:
            response = requests.get(
                "https://api.ipify.org?format=json",
                timeout=5
            )

            response.raise_for_status()

            ip = response.json()["ip"]

            return f"Votre IP publique est : {ip}"

        except Exception as e:
            return f"Erreur récupération IP : {e}"