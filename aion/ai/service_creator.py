"""
Service Creator AION - genere et enregistre de nouveaux services via Ollama.

Le LLM genere le code Python complet du service,
qui est ensuite valide, sauvegarde et charge dynamiquement.
"""
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from aion.ai.ollama_client import OllamaClient
from aion.services.domains import DOMAINS, is_valid_domain, add_domain

if TYPE_CHECKING:
    from aion.core.app import AionApp

logger = logging.getLogger(__name__)

SERVICE_CREATION_PROMPT = (
    "Tu es un expert Python qui cree des services pour AION.\n\n"
    "NOMENCLATURE OBLIGATOIRE : <domaine>_<action>\n"
    "Domaines disponibles :\n{domains}\n\n"
    "Tu dois generer le code Python COMPLET d un service AION valide.\n\n"
    "TEMPLATE OBLIGATOIRE :\n\n"
    '```python\n'
    '"""Service <domaine>_<action> - <description courte>."""\n'
    "from typing import Any\n"
    "# imports necessaires ici\n\n"
    "from aion.services.base_service import BaseService\n\n\n"
    "class <NomEnPascalCase>Service(BaseService):\n"
    '    """<Description complete>."""\n\n'
    '    name = "<domaine>_<action>"\n'
    '    description = "<description lisible>"\n'
    "    permissions = []\n"
    '    domain = "<domaine>"\n\n'
    "    def execute(self, payload: dict[str, Any]) -> str:\n"
    "        # implementation ici\n"
    '        return "<resultat>"\n'
    '```\n\n'
    "REGLES :\n"
    "- Le nom du fichier sera <domaine>_<action>_service.py\n"
    "- La classe doit heriter de BaseService\n"
    "- execute() doit retourner une str\n"
    "- Gerer les exceptions avec try/except\n"
    "- Commencer le retour par '<domaine>_<action> :' pour la coherence\n"
    "- Utiliser uniquement : stdlib Python, psutil, requests, pyyaml\n\n"
    "Reponds UNIQUEMENT avec le bloc de code entre ```python et ```.\n"
    "Aucun texte avant ou apres."
)


class ServiceCreator:
    """
    Cree de nouveaux services AION via le LLM Ollama.

    Workflow :
    1. L utilisateur decrit le service en langage naturel
    2. Le LLM genere le code Python complet
    3. Le code est valide (syntaxe + structure)
    4. Le fichier est sauvegarde dans aion/services/
    5. Le registry recharge automatiquement les services
    """

    SERVICES_DIR = Path("aion/services")

    def __init__(self, app: "AionApp", client: OllamaClient) -> None:
        self._app = app
        self._client = client

    def create(self, description: str, domain: str | None = None) -> str:
        """
        Cree un nouveau service a partir d une description.

        Args:
            description: Description en langage naturel du service desire.
            domain:      Domaine optionnel (si None, le LLM choisit).

        Returns:
            Message de succes ou d erreur.
        """
        logger.info("ServiceCreator: creation demandee : %s", description)

        # Valider le domaine si fourni
        if domain and not is_valid_domain(domain):
            return (
                f"Domaine inconnu : {domain}\n"
                f"Domaines disponibles : {', '.join(DOMAINS.keys())}\n"
                f"Pour ajouter un domaine : domain add <nom> <description>"
            )

        # Construire le prompt
        domains_list = "\n".join(
            f"  - {k}: {v}" for k, v in DOMAINS.items()
        )
        domain_hint = f"\nDomaine prefere : {domain}" if domain else ""
        full_prompt = (
            f"Cree un service AION pour : {description}{domain_hint}\n\n"
            f"Choisis le domaine et l action les plus appropries."
        )

        # Appel LLM
        system = SERVICE_CREATION_PROMPT.format(domains=domains_list)
        raw_code = self._client.generate(full_prompt, system=system)

        # Extraire le code du bloc markdown
        code = self._extract_code(raw_code)
        if not code:
            return "Le LLM n a pas genere de code valide. Reessaie avec une description plus precise."

        # Valider la syntaxe
        validation_error = self._validate_code(code)
        if validation_error:
            return f"Code genere invalide : {validation_error}"

        # Extraire le nom du service
        service_name = self._extract_service_name(code)
        if not service_name:
            return "Impossible d extraire le nom du service depuis le code genere."

        # Sauvegarder le fichier
        filename = f"{service_name}_service.py"
        filepath = self.SERVICES_DIR / filename

        if filepath.exists():
            return (
                f"Un service {service_name} existe deja.\n"
                f"Fichier : {filepath}"
            )

        try:
            filepath.write_text(code, encoding="utf-8")
            logger.info("ServiceCreator: fichier cree : %s", filepath)
        except Exception as exc:
            return f"Erreur lors de la sauvegarde : {exc}"

        # Recharger les services
        try:
            self._app.registry.reload_services()
            logger.info("ServiceCreator: services recharges")
        except Exception as exc:
            return (
                f"Service sauvegarde ({filepath}) mais erreur au chargement : {exc}\n"
                f"Essaie : reload services"
            )

        return (
            f"✅ Service cree avec succes !\n"
            f"  Nom     : {service_name}\n"
            f"  Fichier : {filepath}\n"
            f"  Test    : run {service_name}\n\n"
            f"--- Code genere ---\n{code}"
        )

    def _extract_code(self, raw: str) -> str:
        """Extrait le code Python du bloc markdown."""
        # Chercher ```python ... ```
        match = re.search(r"```python\s*\n(.*?)```", raw, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Fallback : chercher ``` ... ```
        match = re.search(r"```\s*\n(.*?)```", raw, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Fallback : retourner le raw si ca ressemble a du Python
        if "class" in raw and "BaseService" in raw:
            return raw.strip()
        return ""

    def _validate_code(self, code: str) -> str | None:
        """Valide la syntaxe Python et la structure du service."""
        # Validation syntaxe
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as exc:
            return f"Erreur de syntaxe : {exc}"

        # Validation structure minimale
        checks = [
            ("BaseService", "Le service doit heriter de BaseService"),
            ("def execute(", "Le service doit implementer execute()"),
            ('name = "', "Le service doit avoir un attribut name"),
            ("domain = ", "Le service doit avoir un attribut domain"),
        ]
        for pattern, message in checks:
            if pattern not in code:
                return message

        return None

    def _extract_service_name(self, code: str) -> str | None:
        """Extrait le nom du service depuis le code."""
        match = re.search(r'name\s*=\s*["\'](\w+)["\']', code)
        if match:
            return match.group(1)
        return None
