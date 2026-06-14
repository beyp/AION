"""Service ado_search_items - recherche des work items Azure DevOps."""
import base64
import os
from typing import Any

import requests

from aion.services.base_service import BaseService

ADO_ORG      = os.getenv("ADO_ORG", "Premiertech")
ADO_BASE_URL = f"https://dev.azure.com/{ADO_ORG}"


class AdoSearchItemsService(BaseService):
    """
    Recherche des work items Azure DevOps.

    Payload :
        project   : str  - Projet (defaut: PTG - TMM D2)
        state     : str  - Filtrer par etat (optionnel)
        type      : str  - Filtrer par type (optionnel)
        assigned  : str  - Filtrer par assignee (optionnel, "@me" pour soi)
        limit     : int  - Nombre max de resultats (defaut: 10)
    """

    name        = "ado_search_items"
    description = "Recherche des work items Azure DevOps (par projet, etat, type)"
    permissions = ["network", "azure_devops"]
    domain      = "ado"

    def execute(self, payload: dict[str, Any]) -> str:
        pat = self._get_pat()
        if not pat:
            return "ado_search_items : PAT non configure."

        project  = payload.get("project", "PTG - TMM D2")
        state    = payload.get("state", "")
        wi_type  = payload.get("type", "")
        assigned = payload.get("assigned", "")
        limit    = int(payload.get("limit", 10))

        token = base64.b64encode(f":{pat}".encode()).decode()
        headers = {
            "Authorization": f"Basic {token}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

        # Construire la requete WIQL
        conditions = [f"[System.TeamProject] = \'{project}\'"]
        if state:
            conditions.append(f"[System.State] = \'{state}\'")
        if wi_type:
            conditions.append(f"[System.WorkItemType] = \'{wi_type}\'")
        if assigned:
            if assigned == "@me":
                conditions.append("[System.AssignedTo] = @Me")
            else:
                conditions.append(f"[System.AssignedTo] contains \'{assigned}\'")

        where_clause = " AND ".join(conditions)
        wiql = {
            "query": (
                "SELECT [System.Id], [System.Title], [System.WorkItemType], "
                "[System.State], [System.AssignedTo] "
                f"FROM WorkItems WHERE {where_clause} "
                "ORDER BY [System.ChangedDate] DESC"
            )
        }

        try:
            proj_encoded = requests.utils.quote(project)
            r = requests.post(
                f"{ADO_BASE_URL}/{proj_encoded}/_apis/wit/wiql"
                f"?$top={limit}&api-version=7.1",
                headers=headers,
                json=wiql,
                timeout=10,
            )
            if r.status_code != 200:
                return f"ado_search_items : HTTP {r.status_code} : {r.text[:200]}"

            items = r.json().get("workItems", [])
            if not items:
                return (
                    f"ado_search_items : aucun item trouve\n"
                    f"  Projet : {project}"
                    + (f"\n  Etat   : {state}" if state else "")
                    + (f"\n  Type   : {wi_type}" if wi_type else "")
                )

            # Recuperer les details
            ids = [str(i["id"]) for i in items[:limit]]
            ids_str = ",".join(ids)
            r2 = requests.get(
                f"{ADO_BASE_URL}/_apis/wit/workitems"
                f"?ids={ids_str}&fields=System.Id,System.Title,"
                f"System.WorkItemType,System.State,System.AssignedTo"
                f"&api-version=7.1",
                headers=headers,
                timeout=10,
            )

            if r2.status_code != 200:
                return f"ado_search_items : erreur details HTTP {r2.status_code}"

            detail_items = r2.json().get("value", [])
            filter_desc = f"Projet={project}"
            if state:   filter_desc += f" | Etat={state}"
            if wi_type: filter_desc += f" | Type={wi_type}"

            lines = [
                f"ado_search_items : {len(detail_items)} item(s)",
                f"  Filtre : {filter_desc}",
                f"  {'─' * 50}",
            ]

            type_icons = {
                "Bug": "🔴", "Task": "✅", "User Story": "📖",
                "Feature": "⭐", "Epic": "🚀",
            }

            for item in detail_items:
                fields = item.get("fields", {})
                wi_id    = item["id"]
                title    = fields.get("System.Title", "")[:60]
                wi_state = fields.get("System.State", "")
                wi_t     = fields.get("System.WorkItemType", "")
                assigned_to = fields.get("System.AssignedTo", {})
                assigned_name = (
                    assigned_to.get("displayName", "")[:20]
                    if isinstance(assigned_to, dict) else ""
                )
                icon = type_icons.get(wi_t, "📌")
                lines.append(
                    f"  {icon} #{wi_id:<8} [{wi_state:<12}] {title}"
                    + (f" → {assigned_name}" if assigned_name else "")
                )

            return "\n".join(lines)

        except requests.exceptions.ConnectionError:
            return "ado_search_items : impossible de joindre Azure DevOps."
        except Exception as exc:
            return f"ado_search_items : erreur -> {exc}"

    def _get_pat(self) -> str:
        pat = os.getenv("ADO_PAT", "")
        if pat:
            return pat
        try:
            from aion.memory.memory_manager import MemoryManager
            pat = MemoryManager().recall("ado_pat") or ""
        except Exception:
            pass
        return pat
