"""Service ado_get_item - recupere les details d un work item Azure DevOps."""
import base64
import os
from typing import Any

import requests

from aion.services.base_service import BaseService

ADO_ORG      = os.getenv("ADO_ORG", "Premiertech")
ADO_BASE_URL = f"https://dev.azure.com/{ADO_ORG}"


class AdoGetItemService(BaseService):
    """
    Recupere les details d un work item Azure DevOps.

    Payload :
        item_id : int - ID du work item
    """

    name        = "ado_get_item"
    description = "Recupere les details d un work item Azure DevOps par son ID"
    permissions = ["network", "azure_devops"]
    domain      = "ado"

    def execute(self, payload: dict[str, Any]) -> str:
        pat = self._get_pat()
        if not pat:
            return "ado_get_item : PAT non configure. Ajoute ADO_PAT dans .env"

        item_id = payload.get("item_id")
        if not item_id:
            return "ado_get_item : item_id obligatoire."

        token = base64.b64encode(f":{pat}".encode()).decode()
        headers = {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
        }

        try:
            r = requests.get(
                f"{ADO_BASE_URL}/_apis/wit/workitems/{item_id}"
                f"?$expand=relations&api-version=7.1",
                headers=headers,
                timeout=10,
            )
            if r.status_code == 404:
                return f"ado_get_item : work item #{item_id} introuvable."
            if r.status_code == 401:
                return "ado_get_item : PAT invalide ou expire."
            if r.status_code != 200:
                return f"ado_get_item : HTTP {r.status_code}"

            fields = r.json().get("fields", {})
            assigned = fields.get("System.AssignedTo", {})
            assigned_name = (
                assigned.get("displayName", "Non assigne")
                if isinstance(assigned, dict)
                else str(assigned) if assigned else "Non assigne"
            )

            tags = fields.get("System.Tags", "") or ""
            priority = fields.get("Microsoft.VSTS.Common.Priority", "")
            iteration = fields.get("System.IterationPath", "")
            area = fields.get("System.AreaPath", "")
            created = fields.get("System.CreatedDate", "")[:10] if fields.get("System.CreatedDate") else ""
            changed  = fields.get("System.ChangedDate", "")[:10] if fields.get("System.ChangedDate") else ""

            lines = [
                f"ado_get_item : Work Item #{item_id}",
                f"  Titre      : {fields.get('System.Title', '')}",
                f"  Type       : {fields.get('System.WorkItemType', '')}",
                f"  Statut     : {fields.get('System.State', '')}",
                f"  Projet     : {fields.get('System.TeamProject', '')}",
                f"  Assigne a  : {assigned_name}",
            ]
            if priority:
                lines.append(f"  Priorite   : {priority}")
            if iteration:
                lines.append(f"  Iteration  : {iteration}")
            if area:
                lines.append(f"  Zone       : {area}")
            if tags:
                lines.append(f"  Tags       : {tags}")
            if created:
                lines.append(f"  Cree le    : {created}")
            if changed:
                lines.append(f"  Modifie le : {changed}")

            desc = fields.get("System.Description", "") or ""
            if desc:
                import re
                clean = re.sub(r"<[^>]+>", "", desc).strip()[:200]
                if clean:
                    lines.append(f"  Description: {clean}{'...' if len(clean) == 200 else ''}")

            return "\n".join(lines)

        except requests.exceptions.ConnectionError:
            return "ado_get_item : impossible de joindre Azure DevOps."
        except Exception as exc:
            return f"ado_get_item : erreur -> {exc}"

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
