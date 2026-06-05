"""Application console principale d AION v0.7.0."""
from pathlib import Path

from aion.ai.aion_agent import AionAgent
from aion.ai.ollama_client import OllamaClient
from aion.core.config_loader import ConfigLoader
from aion.core.event_bus import EventBus
from aion.core.executor import ServiceExecutor
from aion.core.logger import setup_logger
from aion.core.registry import ServiceRegistry
from aion.core.scheduler import AionScheduler
from aion.memory.memory_manager import MemoryManager
from aion.notifications.notifier import AionNotifier
from aion.services.domains import DOMAINS, add_domain, list_domains
from aion.tray.tray_app import AionTrayApp

AION_VERSION = "0.7.0"


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
        self.executor = ServiceExecutor(self.registry)
        self.memory = MemoryManager()
        self.event_bus = EventBus()
        self.scheduler = AionScheduler()

        notif_config = self.config.get("notifications", {})
        self.notifier = AionNotifier(enabled=notif_config.get("enabled", True))
        self.tray = AionTrayApp(self)
        self._stop_requested = False

        ai_config = self.config.get("ai", {})
        self._ollama = OllamaClient(
            base_url=ai_config.get("ollama_url", "http://localhost:11434"),
            model=ai_config.get("model", "mistral:latest"),
            timeout=ai_config.get("timeout", 60),
        )
        self._agent = AionAgent(self, self._ollama)
        self._ai_mode = False

        self._register_event_hooks()

    def _register_event_hooks(self) -> None:
        self.event_bus.subscribe("service.executed", self._on_service_executed)
        self.event_bus.subscribe("memory.changed", self._on_memory_changed)
        self.event_bus.subscribe("alert", self._on_alert)

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
        app_name = app_config.get("name", "AION")

        print(f"\n{app_name} v{AION_VERSION}")
        print("AI Agent Orchestrator Node")
        print("Tape 'help' pour voir les commandes.\n")

        self.logger.info("AION started v%s", AION_VERSION)
        self.scheduler.start()
        self.tray.start()
        self.notifier.notify_info(f"AION v{AION_VERSION} demarre !")

        if self._ollama.is_available():
            models = self._ollama.list_models()
            print(f"🤖 Ollama connecte | modele : {self._ollama.model}")
            print(f"   Modeles dispo : {', '.join(models)}")
            print(f"   Tape 'ai' pour le mode conversation\n")
        else:
            print("⚠️  Ollama non detecte - lance : ollama serve\n")

        try:
            self._main_loop()
        finally:
            self.scheduler.stop()
            self.tray.stop()

    def _main_loop(self) -> None:
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
                self.logger.info("AION stopped by user")
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

    def handle_command(self, command: str) -> str:
        self.logger.info("Command received: %s", command)

        if command == "help":            return self._help()
        if command == "services":        return self._list_services()
        if command == "status":          return self._status()
        if command == "reload services":
            self.registry.reload_services()
            return f"Services recharges : {self.registry.count()}"
        if command.startswith("info "):
            return self._service_info(command.replace("info ", "", 1).strip())
        if command.startswith("run "):
            svc = command.replace("run ", "", 1).strip()
            result = self.executor.execute(svc)
            self.event_bus.emit("service.executed", {"service": svc})
            return result

        # Domaines
        if command == "domains":
            return self._list_domains()
        if command.startswith("domain add "):
            return self._add_domain(command.replace("domain add ", "", 1).strip())
        if command.startswith("domain remove "):
            return self._remove_domain(command.replace("domain remove ", "", 1).strip())

        # Memoire
        if command.startswith("remember path "):
            return self._remember_path(command)
        if command.startswith("remember "):
            return self._remember_info(command)
        if command.startswith("recall "):
            key = command.replace("recall ", "", 1).strip()
            value = self.memory.recall(key)
            return f"{key} = {value}" if value is not None else f"Aucune memoire pour : {key}"
        if command in {"memory", "memory list"}:
            return self._list_memory()
        if command.startswith("memory list "):
            return self._list_memory(memory_type=command.replace("memory list ", "", 1).strip())
        if command.startswith("memory show "):
            return self._show_memory_item(command.replace("memory show ", "", 1).strip())
        if command.startswith("memory search "):
            return self._search_memory(command.replace("memory search ", "", 1).strip())
        if command == "memory stats":
            return self._memory_stats()
        if command.startswith("forget "):
            key = command.replace("forget ", "", 1).strip()
            if self.memory.forget(key):
                self.event_bus.emit("memory.changed", {"key": key, "action": "forget"})
                return f"Memoire supprimee : {key}"
            return f"Aucune memoire pour : {key}"

        # EventBus
        if command == "events":          return self._list_events()

        # Scheduler
        if command == "scheduler":       return self._scheduler_status()
        if command.startswith("schedule "):
            return self._schedule_service(command)
        if command.startswith("unschedule "):
            self.scheduler.remove_job(command.replace("unschedule ", "", 1).strip())
            return f"Job supprime : {command.replace('unschedule ', '', 1).strip()}"
        if command.startswith("pause job "):
            jid = command.replace("pause job ", "", 1).strip()
            return f"Job mis en pause : {jid}" if self.scheduler.pause_job(jid) else f"Job introuvable : {jid}"
        if command.startswith("resume job "):
            jid = command.replace("resume job ", "", 1).strip()
            return f"Job repris : {jid}" if self.scheduler.resume_job(jid) else f"Job introuvable : {jid}"

        # Notifications
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

        # API
        if command == "api start":       return self._start_api()

        # IA
        if command == "ai":              return self._ai_enter_mode()
        if command == "ai status":       return self._ai_status()
        if command == "ai models":       return self._ai_list_models()
        if command.startswith("ai model "):
            return self._ai_set_model(command.replace("ai model ", "", 1).strip())
        if command.startswith("ask "):
            return self._agent.ask(command.replace("ask ", "", 1).strip())
        if command.startswith("create service "):
            desc = command.replace("create service ", "", 1).strip()
            return self._agent._creator.create(desc)

        return (
            "Commande inconnue. Essaie : help, services, domains, "
            "run <service>, ai, ask <question>, create service <description>, quit"
        )

    # ── Domaines ──────────────────────────────────────────────────────────────

    def _list_domains(self) -> str:
        domains = list_domains()
        lines = [f"Domaines AION ({len(domains)}) :"]
        for name, desc in domains.items():
            services = [s.name for s in self.registry.list_services()
                       if s.name.startswith(f"{name}_")]
            svc_str = f" [{len(services)} service(s)]" if services else " [aucun service]"
            lines.append(f"  - {name:<10} : {desc}{svc_str}")
        return "\n".join(lines)

    def _add_domain(self, args: str) -> str:
        parts = args.split(" ", 1)
        if len(parts) < 2:
            return "Format : domain add <nom> <description>"
        name, description = parts[0].strip(), parts[1].strip()
        if not name.isalpha() or not name.islower():
            return "Le nom du domaine doit etre en minuscules, lettres uniquement."
        if add_domain(name, description):
            return f"Domaine ajoute : {name} - {description}"
        return f"Le domaine {name} existe deja."

    def _remove_domain(self, name: str) -> str:
        from aion.services.domains import remove_domain
        if remove_domain(name):
            return f"Domaine supprime : {name}"
        return f"Domaine introuvable : {name}"

    # ── IA ────────────────────────────────────────────────────────────────────

    def _ai_enter_mode(self) -> str:
        if not self._ollama.is_available():
            return "Ollama non disponible. Lance : ollama serve"
        self._ai_mode = True
        return (
            f"Mode IA active (modele : {self._ollama.model})\n"
            f"Parle naturellement en francais.\n"
            f"  exit ai          Retour console\n"
            f"  ai clear         Effacer historique\n"
            f"  ai history       Taille historique"
        )

    def _ai_status(self) -> str:
        available = self._ollama.is_available()
        models = self._ollama.list_models() if available else []
        return (
            f"Ollama : {'Connecte' if available else 'Non disponible'}\n"
            f"URL    : {self._ollama.base_url}\n"
            f"Modele : {self._ollama.model}\n"
            f"Modeles: {', '.join(models) if models else 'aucun'}\n"
            f"Historique : {self._agent.history_count()} message(s)\n"
            f"Mode IA : {'actif' if self._ai_mode else 'inactif'}"
        )

    def _ai_set_model(self, model_name: str) -> str:
        self._ollama.model = model_name
        self._agent.clear_history()
        return f"Modele : {model_name} (historique efface)"

    def _ai_list_models(self) -> str:
        if not self._ollama.is_available():
            return "Ollama non disponible."
        models = self._ollama.list_models()
        if not models:
            return "Aucun modele. Essaie : ollama pull mistral"
        lines = ["Modeles Ollama :"]
        for m in models:
            marker = " ← actif" if m.startswith(self._ollama.model) else ""
            lines.append(f"  - {m}{marker}")
        return "\n".join(lines)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _help(self) -> str:
        return """Commandes disponibles :

help                              Affiche l aide
services                          Liste les services
domains                           Liste les domaines
domain add <nom> <desc>           Ajouter un domaine
domain remove <nom>               Supprimer un domaine
reload services                   Recharge les services
info <service>                    Details d un service
run <service>                     Lance un service
status                            Statut d AION

Memoire :
memory / memory list [type]       Lister
memory show/search/stats          Details
remember cle=valeur               Memoriser
recall cle / forget cle           Lire / Supprimer

Scheduler :
scheduler                         Statut
schedule <service> every <N>s     Planifier
unschedule / pause / resume job   Gerer les jobs

Notifications :
notify on/off/status/test         Gerer les notifications

IA Ollama :
ai                                Mode conversation
ask <question>                    Question one-shot
create service <description>      Creer un nouveau service via IA
ai status/models                  Etat Ollama
ai model <nom>                    Changer de modele

API :
api start                         Demarrer (port 8000)
                                  Dashboard : http://127.0.0.1:8000/dashboard

quit                              Quitter AION"""

    def _status(self) -> str:
        stats = self.memory.stats()
        sched_state = "Running" if self.scheduler.is_running() else "Stopped"
        ai_state = "Connecte" if self._ollama.is_available() else "Non disponible"
        domains_count = len(DOMAINS)
        return (
            f"AION Status\n\n"
            f"Version       : {AION_VERSION}\n"
            f"Services      : {self.registry.count()}\n"
            f"Domaines      : {domains_count}\n"
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
        # Grouper par domaine
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
        perms = ", ".join(s.permissions) if s.permissions else "Aucune"
        domain = getattr(s, "domain", "?")
        return f"Service     : {s.name}\nDomaine     : {domain}\nDescription : {s.description}\nPermissions : {perms}"

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
            lines.append(f"  - {event} ({self.event_bus.subscriber_count(event)} abonne(s))")
        return "\n".join(lines)

    def _scheduler_status(self) -> str:
        jobs = self.scheduler.list_jobs()
        state = "Running" if self.scheduler.is_running() else "Stopped"
        if not jobs:
            return f"Scheduler : {state} - Aucun job."
        lines = [f"Scheduler : {state} - {self.scheduler.job_count()} job(s) :"]
        for job_id, info in jobs.items():
            icon = "⏸" if self.scheduler.get_job_state(job_id) == "paused" else "▶"
            lines.append(f"  {icon} {job_id} (toutes les {info['interval_seconds']}s)")
        return "\n".join(lines)

    def _schedule_service(self, command: str) -> str:
        try:
            parts = command.replace("schedule ", "", 1).split(" every ")
            if len(parts) != 2:
                return "Format : schedule <service> every <N>s"
            service_name = parts[0].strip()
            interval_seconds = int(parts[1].strip().rstrip("s"))
        except (ValueError, IndexError):
            return "Format : schedule <service> every <N>s"

        if self.registry.get(service_name) is None:
            return f"Service introuvable : {service_name}"

        job_id = f"scheduled_{service_name}"
        _executor, _notifier, _logger = self.executor, self.notifier, self.logger

        def run():
            result = _executor.execute(service_name, {})
            _logger.info("Scheduled '%s': %s", service_name, result)
            if any(kw in result.upper() for kw in ["ALERTE", "DOWN", "ERROR"]):
                _notifier.notify_alert(f"{service_name}: {result[:120]}")

        self.scheduler.add_job(job_id, run, interval_seconds=interval_seconds)
        self.tray.update_menu()
        return f"Job planifie : {job_id} (toutes les {interval_seconds}s)"

    def _start_api(self) -> str:
        try:
            import subprocess, sys
            subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "aion.api.server:app",
                 "--host", "127.0.0.1", "--port", "8000"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            self.notifier.notify_info("API demarree -> http://127.0.0.1:8000")
            return (
                "API demarree    -> http://127.0.0.1:8000\n"
                "Dashboard       -> http://127.0.0.1:8000/dashboard\n"
                "Swagger         -> http://127.0.0.1:8000/docs"
            )
        except Exception as exc:
            return f"Erreur API : {exc}"
