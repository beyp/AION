import platform
import sys
from typing import Any

from aion.services.base_service import BaseService


class SystemInfoService(BaseService):
    name = "system_info"
    description = "Affiche des informations simples sur l'environnement Python."
    permissions = ["read_system_info"]

    def execute(self, payload: dict[str, Any]) -> str:
        return (
            "Informations système :\n"
            f"- OS : {platform.system()} {platform.release()}\n"
            f"- Machine : {platform.machine()}\n"
            f"- Python : {sys.version.split()[0]}"
        )
