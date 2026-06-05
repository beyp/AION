"""Service sys_uptime - uptime de la machine."""
from datetime import datetime
from typing import Any
import psutil

from aion.services.base_service import BaseService


class SysUptimeService(BaseService):
    """Retourne le temps de fonctionnement de la machine."""

    name = "sys_uptime"
    description = "Affiche le temps de fonctionnement depuis le dernier demarrage"
    permissions = []
    domain = "sys"

    def execute(self, payload: dict[str, Any]) -> str:
        boot_dt = datetime.fromtimestamp(psutil.boot_time())
        delta = datetime.now() - boot_dt
        total_seconds = int(delta.total_seconds())
        days = delta.days
        hours, remainder = divmod(total_seconds % (24 * 3600), 3600)
        minutes, seconds = divmod(remainder, 60)

        return (
            f"sys_uptime\n"
            f"  Demarrage : {boot_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"  Uptime    : {days}j {hours:02d}h {minutes:02d}m {seconds:02d}s"
        )
