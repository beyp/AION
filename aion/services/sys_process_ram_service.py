"""process_ram_monitoring - Monitor the system's RAM usage."""
from typing import Any, Dict
import psutil

from aion.services.base_service import BaseService

class ProcessRAMMonitoringService(BaseService):
    """Monitors the system's RAM usage."""

    name = "sys_process_ram"
    description = "Retrieves and displays information about the system's RAM usage."
    permissions = []
    domain = "sys"

    def execute(self, payload: Dict[str, Any]) -> str:
        try:
            ram = psutil.virtual_memory()
            return f"Sys_process_ram : Total: {ram.total} / Used: {ram.used} / Free: {ram.free}"
        except Exception as e:
            return f"Error: {e}"