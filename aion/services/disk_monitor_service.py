"""Service de monitoring detaille des disques."""
from typing import Any

import psutil

from aion.services.base_service import BaseService


class DiskMonitorService(BaseService):
    """Retourne l etat detaille de toutes les partitions disque."""

    name = "disk_monitor"
    description = "Monitore toutes les partitions disque de la machine"
    permissions = []

    def execute(self, payload: dict[str, Any]) -> str:
        lines = ["Disk Monitor"]
        partitions = psutil.disk_partitions()

        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                used_gb = usage.used / (1024 ** 3)
                total_gb = usage.total / (1024 ** 3)
                free_gb = usage.free / (1024 ** 3)
                alert = " ⚠️ ALERTE" if usage.percent >= 85 else ""
                lines.append(
                    f"  {partition.device} ({partition.mountpoint})\n"
                    f"    Utilise : {used_gb:.1f} / {total_gb:.1f} GB "
                    f"({usage.percent:.1f}%){alert}\n"
                    f"    Libre   : {free_gb:.1f} GB"
                )
            except PermissionError:
                lines.append(f"  {partition.device} : acces refuse")

        return "\n".join(lines)
