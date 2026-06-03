from aion.core.config_loader import ConfigLoader
from aion.core.executor import ServiceExecutor
from aion.core.logger import setup_logger
from aion.core.registry import ServiceRegistry


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
        self.registry.register_default_services()
        self.executor = ServiceExecutor(self.registry)

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

        return (
            "Commande inconnue. Essaie : help, services, run hello, "
            "run system_info, quit"
        )

    def _help(self) -> str:
        return """
Commandes disponibles :

help              Affiche l'aide
services          Liste les services disponibles
run hello         Lance le service hello
run system_info   Affiche des informations système
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
