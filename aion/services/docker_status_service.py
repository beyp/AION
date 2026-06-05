"""Service docker_status - conteneurs Docker."""
import subprocess
from typing import Any

from aion.services.base_service import BaseService


class DockerStatusService(BaseService):
    """Liste les conteneurs Docker actifs."""

    name = "docker_status"
    description = "Liste les conteneurs Docker en cours d execution"
    permissions = ["shell"]
    domain = "docker"

    def execute(self, payload: dict[str, Any]) -> str:
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return f"docker_status : erreur -> {result.stderr.strip()}"
            output = result.stdout.strip()
            if not output or output == "NAMES\tSTATUS\tPORTS":
                return "docker_status : aucun conteneur en cours d execution."
            lines = ["docker_status :"]
            for line in output.splitlines():
                lines.append(f"  {line}")
            return "\n".join(lines)
        except FileNotFoundError:
            return "docker_status : Docker non installe ou non accessible."
        except subprocess.TimeoutExpired:
            return "docker_status : timeout."
        except Exception as exc:
            return f"docker_status : erreur -> {exc}"
