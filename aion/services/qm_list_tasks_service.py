"""Service qm_list_tasks - liste les taches QuickMind."""
from typing import Any
import requests

from aion.services.base_service import BaseService

QUICKMIND_URL = "http://localhost:8765"


class QmListTasksService(BaseService):
    """Liste les taches en cours dans QuickMind."""

    name = "qm_list_tasks"
    description = "Liste les taches actives de QuickMind"
    permissions = ["network"]
    domain = "qm"

    def execute(self, payload: dict[str, Any]) -> str:
        priority = payload.get("priority", None)
        status   = payload.get("status", "todo")

        try:
            params = {}
            if priority: params["priority"] = priority
            if status:   params["status"]   = status

            r = requests.get(
                f"{QUICKMIND_URL}/tasks",
                params=params,
                timeout=5,
            )
            r.raise_for_status()
            tasks = r.json()

            if not tasks:
                return "qm_list_tasks : aucune tache trouvee."

            lines = [f"qm_list_tasks : {len(tasks)} tache(s) :"]
            for t in tasks[:10]:  # max 10
                prio = t.get("priority", "?")
                title = t.get("title", "?")
                tid = t.get("id", "?")
                lines.append(f"  #{tid} [{prio}] {title}")

            if len(tasks) > 10:
                lines.append(f"  ... et {len(tasks) - 10} autres")

            return "\n".join(lines)

        except requests.exceptions.ConnectionError:
            return "qm_list_tasks : QuickMind non disponible."
        except Exception as exc:
            return f"qm_list_tasks : erreur -> {exc}"
