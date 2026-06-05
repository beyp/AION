"""Service sys_info - informations systeme."""
import platform
import sys
from typing import Any

from aion.services.base_service import BaseService


class SysInfoService(BaseService):
    """Affiche les informations systeme et Python."""

    name = "sys_info"
    description = "Affiche les informations systeme (OS, machine, Python)"
    permissions = ["read_system_info"]
    domain = "sys"

    def execute(self, payload: dict[str, Any]) -> str:
        return (
            f"sys_info\n"
            f"  OS      : {platform.system()} {platform.release()}\n"
            f"  Machine : {platform.machine()}\n"
            f"  Python  : {sys.version.split()[0]}"
        )
