"""Service net_ping - test de connectivite reseau."""
from typing import Any
import subprocess
import platform

from aion.services.base_service import BaseService


class NetPingService(BaseService):
    """Teste la connectivite vers un hote cible."""

    name = "net_ping"
    description = "Teste la connectivite reseau vers un hote (defaut: 8.8.8.8)"
    permissions = ["network"]
    domain = "net"

    def execute(self, payload: dict[str, Any]) -> str:
        host = payload.get("host", "8.8.8.8")
        count = "-n" if platform.system().lower() == "windows" else "-c"
        try:
            result = subprocess.run(
                ["ping", count, "1", host],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return f"net_ping : {host} -> OK ✅"
            return f"net_ping : {host} -> UNREACHABLE ❌"
        except subprocess.TimeoutExpired:
            return f"net_ping : {host} -> TIMEOUT ❌"
        except Exception as exc:
            return f"net_ping : erreur -> {exc}"
