"""Service de monitoring CPU, RAM et disque."""
import platform
from typing import Any

import psutil

from aion.services.base_service import BaseService


class CpuMonitorService(BaseService):
    """Retourne l utilisation CPU, RAM et disque de la machine."""

    name = "cpu_monitor"
    description = "Monitore CPU, RAM et disque de la machine locale"
    permissions = []

    def execute(self, payload: dict[str, Any]) -> str:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        ram_used_gb = ram.used / (1024 ** 3)
        ram_total_gb = ram.total / (1024 ** 3)
        disk_used_gb = disk.used / (1024 ** 3)
        disk_total_gb = disk.total / (1024 ** 3)

        return (
            f"CPU Monitor\n"
            f"  CPU       : {cpu:.1f}%\n"
            f"  RAM       : {ram_used_gb:.1f} / {ram_total_gb:.1f} GB ({ram.percent:.1f}%)\n"
            f"  Disque    : {disk_used_gb:.1f} / {disk_total_gb:.1f} GB ({disk.percent:.1f}%)"
        )
