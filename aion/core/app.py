"""Application console principale d AION v0.7.2."""
from pathlib import Path

from aion.ai.aion_agent import AionAgent
from aion.ai.ollama_client import OllamaClient
from aion.core.command_parser import get_domain_help
from aion.core.config_loader import ConfigLoader
from aion.core.domain_router import DomainRouter
from aion.core.event_bus import EventBus
from aion.core.executor import ServiceExecutor
from aion.core.help_builder import build_help
from aion.core.logger import setup_logger
from aion.core.registry import ServiceRegistry
from aion.core.scheduler import AionScheduler
from aion.memory.memory_manager import MemoryManager
from aion.notifications.notifier import AionNotifier
from aion.services.domains import DOMAINS, add_domain, list_domains, remove_domain
from aion.tray.tray_app import AionTrayApp

AION_VERSION = "0.7.2"

def _get_hint(cmd: str) -> str:
    """Retourne une description courte pour l autocompletion."""
    hints = {
        "ado get item ":       "Voir un work item",
        "ado status change ":  "Changer le statut",
        "ado list":            "Lister les items",
        "ado my":              "Mes items assignes",
        "net status":          "Statut reseau",
        "net ping":            "Ping 8.8.8.8",
        "sys cpu":             "CPU et RAM",
        "sys disk":            "Partitions disque",
        "fs search ":          "Rechercher des fichiers",
        "qm add ":             "Creer une tache",
        "qm list":             "Lister les taches",
        "qm done ":            "Marquer termine",
        "docker status":       "Conteneurs Docker",
        "help":                "Aide complete",
        "shortcuts":           "Raccourcis par domaine",
        "status":              "Statut AION",
    }
    for key, val in hints.items():
        if cmd.startswith(key):
            return val
    return ""


