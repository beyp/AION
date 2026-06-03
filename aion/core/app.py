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
        self.registry.discover_services()
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

