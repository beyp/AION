"""Service qm_add_task - cree une tache dans QuickMind."""
from typing import Any
import requests

from aion.services.base_service import BaseService

QUICKMIND_URL = "http://localhost:8765"


class QmAddTaskService(BaseService):
    """Cree une nouvelle tache dans QuickMind via l API REST."""

    name = "qm_add_task"
    description = "Cree une tache dans QuickMind (title, priority, category)"
    permissions = ["network"]
    domain = "qm"

    def execute(self, payload: dict[str, Any]) -> str:
        title    = payload.get("title", "Tache AION")
        priority = payload.get("priority", "normal")
        category = payload.get("category", None)

        body: dict[str, Any] = {
            "title":    title,
            "priority": priority,
        }
        if category:
            body["category"] = category

        try:
            r = requests.post(
                f"{QUICKMIND_URL}/task",
                json=body,
                timeout=5,
            )
            r.raise_for_status()
            data = r.json()
            task_id = data.get("id", "?")
            return f"qm_add_task : tache #{task_id} creee -> {title} [{priority}]"
        except requests.exceptions.ConnectionError:
            return "qm_add_task : QuickMind non disponible (http://localhost:8765)"
        except Exception as exc:
            return f"qm_add_task : erreur -> {exc}"
