"""Service sys_disk - monitoring des disques."""
from typing import Any
import psutil

from aion.services.base_service import BaseService


class SysDiskService(BaseService):
    """Retourne l etat de toutes les partitions disque."""

    name = "sys_disk"
    description = "Monitore toutes les partitions disque (alerte a 85%)"
    permissions = []
    domain = "sys"

    def execute(self, payload: dict[str, Any]) -> str:
        lines = ["sys_disk"]
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                used_gb = usage.used / (1024 ** 3)
                total_gb = usage.total / (1024 ** 3)
                free_gb = usage.free / (1024 ** 3)
                alert = " ⚠️ ALERTE" if usage.percent >= 85 else ""
                lines.append(
                    f"  {partition.device}\n"
                    f"    Utilise : {used_gb:.1f} / {total_gb:.1f} GB ({usage.percent:.1f}%){alert}\n"
                    f"    Libre   : {free_gb:.1f} GB"
                )
            except PermissionError:
                lines.append(f"  {partition.device} : acces refuse")
        return "\n".join(lines)
