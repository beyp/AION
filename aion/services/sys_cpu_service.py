"""Service sys_cpu - monitoring CPU et RAM."""
from typing import Any
import psutil

from aion.services.base_service import BaseService


class SysCpuService(BaseService):
    """Retourne l utilisation CPU et RAM de la machine."""

    name = "sys_cpu"
    description = "Monitore l utilisation CPU et RAM de la machine"
    permissions = []
    domain = "sys"

    def execute(self, payload: dict[str, Any]) -> str:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        ram_used = ram.used / (1024 ** 3)
        ram_total = ram.total / (1024 ** 3)

        return (
            f"sys_cpu\n"
            f"  CPU : {cpu:.1f}%\n"
            f"  RAM : {ram_used:.1f} / {ram_total:.1f} GB ({ram.percent:.1f}%)"
        )
