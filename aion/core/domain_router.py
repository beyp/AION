"""
DomainRouter - route les commandes naturelles vers les services AION.

Usage dans app.py :
    result = self.domain_router.dispatch(command)
    if result is not None:
        return result
"""
import logging
import webbrowser
from typing import TYPE_CHECKING

from aion.core.command_parser import (
    ParsedCommand, parse_command, get_domain_help, DOMAIN_HELP
)

if TYPE_CHECKING:
    from aion.core.executor import ServiceExecutor
    from aion.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

# Domaines reconnus par le router
ROUTED_DOMAINS = {"ado", "net", "sys", "fs", "qm", "docker"}

# Projet ADO par defaut (modifiable par "ado project <nom>")
_ado_default_project = "PTG - TMM D2"


class DomainRouter:
    """
    Route les commandes naturelles (domaine + action + args)
    vers les services AION correspondants.
    """

    def __init__(
        self,
        executor: "ServiceExecutor",
        memory:   "MemoryManager",
    ) -> None:
        self._executor = executor
        self._memory   = memory

    def can_handle(self, command: str) -> bool:
        """Verifie si la commande commence par un domaine connu."""
        first = command.strip().split()[0].lower() if command.strip() else ""
        return first in ROUTED_DOMAINS

    def dispatch(self, command: str) -> str | None:
        """
        Tente de traiter la commande.
        Retourne None si le domaine n est pas reconnu.
        """
        parsed = parse_command(command)
        if parsed is None:
            return None
        if parsed.domain not in ROUTED_DOMAINS:
            return None

        logger.info("DomainRouter: %s %s %s %s",
                    parsed.domain, parsed.action, parsed.args, parsed.params)

        # Aide contextuelle : domaine ? ou domaine action ?
        if parsed.action in ("?", "help"):
            return get_domain_help(parsed.domain)
        if len(parsed.args) == 1 and parsed.args[0] == "?":
            return get_domain_help(parsed.domain, parsed.action)

        router_fn = {
            "ado":    self._ado,
            "net":    self._net,
            "sys":    self._sys,
            "fs":     self._fs,
            "qm":     self._qm,
            "docker": self._docker,
        }.get(parsed.domain)

        if router_fn is None:
            return None

        return router_fn(parsed)

    # ── ADO ───────────────────────────────────────────────────────────────────

    def _ado(self, p: ParsedCommand) -> str:
        global _ado_default_project

        action = p.action

        # ado ? ou ado help
        if not action:
            return get_domain_help("ado")

        # ado get item <id>  ou  ado get <id>
        if action == "get":
            item_id = self._find_id(p)
            if not item_id:
                return get_domain_help("ado", "get")
            return self._executor.execute("ado_get_item", {"item_id": item_id})

        # ado status change <id> <state> [--comment "..."]
        if action == "status":
            sub = p.args[0].lower() if p.args else ""
            if sub == "change" and len(p.args) >= 3:
                item_id = self._to_int(p.args[1])
                state   = p.args[2]
                comment = p.params.get("comment", "")
                if not item_id:
                    return "Format : ado status change <id> <etat>"
                payload = {
                    "item_id": item_id,
                    "state":   state,
                    "project": p.params.get("project", _ado_default_project),
                }
                if comment:
                    payload["comment"] = comment
                return self._executor.execute("ado_update_item", payload)
            # ado status <id> <state> (raccourci)
            if len(p.args) >= 2 and p.args[0].isdigit():
                item_id = int(p.args[0])
                state   = p.args[1]
                comment = p.params.get("comment", "")
                payload = {
                    "item_id": item_id,
                    "state":   state,
                    "project": p.params.get("project", _ado_default_project),
                }
                if comment:
                    payload["comment"] = comment
                return self._executor.execute("ado_update_item", payload)
            return get_domain_help("ado", "status")

        # ado list [--state ...] [--type ...] [--project ...]
        if action == "list":
            payload = {
                "project": p.params.get("project", _ado_default_project),
                "limit":   int(p.params.get("limit", 10)),
            }
            if "state" in p.params:  payload["state"]    = p.params["state"]
            if "type"  in p.params:  payload["type"]     = p.params["type"]
            if p.args:               payload["state"]    = " ".join(p.args)
            return self._executor.execute("ado_search_items", payload)

        # ado my [--state ...]
        if action == "my":
            payload = {
                "project":  p.params.get("project", _ado_default_project),
                "assigned": "@me",
                "limit":    int(p.params.get("limit", 15)),
            }
            if "state" in p.params: payload["state"] = p.params["state"]
            return self._executor.execute("ado_search_items", payload)

        # ado search <texte>
        if action == "search":
            if not p.args:
                return get_domain_help("ado", "search")
            # Recherche par titre via WIQL
            payload = {
                "project": p.params.get("project", _ado_default_project),
                "title_contains": " ".join(p.args),
                "limit": int(p.params.get("limit", 10)),
            }
            return self._executor.execute("ado_search_items", payload)

        # ado open <id>
        if action == "open":
            item_id = self._find_id(p)
            if not item_id:
                return "Format : ado open <id>"
            proj = _ado_default_project.replace(" ", "%20")
            url  = f"https://dev.azure.com/Premiertech/{proj}/_workitems/edit/{item_id}"
            webbrowser.open(url)
            return f"ado open : navigateur ouvert -> {url}"

        # ado project [<nom>]
        if action == "project":
            if p.args:
                _ado_default_project = " ".join(p.args)
                return f"ado project : projet par defaut -> {_ado_default_project}"
            return f"ado project : projet actif = {_ado_default_project}"

        return get_domain_help("ado")

    # ── NET ───────────────────────────────────────────────────────────────────

    def _net(self, p: ParsedCommand) -> str:
        if not p.action:
            return get_domain_help("net")

        if p.action == "status":
            return self._executor.execute("net_status", {})

        if p.action == "myip":
            return self._executor.execute("net_myip", {})

        if p.action == "ping":
            host = (
                p.params.get("host")
                or (p.args[0] if p.args else "8.8.8.8")
            )
            return self._executor.execute("net_ping", {"host": host})

        return get_domain_help("net")

    # ── SYS ───────────────────────────────────────────────────────────────────

    def _sys(self, p: ParsedCommand) -> str:
        mapping = {
            "cpu":    "sys_cpu",
            "disk":   "sys_disk",
            "uptime": "sys_uptime",
            "info":   "sys_info",
        }
        if not p.action:
            return get_domain_help("sys")
        svc = mapping.get(p.action)
        if svc:
            return self._executor.execute(svc, {})
        return get_domain_help("sys")

    # ── FS ────────────────────────────────────────────────────────────────────

    def _fs(self, p: ParsedCommand) -> str:
        if not p.action:
            return get_domain_help("fs")

        if p.action == "search":
            if not p.args:
                return get_domain_help("fs", "search")

            # Determiner mots-cles et repertoire
            # fs search <mot1> [mot2...] [--path <dir>] [--key <memkey>]
            # fs search <mot1> [mot2...] <chemin_si_commence_par_lettre:>
            keywords_parts = []
            directory      = p.params.get("path", "")
            memory_key     = p.params.get("key", "search_dir")

            for arg in p.args:
                # Detecter un chemin Windows (C:\ ou \)
                if len(arg) > 2 and arg[1] == ":" or arg.startswith("\\"):
                    directory = arg
                else:
                    keywords_parts.append(arg)

            keywords = " ".join(keywords_parts)
            if not keywords:
                return get_domain_help("fs", "search")

            payload = {"keywords": keywords, "memory_key": memory_key}
            if directory:
                payload["directory"] = directory

            return self._executor.execute("fs_search", payload)

        return get_domain_help("fs")

    # ── QM ────────────────────────────────────────────────────────────────────

    def _qm(self, p: ParsedCommand) -> str:
        if not p.action:
            return get_domain_help("qm")

        # qm add <titre> [--priority ...] [--category ...] [--reminder ...]
        if p.action == "add":
            if not p.args and "title" not in p.params:
                return get_domain_help("qm", "add")
            title    = p.params.get("title") or " ".join(p.args)
            priority = p.params.get("priority", "normal")
            category = p.params.get("category", "")
            # Normaliser priorite
            prio_map = {"u": "urgent", "h": "high", "n": "normal", "l": "low"}
            priority = prio_map.get(priority[0].lower(), priority) if priority else "normal"
            payload  = {"title": title, "priority": priority}
            if category:
                payload["category"] = category
            return self._executor.execute("qm_add_task", payload)

        # qm list [--priority ...] [--status ...]
        if p.action == "list":
            payload = {}
            if "priority" in p.params: payload["priority"] = p.params["priority"]
            if "status"   in p.params: payload["status"]   = p.params["status"]
            return self._executor.execute("qm_list_tasks", payload)

        # qm done <id>
        if p.action == "done":
            item_id = self._find_id(p)
            if not item_id:
                return get_domain_help("qm", "done")
            import requests as req
            try:
                r = req.post(
                    f"http://localhost:8765/task/{item_id}/done",
                    timeout=5,
                )
                r.raise_for_status()
                return f"qm done : tache #{item_id} marquee Done ✅"
            except Exception as exc:
                return f"qm done : erreur -> {exc}"

        # qm health
        if p.action == "health":
            return self._executor.execute("qm_health", {})

        return get_domain_help("qm")

    # ── DOCKER ────────────────────────────────────────────────────────────────

    def _docker(self, p: ParsedCommand) -> str:
        if p.action == "status" or not p.action:
            return self._executor.execute("docker_status", {})
        return get_domain_help("docker")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _find_id(self, p: ParsedCommand) -> int | None:
        """Trouve un ID numerique dans args ou params."""
        # Chercher dans args (ignore "item", "change", etc.)
        for arg in p.args:
            if arg.isdigit():
                return int(arg)
        # Chercher dans params
        for key in ("id", "item_id", "item"):
            if key in p.params and p.params[key].isdigit():
                return int(p.params[key])
        return None

    def _to_int(self, val: str) -> int | None:
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    def all_shortcuts(self) -> str:
        """Retourne un resume de tous les raccourcis disponibles."""
        lines = ["Raccourcis de commandes AION :", ""]
        for domain, actions in DOMAIN_HELP.items():
            desc = actions.get("_desc", "")
            lines.append(f"  [{domain}] {desc}")
            for action, entries in actions.items():
                if action == "_desc":
                    continue
                if entries:
                    cmd, explanation = entries[0]
                    lines.append(f"    {cmd:<55} {explanation}")
            lines.append("")
        lines.append("  Aide : <domaine> ?   ou   <domaine> <action> ?")
        return "\n".join(lines)
