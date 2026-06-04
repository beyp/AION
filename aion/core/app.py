"""Application console principale d AION v0.4.0."""
from pathlib import Path

from aion.core.config_loader import ConfigLoader
from aion.core.event_bus import EventBus
from aion.core.executor import ServiceExecutor
from aion.core.logger import setup_logger
from aion.core.registry import ServiceRegistry
from aion.core.scheduler import AionScheduler
from aion.memory.memory_manager import MemoryManager

AION_VERSION = "0.4.0"


class AionApp:
    """Application console principale pour AION."""

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

        self._register_event_hooks()

    def _register_event_hooks(self) -> None:
        """Enregistre les hooks internes de l EventBus."""
        self.event_bus.subscribe("service.executed", self._on_service_executed)
        self.event_bus.subscribe("memory.changed", self._on_memory_changed)

    def _on_service_executed(self, data: dict) -> None:
        self.logger.info("Event [service.executed]: %s", data.get("service"))

    def _on_memory_changed(self, data: dict) -> None:
        self.logger.info(
            "Event [memory.changed]: key=%s action=%s",
            data.get("key"),
            data.get("action"),
        )

    def run(self) -> None:
        app_config = self.config.get("app", {})
        app_name = app_config.get("name", "AION")

        print(f"\n{app_name} v{AION_VERSION}")
        print("AI Agent Orchestrator Node")
        print("Tape 'help' pour voir les commandes.\n")

        self.logger.info("AION started v%s", AION_VERSION)
        self.scheduler.start()

        try:
            self._main_loop()
        finally:
            self.scheduler.stop()

    def _main_loop(self) -> None:
        while True:
            try:
                command = input("AION> ").strip()
            except KeyboardInterrupt:
                print("\nArret demande.")
                break

            if not command:
                continue

            if command in {"quit", "exit"}:
                print("Arret d'AION.")
                self.logger.info("AION stopped by user")
                break

            response = self.handle_command(command)
            print(response)

    def handle_command(self, command: str) -> str:
        self.logger.info("Command received: %s", command)

        if command == "help":
            return self._help()

        if command == "services":
            return self._list_services()

        if command == "status":
            return self._status()

        if command == "reload services":
            self.registry.reload_services()
            return f"Services recharges : {self.registry.count()}"

        if command.startswith("info "):
            service_name = command.replace("info ", "", 1).strip()
            return self._service_info(service_name)

        if command.startswith("run "):
            service_name = command.replace("run ", "", 1).strip()
            result = self.executor.execute(service_name)
            self.event_bus.emit("service.executed", {"service": service_name})
            return result

        # Memoire
        if command.startswith("remember path "):
            return self._remember_path(command)

        if command.startswith("remember "):
            return self._remember_info(command)

        if command.startswith("recall "):
            key = command.replace("recall ", "", 1).strip()
            value = self.memory.recall(key)
            if value is None:
                return f"Aucune memoire trouvee pour : {key}"
            return f"{key} = {value}"

        if command in {"memory", "memory list"}:
            return self._list_memory()

        if command.startswith("memory list "):
            memory_type = command.replace("memory list ", "", 1).strip()
            return self._list_memory(memory_type=memory_type)

        if command.startswith("memory show "):
            key = command.replace("memory show ", "", 1).strip()
            return self._show_memory_item(key)

        if command.startswith("memory search "):
            query = command.replace("memory search ", "", 1).strip()
            return self._search_memory(query)

        if command == "memory stats":
            return self._memory_stats()

        if command.startswith("forget "):
            key = command.replace("forget ", "", 1).strip()
            if self.memory.forget(key):
                self.event_bus.emit("memory.changed", {"key": key, "action": "forget"})
                return f"Memoire supprimee : {key}"
            return f"Aucune memoire trouvee pour : {key}"

        # EventBus
        if command == "events":
            return self._list_events()

        # Scheduler
        if command == "scheduler":
            return self._scheduler_status()

        if command.startswith("schedule "):
            return self._schedule_service(command)

        if command.startswith("unschedule "):
            job_id = command.replace("unschedule ", "", 1).strip()
            self.scheduler.remove_job(job_id)
            return f"Job supprime : {job_id}"

        if command.startswith("pause job "):
            job_id = command.replace("pause job ", "", 1).strip()
            if self.scheduler.pause_job(job_id):
                return f"Job mis en pause : {job_id}"
            return f"Job introuvable : {job_id}"

        if command.startswith("resume job "):
            job_id = command.replace("resume job ", "", 1).strip()
            if self.scheduler.resume_job(job_id):
                return f"Job repris : {job_id}"
            return f"Job introuvable : {job_id}"

        # API
        if command == "api start":
            return self._start_api()

        return (
            "Commande inconnue. Essaie : help, services, run <service>, "
            "scheduler, schedule <service> every <N>s, api start, events, memory list, quit"
        )

    def _help(self) -> str:
        return """Commandes disponibles :

help                              Affiche l aide
services                          Liste les services disponibles
reload services                   Recharge les services sans redemarrer
info <service>                    Details d un service
run <service>                     Lance un service
status                            Statut d AION

Memoire :
memory                            Liste toute la memoire persistante
memory list [type]                Liste la memoire (filtrable par type)
memory show <cle>                 Detail d un element memoire
memory search <texte>             Recherche dans la memoire
memory stats                      Statistiques memoire
remember cle=valeur               Memorise une information
remember path cle=chemin          Memorise un chemin local existant
recall cle                        Rappelle une valeur
forget cle                        Supprime une memoire

EventBus :
events                            Liste les evenements actifs

Scheduler :
scheduler                         Statut du planificateur
schedule <service> every <N>s     Planifie un service toutes les N secondes
unschedule <job_id>               Supprime un job planifie
pause job <job_id>                Met un job en pause
resume job <job_id>               Reprend un job en pause

API REST :
api start                         Demarre le serveur API REST (port 8000)

quit                              Quitte AION"""

    def _status(self) -> str:
        stats = self.memory.stats()
        active_events = self.event_bus.list_events()
        sched_state = "Running" if self.scheduler.is_running() else "Stopped"
        return f"""AION Status

Version      : {AION_VERSION}
Services     : {self.registry.count()}
Memory       : Ready ({stats["total"]} items, {stats["temporary_total"]} temp)
EventBus     : Ready ({len(active_events)} event(s) actif(s))
Scheduler    : {sched_state} ({self.scheduler.job_count()} jobs)
API REST     : http://127.0.0.1:8000 (lancez "api start")
AI           : Not Connected"""

    def _list_services(self) -> str:
        services = self.registry.list_services()
        if not services:
            return "Aucun service enregistre."
        lines = ["Services disponibles :"]
        for s in services:
            lines.append(f"  - {s.name}: {s.description}")
        return "\n".join(lines)

    def _service_info(self, service_name: str) -> str:
        service = self.registry.get(service_name)
        if service is None:
            return "Service introuvable."
        perms = ", ".join(service.permissions) if service.permissions else "Aucune"
        return f"""Service     : {service.name}
Description : {service.description}
Permissions : {perms}"""

    def _remember_info(self, command: str) -> str:
        raw = command.replace("remember ", "", 1).strip()
        if "=" not in raw:
            return "Format attendu : remember cle=valeur"
        key, value = raw.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key or not value:
            return "La cle et la valeur sont obligatoires."
        self.memory.remember(key, value, memory_type="info")
        self.event_bus.emit("memory.changed", {"key": key, "action": "remember"})
        return f"Information memorisee : {key}"

    def _remember_path(self, command: str) -> str:
        raw = command.replace("remember path ", "", 1).strip()
        if "=" not in raw:
            return "Format attendu : remember path cle=chemin"
        key, value = raw.split("=", 1)
        key, value = key.strip(), value.strip().strip('"')
        if not key or not value:
            return "La cle et le chemin sont obligatoires."
        path = Path(value)
        if not path.exists():
            return f"Chemin introuvable : {value}"
        self.memory.remember(key, str(path), memory_type="path")
        self.event_bus.emit("memory.changed", {"key": key, "action": "remember_path"})
        return f"Chemin memorise : {key}"

    def _list_memory(self, memory_type: str | None = None) -> str:
        items = self.memory.list_memory(memory_type=memory_type)
        if not items:
            label = f"[{memory_type}] " if memory_type else ""
            return f"Memoire {label}vide."
        title = f"Memoire AION{f' [{memory_type}]' if memory_type else ''} :"
        lines = [title]
        for key, item in items.items():
            lines.append(f"  - {key} [{item.get('type', 'info')}] = {item.get('value')}")
        return "\n".join(lines)

    def _show_memory_item(self, key: str) -> str:
        item = self.memory.get_item(key)
        if item is None:
            return f"Aucune memoire trouvee pour : {key}"
        return f"""Memoire     : {key}
Type        : {item.get("type", "info")}
Valeur      : {item.get("value")}
Creee       : {item.get("created_at", "inconnu")}
Mise a jour : {item.get("updated_at", "inconnu")}"""

    def _search_memory(self, query: str) -> str:
        results = self.memory.search(query)
        if not results:
            return f"Aucune memoire trouvee pour : {query}"
        lines = [f"Resultats pour '{query}' :"]
        for key, item in results.items():
            lines.append(f"  - {key} [{item.get('type', 'info')}] = {item.get('value')}")
        return "\n".join(lines)

    def _memory_stats(self) -> str:
        stats = self.memory.stats()
        lines = [
            "Statistiques memoire :",
            f"  Total permanent  : {stats['total']}",
            f"  Total temporaire : {stats['temporary_total']}",
            "  Par type :",
        ]
        if not stats["by_type"]:
            lines.append("    Aucun element")
        else:
            for t, count in stats["by_type"].items():
                lines.append(f"    - {t}: {count}")
        return "\n".join(lines)

    def _list_events(self) -> str:
        events = self.event_bus.list_events()
        if not events:
            return "Aucun evenement actif."
        lines = ["Evenements actifs :"]
        for event in events:
            count = self.event_bus.subscriber_count(event)
            lines.append(f"  - {event} ({count} abonne(s))")
        return "\n".join(lines)

    def _scheduler_status(self) -> str:
        jobs = self.scheduler.list_jobs()
        state = "Running" if self.scheduler.is_running() else "Stopped"
        if not jobs:
            return f"Scheduler : {state} - Aucun job planifie."
        lines = [f"Scheduler : {state} - {self.scheduler.job_count()} job(s) :"]
        for job_id, info in jobs.items():
            lines.append(
                f"  - {job_id} -> {info['func']} (toutes les {info['interval_seconds']}s)"
            )
        return "\n".join(lines)

    def _schedule_service(self, command: str) -> str:
        try:
            parts = command.replace("schedule ", "", 1).split(" every ")
            if len(parts) != 2:
                return "Format attendu : schedule <service> every <N>s"
            service_name = parts[0].strip()
            interval_str = parts[1].strip().rstrip("s")
            interval_seconds = int(interval_str)
        except (ValueError, IndexError):
            return "Format attendu : schedule <service> every <N>s  (ex: schedule ping every 60s)"

        service = self.registry.get(service_name)
        if service is None:
            return f"Service introuvable : {service_name}"

        job_id = f"scheduled_{service_name}"
        _executor = self.executor
        _logger = self.logger

        def run():
            result = _executor.execute(service_name, {})
            _logger.info("Scheduled job '%s' result: %s", service_name, result)

        self.scheduler.add_job(job_id, run, interval_seconds=interval_seconds)
        return f"Job planifie : {job_id} (toutes les {interval_seconds}s)"

    def _start_api(self) -> str:
        try:
            import subprocess
            import sys
            subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "aion.api.server:app",
                 "--host", "127.0.0.1", "--port", "8000"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return (
                "Serveur API demarre -> http://127.0.0.1:8000\n"
                "Docs disponibles sur  http://127.0.0.1:8000/docs"
            )
        except Exception as exc:
            return f"Impossible de demarrer l API : {exc}"
