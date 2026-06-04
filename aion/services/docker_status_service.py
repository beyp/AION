"""Service de statut Docker."""
import subprocess
from typing import Any

from aion.services.base_service import BaseService


class DockerStatusService(BaseService):
    """Liste les conteneurs Docker actifs sur la machine."""

    name = "docker_status"
    description = "Liste les conteneurs Docker en cours d execution"
    permissions = ["shell"]

    def execute(self, payload: dict[str, Any]) -> str:
        try:
            result = subprocess.run(
                ["docker", "ps", "--format",
                 "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return f"Docker error : {result.stderr.strip()}"

            output = result.stdout.strip()

            if not output or output == "NAMES\tSTATUS\tPORTS":
                return "Docker : Aucun conteneur en cours d execution."

            lines = ["Docker Containers :"]
            for line in output.splitlines():
                lines.append(f"  {line}")
            return "\n".join(lines)

        except FileNotFoundError:
            return "Docker : non installe ou non accessible dans le PATH."
        except subprocess.TimeoutExpired:
            return "Docker : timeout lors de la requete."
        except Exception as exc:
            return f"Docker : erreur inattendue : {exc}"
