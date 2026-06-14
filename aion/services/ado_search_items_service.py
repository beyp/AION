"""Service ado_search_items - recherche des work items Azure DevOps."""
import base64
import os
from typing import Any

import requests

from aion.services.base_service import BaseService

ADO_ORG      = os.getenv("ADO_ORG", "Premiertech")
ADO_BASE_URL = f"https://dev.azure.com/{ADO_ORG}"

# Icones Azure DevOps par type de work item
TYPE_ICONS = {
    "Bug":        "[Bug]",
    "Task":       "[Task]",
    "User Story": "[Story]",
    "Feature":    "[Feature]",
    "Epic":       "[Epic]",
    "Issue":      "[Issue]",
}

# Couleurs terminal par statut
STATE_COLORS = {
    "Done":         "green",
    "Closed":       "green",
    "In Progress":  "yellow",
    "Active":       "yellow",
    "In Review":    "yellow",
    "New":          "blue",
    "ToDo":         "blue",
    "In Analysis":  "blue",
    "On hold":      "orange",
    "Removed":      "red",
}


class AdoSearchItemsService(BaseService):
    """
    Recherche des work items Azure DevOps.

    Payload :
        project         : str  - Projet (defaut: PTG - TMM D2)
        state           : str  - Filtrer par etat (optionnel)
        type            : str  - Filtrer par type (optionnel)
        assigned        : str  - Filtrer par assignee (@me pour soi)
        title_contains  : str  - Recherche dans le titre
        limit           : int  - Nombre max (defaut: 10)
    """

    name        = "ado_search_items"
    description = "Recherche des work items Azure DevOps (par projet, etat, type)"
    permissions = ["network", "azure_devops"]
    domain      = "ado"

    def execute(self, payload: dict[str, Any]) -> str:
        pat = self._get_pat()
        if not pat:
            return "ado_search_items : PAT non configure."

        project         = payload.get("project", "PTG - TMM D2")
        state           = payload.get("state", "")
        wi_type         = payload.get("type", "")
        assigned        = payload.get("assigned", "")
        title_contains  = payload.get("title_contains", "")
        limit           = int(payload.get("limit", 10))

        token = base64.b64encode(f":{pat}".encode()).decode()
        headers = {
            "Authorization": f"Basic {token}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

        # Construire WIQL
        conditions = [f"[System.TeamProject] = '{project}'"]
        if state:          conditions.append(f"[System.State] = '{state}'")
        if wi_type:        conditions.append(f"[System.WorkItemType] = '{wi_type}'")
        if title_contains: conditions.append(f"[System.Title] contains '{title_contains}'")
        if assigned == "@me":
            conditions.append("[System.AssignedTo] = @Me")
        elif assigned:
            conditions.append(f"[System.AssignedTo] contains '{assigned}'")

        where_clause = " AND ".join(conditions)
        wiql = {
            "query": (
                "SELECT [System.Id],[System.Title],[System.WorkItemType],"
                "[System.State],[System.AssignedTo] "
                f"FROM WorkItems WHERE {where_clause} "
                "ORDER BY [System.ChangedDate] DESC"
            )
        }

        try:
            proj_encoded = requests.utils.quote(project)
            r = requests.post(
                f"{ADO_BASE_URL}/{proj_encoded}/_apis/wit/wiql"
                f"?$top={limit}&api-version=7.1",
                headers=headers, json=wiql, timeout=10,
            )
            if r.status_code != 200:
                return f"ado_search_items : HTTP {r.status_code} : {r.text[:200]}"

            items = r.json().get("workItems", [])
            if not items:
                filter_desc = f"Projet={project}"
                if state:          filter_desc += f" | Etat={state}"
                if wi_type:        filter_desc += f" | Type={wi_type}"
                if title_contains: filter_desc += f" | Titre contient={title_contains}"
                return f"ado_search_items : aucun item trouve\n  Filtre : {filter_desc}"

            # Recuperer les details
            ids     = [str(i["id"]) for i in items[:limit]]
            ids_str = ",".join(ids)
            r2 = requests.get(
                f"{ADO_BASE_URL}/_apis/wit/workitems"
                f"?ids={ids_str}"
                f"&fields=System.Id,System.Title,System.WorkItemType,"
                f"System.State,System.AssignedTo,System.IterationPath"
                f"&api-version=7.1",
                headers=headers, timeout=10,
            )
            if r2.status_code != 200:
                return f"ado_search_items : erreur details HTTP {r2.status_code}"

            detail_items = r2.json().get("value", [])

            # En-tete
            filter_desc = f"Projet={project}"
            if state:          filter_desc += f" | Etat={state}"
            if wi_type:        filter_desc += f" | Type={wi_type}"
            if title_contains: filter_desc += f" | Titre={title_contains}"
            if assigned:       filter_desc += f" | Assigne={assigned}"

            lines = [
                f"ado_search_items : {len(detail_items)} item(s)",
                f"  Filtre  : {filter_desc}",
                f"  {'-' * 68}",
                f"  {'Type':<10} {'ID':<9} {'Statut':<16} {'Titre'}",
                f"  {'-' * 68}",
            ]

            for item in detail_items:
                fields      = item.get("fields", {})
                wi_id       = item["id"]
                title       = fields.get("System.Title", "")[:52]
                wi_state    = fields.get("System.State", "")
                wi_t        = fields.get("System.WorkItemType", "")
                assigned_to = fields.get("System.AssignedTo", {})
                assignee    = (
                    assigned_to.get("displayName", "")[:15]
                    if isinstance(assigned_to, dict) else ""
                )
                type_label = TYPE_ICONS.get(wi_t, f"[{wi_t[:6]}]")

                line = (
                    f"  ITEM:{wi_id}|{wi_t}|{wi_state}|"
                    f"  {type_label:<10} #{wi_id:<8} [{wi_state:<14}] {title}"
                )
                if assignee:
                    line += f"  -> {assignee}"
                lines.append(line)

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
