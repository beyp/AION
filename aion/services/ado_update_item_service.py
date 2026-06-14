"""Service ado_update_item - met a jour le statut d un work item Azure DevOps."""
import base64
import os
from typing import Any

import requests

from aion.services.base_service import BaseService

# ── Configuration ─────────────────────────────────────────────────────────────
ADO_ORG      = os.getenv("ADO_ORG", "Premiertech")
ADO_BASE_URL = f"https://dev.azure.com/{ADO_ORG}"

# Etats valides par type de work item
VALID_STATES: dict[str, list[str]] = {
    "Bug":        ["New", "Active", "Resolved", "Closed"],
    "Task":       ["ToDo", "In Progress", "On hold", "In Review", "Done", "Removed"],
    "User Story": ["New", "In Analysis", "In Progress", "In Review", "Done", "Removed"],
    "Feature":    ["ToDo", "In Progress", "On hold", "In Review", "Done", "Removed"],
    "Epic":       ["New", "In Analysis", "In Progress", "In Review", "On hold", "Done", "Removed"],
}

# Projets connus
KNOWN_PROJECTS = ["PTG - TMM D2", "PTG - TMM"]


class AdoUpdateItemService(BaseService):
    """
    Met a jour le statut d un work item Azure DevOps.

    Payload attendu :
        item_id  : int  - ID du work item (obligatoire)
        state    : str  - Nouveau statut (obligatoire)
        project  : str  - Nom du projet (defaut: PTG - TMM D2)
        comment  : str  - Commentaire optionnel

    Etats disponibles par type :
        Bug        : New, Active, Resolved, Closed
        Task       : ToDo, In Progress, On hold, In Review, Done, Removed
        User Story : New, In Analysis, In Progress, In Review, Done, Removed
        Feature    : ToDo, In Progress, On hold, In Review, Done, Removed
        Epic       : New, In Analysis, In Progress, In Review, On hold, Done, Removed
    """

    name        = "ado_update_item"
    description = "Met a jour le statut d un work item Azure DevOps"
    permissions = ["network", "azure_devops"]
    domain      = "ado"

    def execute(self, payload: dict[str, Any]) -> str:
        # ── Recuperer le PAT ──────────────────────────────────────────────────
        pat = self._get_pat()
        if not pat:
            return (
                "ado_update_item : PAT non configure.\n"
                "  Ajoute dans .env : ADO_PAT=ton_token\n"
                "  Ou memorise : remember ado_pat=ton_token"
            )

        # ── Valider les parametres ────────────────────────────────────────────
        item_id = payload.get("item_id")
        state   = payload.get("state", "").strip()
        project = payload.get("project", "PTG - TMM D2").strip()
        comment = payload.get("comment", "").strip()

        if not item_id:
            return (
                "ado_update_item : item_id obligatoire.\n"
                "  Exemple : run ado_update_item {item_id: 12345, state: \"In Progress\"}"
            )

        if not state:
            return (
                "ado_update_item : state obligatoire.\n"
                "  Etats disponibles selon le type :\n"
                + "\n".join(f"  {k}: {', '.join(v)}" for k, v in VALID_STATES.items())
            )

        headers = self._get_headers(pat)

        # ── Recuperer le work item actuel ─────────────────────────────────────
        current = self._get_work_item(item_id, headers)
        if "error" in current:
            return f"ado_update_item : impossible de recuperer l item #{item_id}\n  {current['error']}"

        wi_type     = current.get("type", "")
        wi_title    = current.get("title", "")
        wi_state    = current.get("state", "")
        wi_project  = current.get("project", project)

        # ── Valider l etat pour ce type ───────────────────────────────────────
        valid = VALID_STATES.get(wi_type, [])
        if valid and state not in valid:
            return (
                f"ado_update_item : etat invalide pour {wi_type}.\n"
                f"  Etats valides : {', '.join(valid)}\n"
                f"  Etat demande  : {state}"
            )

        if wi_state == state:
            return (
                f"ado_update_item : item #{item_id} est deja en etat \"{state}\".\n"
                f"  Titre : {wi_title}\n"
                f"  Type  : {wi_type}"
            )

        # ── Mettre a jour le statut ───────────────────────────────────────────
        result = self._update_state(item_id, state, comment, headers)
        if "error" in result:
            return f"ado_update_item : echec de la mise a jour.\n  {result['error']}"

        return (
            f"ado_update_item : ✅ Item #{item_id} mis a jour\n"
            f"  Titre   : {wi_title}\n"
            f"  Type    : {wi_type}\n"
            f"  Projet  : {wi_project}\n"
            f"  Statut  : {wi_state} -> {state}"
            + (f"\n  Comment : {comment}" if comment else "")
        )

    def _get_pat(self) -> str:
        """Recupere le PAT depuis .env ou la memoire AION."""
        # 1. Variable d environnement
        pat = os.getenv("ADO_PAT", "")
        if pat:
            return pat
        # 2. Memoire AION
        try:
            from aion.memory.memory_manager import MemoryManager
            pat = MemoryManager().recall("ado_pat") or ""
        except Exception:
            pass
        return pat

    def _get_headers(self, pat: str) -> dict:
        token = base64.b64encode(f":{pat}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type":  "application/json-patch+json",
            "Accept":        "application/json",
        }

    def _get_work_item(self, item_id: int, headers: dict) -> dict:
        """Recupere les informations d un work item."""
        try:
            r = requests.get(
                f"{ADO_BASE_URL}/_apis/wit/workitems/{item_id}?api-version=7.1",
                headers=headers,
                timeout=10,
            )
            if r.status_code == 404:
                return {"error": f"Work item #{item_id} introuvable."}
            if r.status_code == 401:
                return {"error": "PAT invalide ou expire."}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code} : {r.text[:200]}"}

            fields = r.json().get("fields", {})
            return {
                "type":    fields.get("System.WorkItemType", ""),
                "title":   fields.get("System.Title", ""),
                "state":   fields.get("System.State", ""),
                "project": fields.get("System.TeamProject", ""),
            }
        except requests.exceptions.ConnectionError:
            return {"error": "Impossible de joindre Azure DevOps. Verifie ta connexion."}
        except Exception as exc:
            return {"error": str(exc)}

    def _update_state(
        self,
        item_id: int,
        state: str,
        comment: str,
        headers: dict,
    ) -> dict:
        """Met a jour le statut et ajoute un commentaire optionnel."""
        patch = [
            {
                "op":    "replace",
                "path":  "/fields/System.State",
                "value": state,
            }
        ]

        if comment:
            patch.append({
                "op":    "add",
                "path":  "/fields/System.History",
                "value": f"[AION] {comment}",
            })

        try:
            r = requests.patch(
                f"{ADO_BASE_URL}/_apis/wit/workitems/{item_id}?api-version=7.1",
                headers=headers,
                json=patch,
                timeout=10,
            )
            if r.status_code in (200, 201):
                return {"ok": True}
            return {"error": f"HTTP {r.status_code} : {r.text[:300]}"}
        except Exception as exc:
            return {"error": str(exc)}
