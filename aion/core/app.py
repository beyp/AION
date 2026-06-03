from pathlib import Path

from aion.core.config_loader import ConfigLoader
from aion.core.executor import ServiceExecutor
from aion.core.logger import setup_logger
from aion.core.registry import ServiceRegistry
from aion.memory.memory_manager import MemoryManager


class AionApp:
    """Main console application for AION."""

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

    def run(self) -> None:
        app_config = self.config.get("app", {})
        app_name = app_config.get("name", "AION")
        app_version = app_config.get("version", "0.3.1")

        print(f"\n{app_name} v{app_version}")
        print("AI Agent Orchestrator Node")
        print("Tape 'help' pour voir les commandes.\n")

        self.logger.info("AION started")

        while True:
            try:
                command = input("AION> ").strip()
            except KeyboardInterrupt:
                print("\nArrêt demandé.")
                break

            if not command:
                continue

            if command in {"quit", "exit"}:
                print("Arrêt d'AION.")
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
            return f"Services rechargés : {self.registry.count()}"

        if command.startswith("info "):
            service_name = command.replace("info ", "", 1).strip()
            return self._service_info(service_name)

        if command.startswith("run "):
            service_name = command.replace("run ", "", 1).strip()
            return self.executor.execute(service_name)

        if command.startswith("remember path "):
            return self._remember_path(command)

        if command.startswith("remember "):
            return self._remember_info(command)

        if command.startswith("recall "):
            key = command.replace("recall ", "", 1).strip()
            value = self.memory.recall(key)

            if value is None:
                return f"Aucune mémoire trouvée pour : {key}"

            return f"{key} = {value}"

        if command == "memory":
            return self._list_memory()

        if command == "memory list":
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
                return f"Mémoire supprimée : {key}"

            return f"Aucune mémoire trouvée pour : {key}"

        return (
            "Commande inconnue. Essaie : help, services, run hello, "
            "run system_info, status, memory list, quit"
        )

    def _help(self) -> str:
        return """
Commandes disponibles :

help                         Affiche l'aide
services                     Liste les services disponibles
reload services              Recharge les services sans redémarrer AION
info <service>               Affiche les détails d'un service
run <service>                Lance un service
status                       Affiche le statut d'AION

Mémoire :
memory                       Liste toute la mémoire permanente
memory list                  Liste toute la mémoire permanente
memory list <type>           Liste la mémoire d'un type précis
memory show <clé>            Affiche le détail d'une mémoire
memory search <texte>        Recherche dans les clés, valeurs et types
memory stats                 Affiche les statistiques de mémoire
remember clé=valeur          Mémorise une information
remember path clé=chemin     Mémorise un chemin local existant
recall clé                   Rappelle une valeur simple
forget clé                   Supprime une mémoire

quit                         Quitte AION
""".strip()

    def _status(self) -> str:
        stats = self.memory.stats()

        return f"""
AION Status

Version : 0.3.1
Services : {self.registry.count()}
Memory : Ready
Memory items : {stats["total"]}
Temporary memory items : {stats["temporary_total"]}
Event Bus : Ready
AI : Not Connected
""".strip()

    def _list_services(self) -> str:
        services = self.registry.list_services()

        if not services:
            return "Aucun service enregistré."

        lines = ["Services disponibles :"]
        for service in services:
            lines.append(f"- {service.name}: {service.description}")

        return "\n".join(lines)

    def _service_info(self, service_name: str) -> str:
        service = self.registry.get(service_name)

        if service is None:
            return "Service introuvable."

        return f"""
Service : {service.name}

Description :
{service.description}

Permissions :
{", ".join(service.permissions) if service.permissions else "Aucune"}
""".strip()

    def _remember_info(self, command: str) -> str:
        raw = command.replace("remember ", "", 1).strip()

        if "=" not in raw:
            return "Format attendu : remember clé=valeur"

        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key or not value:
            return "La clé et la valeur sont obligatoires."

        self.memory.remember(key, value, memory_type="info")
        return f"Information mémorisée : {key}"

    def _remember_path(self, command: str) -> str:
        raw = command.replace("remember path ", "", 1).strip()

        if "=" not in raw:
            return "Format attendu : remember path clé=chemin"

        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"')

        if not key or not value:
            return "La clé et le chemin sont obligatoires."

        path = Path(value)

        if not path.exists():
            return f"Chemin introuvable : {value}"

        self.memory.remember(key, str(path), memory_type="path")
        return f"Chemin mémorisé : {key}"

    def _list_memory(self, memory_type: str | None = None) -> str:
        memory = self.memory.list_memory(memory_type=memory_type)

        if not memory:
            if memory_type:
                return f"Aucune mémoire trouvée pour le type : {memory_type}"
            return "Mémoire vide."

        title = "Mémoire AION"
        if memory_type:
            title += f" [{memory_type}]"

        lines = [f"{title} :"]

        for key, item in memory.items():
            lines.append(
                f"- {key} [{item.get('type', 'info')}] = {item.get('value')}"
            )

        return "\n".join(lines)

    def _show_memory_item(self, key: str) -> str:
        item = self.memory.get_item(key)

        if item is None:
            return f"Aucune mémoire trouvée pour : {key}"

        return f"""
Mémoire : {key}

Type : {item.get("type", "info")}
Valeur : {item.get("value")}
Créée le : {item.get("created_at", "inconnu")}
Mise à jour le : {item.get("updated_at", "inconnu")}
""".strip()

    def _search_memory(self, query: str) -> str:
        results = self.memory.search(query)

        if not results:
            return f"Aucune mémoire trouvée pour la recherche : {query}"

        lines = [f"Résultats mémoire pour : {query}"]

        for key, item in results.items():
            lines.append(
                f"- {key} [{item.get('type', 'info')}] = {item.get('value')}"
            )

        return "\n".join(lines)

    def _memory_stats(self) -> str:
        stats = self.memory.stats()

        lines = [
            "Statistiques mémoire :",
            f"- Total permanent : {stats['total']}",
            f"- Total temporaire : {stats['temporary_total']}",
            "- Par type :",
        ]

        if not stats["by_type"]:
            lines.append("  Aucun élément")
        else:
            for memory_type, count in stats["by_type"].items():
                lines.append(f"  - {memory_type}: {count}")

        return "\n".join(lines)
