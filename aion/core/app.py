from aion.core.config_loader import ConfigLoader
from aion.core.executor import ServiceExecutor
from aion.core.logger import setup_logger
from aion.core.registry import ServiceRegistry
from aion.memory.memory_manager import MemoryManager
from pathlib import Path

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
        app_version = app_config.get("version", "0.1.0")

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

        if command.startswith("run "):
            service_name = command.replace("run ", "", 1).strip()
            return self.executor.execute(service_name)

        if command == "status":
            return self._status()

        if command.startswith("info "):
            service_name = command.replace(
                "info ",
                "",
                1
            ).strip()

            return self._service_info(
                service_name
            )

        if command == "reload services":
            self.registry.reload_services()
            return f"Services rechargés : {self.registry.count()}"

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

        if command.startswith("forget "):
            key = command.replace("forget ", "", 1).strip()

            if self.memory.forget(key):
                return f"Mémoire supprimée : {key}"

            return f"Aucune mémoire trouvée pour : {key}"

        # else return commande inconnue
        return (
            "Commande inconnue. Essaie : help, services, run hello, "
            "run system_info, quit"
        )

    def _help(self) -> str:
        return """
Commandes disponibles :

help              Affiche l'aide
services          Liste les services disponibles
status            AION Status
info <service>    Information sur le <Service>
run hello         Lance le service hello
run system_info   Affiche des informations système
reload services   Recharge les services sans redémarrer AION
memory                         Liste la mémoire permanente
remember clé=valeur            Mémorise une information
remember path clé=chemin       Mémorise un chemin local existant
recall clé                     Rappelle une information
forget clé                     Supprime une information
quit              Quitte AION
""".strip()

    def _list_services(self) -> str:
        services = self.registry.list_services()

        if not services:
            return "Aucun service enregistré."

        lines = ["Services disponibles :"]
        for service in services:
            lines.append(f"- {service.name}: {service.description}")

        return "\n".join(lines)

    def _status(self):

        return f"""
    AION Status

    Version : 0.1.1
    Services : {self.registry.count()}
    Memory : Ready
    Event Bus : Ready
    AI : Not Connected
    """.strip()

    def _service_info(
        self,
        service_name
    ):

        service = self.registry.get(
            service_name
        )

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

    def _list_memory(self) -> str:
        memory = self.memory.list_memory()

        if not memory:
            return "Mémoire vide."

        lines = ["Mémoire AION :"]

        for key, item in memory.items():
            lines.append(
                f"- {key} [{item.get('type', 'info')}] = {item.get('value')}"
            )

        return "\n".join(lines)