class AionApp:
    """Application console principale pour AION."""

    AION_VERSION = AION_VERSION

    def __init__(self) -> None:
        self.config = ConfigLoader().load()

        logging_config = self.config.get("logging", {})
        self.logger = setup_logger(
            log_file=logging_config.get("file", "logs/aion.log"),
            level=logging_config.get("level", "INFO"),
        )

        self.registry = ServiceRegistry()
        self.registry.discover_services()
        self.executor  = ServiceExecutor(self.registry)
        self.memory    = MemoryManager()
        self.event_bus = EventBus()
        self.scheduler = AionScheduler()

        notif_config = self.config.get("notifications", {})
        self.notifier = AionNotifier(enabled=notif_config.get("enabled", True))
        self.tray     = AionTrayApp(self)
        self._stop_requested = False

        # Domain Router — commandes naturelles
        self.domain_router = DomainRouter(self.executor, self.memory)

        ai_config = self.config.get("ai", {})
        self._ollama = OllamaClient(
            base_url=ai_config.get("ollama_url", "http://localhost:11434"),
            model=ai_config.get("model", "mistral:latest"),
            timeout=ai_config.get("timeout", 60),
        )
        self._agent  = AionAgent(self, self._ollama)
        self._ai_mode = False

        self._register_event_hooks()

    def _register_event_hooks(self) -> None:
        self.event_bus.subscribe("service.executed", self._on_service_executed)
        self.event_bus.subscribe("memory.changed",   self._on_memory_changed)
        self.event_bus.subscribe("alert",            self._on_alert)

    def _on_service_executed(self, data: dict) -> None:
        self.logger.info("Event [service.executed]: %s", data.get("service"))

    def _on_memory_changed(self, data: dict) -> None:
        self.logger.info("Event [memory.changed]: key=%s action=%s",
                         data.get("key"), data.get("action"))

    def _on_alert(self, data: dict) -> None:
        message = data.get("message", "Alerte AION")
        self.logger.warning("Event [alert]: %s", message)
        self.notifier.notify_alert(message)

    def request_stop(self) -> None:
        self._stop_requested = True

    def run(self) -> None:
        app_config = self.config.get("app", {})
        app_name   = app_config.get("name", "AION")

        print(f"\n{app_name} v{AION_VERSION}")
        print("AI Agent Orchestrator Node")
        print("Tape 'help' ou 'shortcuts' pour les commandes.\n")

        self.logger.info("AION started v%s", AION_VERSION)
        self.scheduler.start()
        self.tray.start()
        self.notifier.notify_info(f"AION v{AION_VERSION} demarre !")

        if self._ollama.is_available():
            models = self._ollama.list_models()
            print(f"🤖 Ollama connecte | modele : {self._ollama.model}")
            print(f"   Modeles : {', '.join(models)}")
            print(f"   Tape 'ai' pour la conversation\n")
        else:
            print("⚠️  Ollama non detecte\n")

        try:
            self._main_loop()
        finally:
            self.scheduler.stop()
            self.tray.stop()

    def _main_loop(self) -> None:
        # Tenter d utiliser prompt_toolkit pour l autocompletion
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.completion import WordCompleter
            from prompt_toolkit.history import InMemoryHistory
            from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

            self._use_prompt_toolkit = True
        except ImportError:
            self._use_prompt_toolkit = False

        if self._use_prompt_toolkit:
            self._main_loop_pt()
        else:
            self._main_loop_basic()

    def _build_completer(self):
        """Construit la liste de completions dynamiquement."""
        from prompt_toolkit.completion import Completer, Completion

        commands = [
            # Core
            "help", "shortcuts", "status", "services", "domains", "reload services",
            "scheduler", "memory", "events", "api start", "notify on", "notify off",
            "notify status", "notify test", "quit",
            # AI
            "ai", "ai status", "ai models", "ask ",
            # Memory
            "remember ", "remember path ", "recall ", "forget ",
            "memory list", "memory show ", "memory search ", "memory stats",
            # Scheduler
            "schedule ", "unschedule ", "pause job ", "resume job ",
            # ADO
            "ado get item ",
            "ado status change ",
            "ado list",
            "ado list --state ",
            "ado list --type Bug",
            "ado list --type Task",
            "ado list --type User Story",
            "ado list --type Feature",
            "ado list --type Epic",
            "ado my",
            "ado my --state ",
            "ado open ",
            "ado project ",
            "ado ?",
            # NET
            "net status", "net myip", "net ping", "net ping ",
            "net ?",
            # SYS
            "sys cpu", "sys disk", "sys uptime", "sys info",
            "sys ?",
            # FS
            "fs search ", "fs ?",
            # QM
            "qm add ", "qm list", "qm list --priority ",
            "qm done ", "qm health", "qm ?",
            # DOCKER
            "docker status",
        ]

        # Ajouter les services dynamiquement
        for svc in self.registry.list_services():
            commands.append(f"run {svc.name}")

        class AionCompleter(Completer):
            def get_completions(self, document, complete_event):
                text = document.text_before_cursor
                text_lower = text.lower()
                for cmd in commands:
                    if cmd.lower().startswith(text_lower) and cmd.lower() != text_lower:
                        yield Completion(
                            cmd[len(text):],
                            start_position=0,
                            display=cmd,
                            display_meta=_get_hint(cmd),
                        )

        return AionCompleter()

    def _main_loop_pt(self) -> None:
        """Boucle principale avec prompt_toolkit (autocompletion)."""
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        from prompt_toolkit.styles import Style

        style = Style.from_dict({
            "prompt":    "ansicyan bold",
            "": "ansiwhite",
        })

        session = PromptSession(
            history=InMemoryHistory(),
            auto_suggest=AutoSuggestFromHistory(),
            completer=self._build_completer(),
            complete_while_typing=True,
            style=style,
        )

        while True:
            if self._stop_requested:
                print("\nArret demande via systray.")
                break
            try:
                prompt_str = "🤖 AION AI> " if self._ai_mode else "AION> "
                command = session.prompt(prompt_str).strip()
            except KeyboardInterrupt:
                print("\nArret demande.")
                break
            except EOFError:
                break

            if not command:
                continue
            if command in {"quit", "exit"}:
                print("Arret d'AION.")
                break

            if self._ai_mode:
                if command == "exit ai":
                    self._ai_mode = False
                    print("Mode IA desactive.")
                    continue
                if command == "ai clear":
                    self._agent.clear_history()
                    print("Historique efface.")
                    continue
                if command == "ai history":
                    print(f"Historique : {self._agent.history_count()} message(s)")
                    continue
                print(self._agent.ask(command))
                continue

            print(self.handle_command(command))

    def _main_loop_basic(self) -> None:
        """Boucle de fallback sans autocompletion."""
        while True:
            if self._stop_requested:
                print("\nArret demande via systray.")
                break
            try:
                prompt_str = "🤖 AION AI> " if self._ai_mode else "AION> "
                command = input(prompt_str).strip()
            except (KeyboardInterrupt, EOFError):
                print("\nArret demande.")
                break

            if not command:
                continue
            if command in {"quit", "exit"}:
                print("Arret d'AION.")
                break

            if self._ai_mode:
                if command == "exit ai":
                    self._ai_mode = False
                    print("Mode IA desactive.")
                    continue
                if command == "ai clear":
                    self._agent.clear_history()
                    print("Historique efface.")
                    continue
                print(self._agent.ask(command))
                continue

            print(self.handle_command(command))


    def handle_command(self, command: str) -> str:
        self.logger.info("Command received: %s", command)

        # ── 1. Commandes core AION ────────────────────────────────────────────
        if command == "help":
            return build_help(self.registry)
        if command == "shortcuts":
            return self.domain_router.all_shortcuts()
        if command == "services":
            return self._list_services()
        if command == "status":
            return self._status()
        if command == "reload services":
            self.registry.reload_services()
            return f"Services recharges : {self.registry.count()}"
        if command.startswith("info "):
            return self._service_info(command.replace("info ", "", 1).strip())

        # run <service> [id_ou_json] — retro-compatibilite
        if command.startswith("run "):
            return self._run_command(command)

        # create service
        if command.startswith("create service "):
            return self._agent._creator.create(
                command.replace("create service ", "", 1).strip()
            )

        # ── Domaines ──────────────────────────────────────────────────────────
        if command == "domains":
            return self._list_domains()
        if command.startswith("domain add "):
            return self._add_domain(command.replace("domain add ", "", 1).strip())
        if command.startswith("domain remove "):
            name = command.replace("domain remove ", "", 1).strip()
            return (f"Domaine supprime : {name}"
                    if remove_domain(name) else f"Domaine introuvable : {name}")

        # ── Memoire ───────────────────────────────────────────────────────────
        if command.startswith("remember path "):
            return self._remember_path(command)
        if command.startswith("remember "):
            return self._remember_info(command)
        if command.startswith("recall "):
            key   = command.replace("recall ", "", 1).strip()
            value = self.memory.recall(key)
            return f"{key} = {value}" if value is not None else f"Aucune memoire pour : {key}"
        if command in {"memory", "memory list"}:
            return self._list_memory()
        if command.startswith("memory list "):
            return self._list_memory(
                memory_type=command.replace("memory list ", "", 1).strip()
            )
        if command.startswith("memory show "):
            return self._show_memory_item(
                command.replace("memory show ", "", 1).strip()
            )
        if command.startswith("memory search "):
            return self._search_memory(
                command.replace("memory search ", "", 1).strip()
            )
        if command == "memory stats":
            return self._memory_stats()
        if command.startswith("forget "):
            key = command.replace("forget ", "", 1).strip()
            if self.memory.forget(key):
                self.event_bus.emit("memory.changed", {"key": key, "action": "forget"})
                return f"Memoire supprimee : {key}"
            return f"Aucune memoire pour : {key}"

        # ── EventBus ──────────────────────────────────────────────────────────
        if command == "events":
            return self._list_events()

        # ── Scheduler ─────────────────────────────────────────────────────────
        if command == "scheduler":
            return self._scheduler_status()
        if command.startswith("schedule "):
            return self._schedule_service(command)
        if command.startswith("unschedule "):
            jid = command.replace("unschedule ", "", 1).strip()
            self.scheduler.remove_job(jid)
            return f"Job supprime : {jid}"
        if command.startswith("pause job "):
            jid = command.replace("pause job ", "", 1).strip()
            return (f"Job mis en pause : {jid}"
                    if self.scheduler.pause_job(jid) else f"Job introuvable : {jid}")
        if command.startswith("resume job "):
            jid = command.replace("resume job ", "", 1).strip()
            return (f"Job repris : {jid}"
                    if self.scheduler.resume_job(jid) else f"Job introuvable : {jid}")

        # ── Notifications ─────────────────────────────────────────────────────
        if command == "notify on":
            self.notifier.enabled = True; self.tray.update_menu()
            return "Notifications activees."
        if command == "notify off":
            self.notifier.enabled = False; self.tray.update_menu()
            return "Notifications desactivees."
        if command == "notify status":
            s = "activees" if self.notifier.enabled else "desactivees"
            a = "disponible" if self.notifier.available else "non disponible"
            return f"Notifications : {s} | plyer : {a}"
        if command == "notify test":
            self.notifier.notify_info("Test notification AION ! 🎉")
            return "Notification envoyee."

        # ── API ───────────────────────────────────────────────────────────────
        if command == "api start":
            return self._start_api()

        # ── IA Ollama ─────────────────────────────────────────────────────────
        if command == "ai":
            return self._ai_enter_mode()
        if command == "ai status":
            return self._ai_status()
        if command == "ai models":
            return self._ai_list_models()
        if command.startswith("ai model "):
            return self._ai_set_model(
                command.replace("ai model ", "", 1).strip()
            )
        if command.startswith("ask "):
            return self._agent.ask(command.replace("ask ", "", 1).strip())

        # ── 2. Domain Router — commandes naturelles ───────────────────────────
        if self.domain_router.can_handle(command):
            result = self.domain_router.dispatch(command)
            if result is not None:
                self.event_bus.emit("service.executed", {"service": command.split()[0]})
                return result

        return (
            "Commande inconnue.\n"
            "  help        : liste complete des commandes\n"
            "  shortcuts   : raccourcis par domaine (ado, net, sys, fs, qm...)\n"
            "  ado ?       : aide du domaine ado\n"
            "  ado get ?   : aide de la commande ado get"
        )

    # ── run retro-compatible ──────────────────────────────────────────────────

    def _run_command(self, command: str) -> str:
        """Gere run <service> [arg_ou_json]."""
        import json as _json
        parts        = command.replace("run ", "", 1).strip().split(" ", 1)
        service_name = parts[0]
        payload      = {}

        if len(parts) > 1:
            arg = parts[1].strip()
            if arg.startswith("{"):
                try:
                    payload = _json.loads(arg)
                except Exception:
                    return f"Payload JSON invalide : {arg}"
            elif arg.isdigit():
                payload = {"item_id": int(arg)}
            else:
                payload = {"keywords": arg}

        result = self.executor.execute(service_name, payload)
        self.event_bus.emit("service.executed", {"service": service_name})
        return result

    # ── IA ────────────────────────────────────────────────────────────────────

    def _ai_enter_mode(self) -> str:
        if not self._ollama.is_available():
            return "Ollama non disponible. Lance : ollama serve"
        self._ai_mode = True
        return (
            f"Mode IA active (modele : {self._ollama.model})\n"
            f"  exit ai    Retour console\n"
            f"  ai clear   Effacer historique"
        )

    def _ai_status(self) -> str:
        available = self._ollama.is_available()
        models    = self._ollama.list_models() if available else []
        return (
            f"Ollama : {'Connecte' if available else 'Non disponible'}\n"
            f"Modele : {self._ollama.model}\n"
            f"Modeles: {', '.join(models) if models else 'aucun'}"
        )

    def _ai_set_model(self, model_name: str) -> str:
        self._ollama.model = model_name
        self._agent.clear_history()
        return f"Modele : {model_name}"

    def _ai_list_models(self) -> str:
        if not self._ollama.is_available():
            return "Ollama non disponible."
        models = self._ollama.list_models()
        if not models:
            return "Aucun modele. Essaie : ollama pull mistral"
        lines = ["Modeles Ollama :"]
        for m in models:
            marker = " <- actif" if m.startswith(self._ollama.model) else ""
            lines.append(f"  - {m}{marker}")
        return "\n".join(lines)

    # ── Status & Services ─────────────────────────────────────────────────────

    def _status(self) -> str:
        stats       = self.memory.stats()
        sched_state = "Running" if self.scheduler.is_running() else "Stopped"
        ai_state    = "Connecte" if self._ollama.is_available() else "Non disponible"
        return (
            f"AION Status\n\n"
            f"Version       : {AION_VERSION}\n"
            f"Services      : {self.registry.count()}\n"
            f"Domaines      : {len(DOMAINS)}\n"
            f"Memory        : {stats['total']} items\n"
            f"Scheduler     : {sched_state} ({self.scheduler.job_count()} jobs)\n"
            f"Notifications : {'ON' if self.notifier.enabled else 'OFF'}\n"
            f"Ollama        : {ai_state} | {self._ollama.model}\n"
            f"Dashboard     : http://127.0.0.1:8000/dashboard"
        )

    def _list_services(self) -> str:
        services = self.registry.list_services()
        if not services:
            return "Aucun service enregistre."
        from aion.services.domains import get_domain
        grouped: dict[str, list] = {}
        for s in services:
            domain = get_domain(s.name) or "other"
            grouped.setdefault(domain, []).append(s)
        lines = [f"Services AION ({len(services)}) :"]
        for domain, svcs in sorted(grouped.items()):
            lines.append(f"  [{domain}]")
            for s in svcs:
                lines.append(f"    - {s.name}: {s.description}")
        return "\n".join(lines)

    def _service_info(self, name: str) -> str:
        s = self.registry.get(name)
        if s is None:
            return "Service introuvable."
        perms  = ", ".join(s.permissions) if s.permissions else "Aucune"
        domain = getattr(s, "domain", "?")
        return (
            f"Service     : {s.name}\n"
            f"Domaine     : {domain}\n"
            f"Description : {s.description}\n"
            f"Permissions : {perms}"
        )

    # ── Domaines ──────────────────────────────────────────────────────────────

    def _list_domains(self) -> str:
        domains = list_domains()
        lines   = [f"Domaines AION ({len(domains)}) :"]
        for name, desc in domains.items():
            svcs    = [s.name for s in self.registry.list_services()
                       if s.name.startswith(f"{name}_")]
            svc_str = f" [{len(svcs)} service(s)]" if svcs else " [aucun service]"
            lines.append(f"  - {name:<12} : {desc}{svc_str}")
        return "\n".join(lines)

    def _add_domain(self, args: str) -> str:
        parts = args.split(" ", 1)
        if len(parts) < 2:
            return "Format : domain add <nom> <description>"
        name, description = parts[0].strip(), parts[1].strip()
        if not name.isalpha() or not name.islower():
            return "Le nom doit etre en minuscules, lettres uniquement."
        return (f"Domaine ajoute : {name}"
                if add_domain(name, description) else f"Domaine {name} existe deja.")

    # ── Memoire ───────────────────────────────────────────────────────────────

    def _remember_info(self, command: str) -> str:
        raw = command.replace("remember ", "", 1).strip()
        if "=" not in raw:
            return "Format : remember cle=valeur"
        key, value = raw.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key or not value:
            return "Cle et valeur obligatoires."
        self.memory.remember(key, value, memory_type="info")
        self.event_bus.emit("memory.changed", {"key": key, "action": "remember"})
        return f"Memorise : {key}"

    def _remember_path(self, command: str) -> str:
        raw = command.replace("remember path ", "", 1).strip()
        if "=" not in raw:
            return "Format : remember path cle=chemin"
        key, value = raw.split("=", 1)
        key, value = key.strip(), value.strip().strip('"')
        path = Path(value)
        if not path.exists():
            return f"Chemin introuvable : {value}"
        self.memory.remember(key, str(path), memory_type="path")
        self.event_bus.emit("memory.changed", {"key": key, "action": "remember_path"})
        return f"Chemin memorise : {key}"

    def _list_memory(self, memory_type: str | None = None) -> str:
        items = self.memory.list_memory(memory_type=memory_type)
        if not items:
            return f"Memoire{f' [{memory_type}]' if memory_type else ''} vide."
        lines = [f"Memoire AION{f' [{memory_type}]' if memory_type else ''} :"]
        for key, item in items.items():
            lines.append(f"  - {key} [{item.get('type', 'info')}] = {item.get('value')}")
        return "\n".join(lines)

    def _show_memory_item(self, key: str) -> str:
        item = self.memory.get_item(key)
        if item is None:
            return f"Aucune memoire pour : {key}"
        return (
            f"Memoire     : {key}\n"
            f"Type        : {item.get('type', 'info')}\n"
            f"Valeur      : {item.get('value')}\n"
            f"Creee       : {item.get('created_at', '?')}\n"
            f"Mise a jour : {item.get('updated_at', '?')}"
        )

    def _search_memory(self, query: str) -> str:
        results = self.memory.search(query)
        if not results:
            return f"Aucun resultat pour : {query}"
        lines = [f"Resultats '{query}' :"]
        for key, item in results.items():
            lines.append(f"  - {key} [{item.get('type')}] = {item.get('value')}")
        return "\n".join(lines)

    def _memory_stats(self) -> str:
        stats = self.memory.stats()
        lines = [
            "Statistiques memoire :",
            f"  Permanent  : {stats['total']}",
            f"  Temporaire : {stats['temporary_total']}",
            "  Par type :",
        ]
        for t, count in (stats["by_type"] or {}).items():
            lines.append(f"    - {t}: {count}")
        return "\n".join(lines)

    def _list_events(self) -> str:
        events = self.event_bus.list_events()
        if not events:
            return "Aucun evenement actif."
        lines = ["Evenements actifs :"]
        for event in events:
            lines.append(
                f"  - {event} ({self.event_bus.subscriber_count(event)} abonne(s))"
            )
        return "\n".join(lines)

    def _scheduler_status(self) -> str:
        jobs  = self.scheduler.list_jobs()
        state = "Running" if self.scheduler.is_running() else "Stopped"
        if not jobs:
            return f"Scheduler : {state} - Aucun job."
        lines = [f"Scheduler : {state} - {self.scheduler.job_count()} job(s) :"]
        for job_id, info in jobs.items():
            icon = "⏸" if self.scheduler.get_job_state(job_id) == "paused" else "▶"
            lines.append(
                f"  {icon} {job_id} (toutes les {info['interval_seconds']}s)"
            )
        return "\n".join(lines)

    def _schedule_service(self, command: str) -> str:
        try:
            parts            = command.replace("schedule ", "", 1).split(" every ")
            service_name     = parts[0].strip()
            interval_seconds = int(parts[1].strip().rstrip("s"))
        except (ValueError, IndexError):
            return "Format : schedule <service> every <N>s"

        if self.registry.get(service_name) is None:
            return f"Service introuvable : {service_name}"

        job_id   = f"scheduled_{service_name}"
        _exec    = self.executor
        _notif   = self.notifier
        _logger  = self.logger

        def run():
            result = _exec.execute(service_name, {})
            _logger.info("Scheduled '%s': %s", service_name, result)
            if any(kw in result.upper() for kw in ["ALERTE", "DOWN", "ERROR"]):
                _notif.notify_alert(f"{service_name}: {result[:120]}")

        self.scheduler.add_job(job_id, run, interval_seconds=interval_seconds)
        self.tray.update_menu()
        return f"Job planifie : {job_id} (toutes les {interval_seconds}s)"

    def _start_api(self) -> str:
        try:
            import subprocess, sys
            subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "aion.dashboard.server:app",
                 "--host", "127.0.0.1", "--port", "8000"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.notifier.notify_info("Dashboard -> http://127.0.0.1:8000")
            return (
                "Dashboard -> http://127.0.0.1:8000/dashboard\n"
                "Swagger   -> http://127.0.0.1:8000/docs"
            )
        except Exception as exc:
            return f"Erreur API : {exc}"
