"""Service d uptime systeme."""
from datetime import datetime, timezone
from typing import Any

import psutil

from aion.services.base_service import BaseService


class UptimeService(BaseService):
    """Retourne le temps de fonctionnement de la machine depuis le dernier demarrage."""

    name = "uptime"
    description = "Affiche le temps de fonctionnement de la machine"
    permissions = []

    def execute(self, payload: dict[str, Any]) -> str:
        boot_time = psutil.boot_time()
        boot_dt = datetime.fromtimestamp(boot_time)
        now = datetime.now()
        delta = now - boot_dt

        total_seconds = int(delta.total_seconds())
        days = delta.days
        hours, remainder = divmod(total_seconds % (24 * 3600), 3600)
        minutes, seconds = divmod(remainder, 60)

        return (
            f"Uptime\n"
            f"  Demarrage : {boot_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"  Uptime    : {days}j {hours:02d}h {minutes:02d}m {seconds:02d}s"
        )
