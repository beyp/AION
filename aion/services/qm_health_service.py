"""Service qm_health - verifie que QuickMind tourne."""
from typing import Any
import requests

from aion.services.base_service import BaseService

QUICKMIND_URL = "http://localhost:8765"


class QmHealthService(BaseService):
    """Verifie que QuickMind est en ligne."""

    name = "qm_health"
    description = "Verifie que QuickMind est en cours d execution"
    permissions = ["network"]
    domain = "qm"

    def execute(self, payload: dict[str, Any]) -> str:
        try:
            r = requests.get(f"{QUICKMIND_URL}/tasks", timeout=3)
            if r.status_code == 200:
                return "qm_health : QuickMind en ligne ✅ (http://localhost:8765)"
            return f"qm_health : QuickMind repond mais status {r.status_code} ⚠️"
        except requests.exceptions.ConnectionError:
            return "qm_health : QuickMind HORS LIGNE ❌"
        except Exception as exc:
            return f"qm_health : erreur -> {exc}"
