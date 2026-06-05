"""Agent IA AION - interprete le langage naturel et execute des commandes."""
import logging
from typing import TYPE_CHECKING

from aion.ai.ollama_client import OllamaClient
from aion.ai.service_creator import ServiceCreator
from aion.services.domains import DOMAINS

if TYPE_CHECKING:
    from aion.core.app import AionApp

logger = logging.getLogger(__name__)


def _build_system_prompt(services: list[str]) -> str:
    """Construit le prompt systeme dynamiquement avec les services reels."""
    domains_list = "\n".join(f"  - {k}: {v}" for k, v in DOMAINS.items())
    services_list = ", ".join(services)

    return f"""Tu es AION, un assistant IA local d orchestration systeme.
Tu aides l utilisateur a gerer son environnement informatique en francais.

NOMENCLATURE DES SERVICES : <domaine>_<action>
Domaines disponibles :
{domains_list}

SERVICES DISPONIBLES (utilise exactement ces noms) :
{services_list}

COMMANDES DISPONIBLES :
- run <service>                  : executer un service (utilise le nom exact)
- services                       : lister les services
- status                         : statut general d AION
- memory                         : lister la memoire
- remember cle=valeur            : memoriser une information
- recall cle                     : rappeler une valeur
- scheduler                      : voir les jobs planifies
- schedule <service> every <N>s  : planifier un service
- notify on / notify off         : activer/desactiver les notifications
- domain add <nom> <description> : ajouter un nouveau domaine

CREATION DE SERVICE :
- Si l utilisateur veut un nouveau service qui n existe pas :
  AION_CREATE: <description du service en francais>
  ou avec domaine specifique :
  AION_CREATE_DOMAIN:<domaine>: <description>

REGLES STRICTES :
1. Reponds toujours en francais, brievement (1-3 phrases max)
2. Pour executer un service : AION_CMD: run <nom_exact>
3. AION_CMD doit TOUJOURS etre sur sa propre ligne separee
4. Utilise le nom EXACT du service tel que liste ci-dessus
5. Ne fabrique jamais de donnees - utilise les commandes
6. Si le service n existe pas, propose de le creer avec AION_CREATE

Exemples corrects :
  Je vais verifier votre reseau.
  AION_CMD: run net_status

  Je vais creer ce service pour vous.
  AION_CREATE: service qui surveille la temperature CPU

Sois concis, utile et professionnel."""


class AionAgent:
    """
    Agent IA pour AION.

    Interprete les requetes en langage naturel,
    genere une reponse, execute la commande AION appropriee
    ou cree un nouveau service si necessaire.
    """

    def __init__(self, app: "AionApp", client: OllamaClient) -> None:
        self._app = app
        self._client = client
        self._creator = ServiceCreator(app, client)
        self._history: list[dict[str, str]] = []
        self._max_history = 10

    def ask(self, user_input: str) -> str:
        """Traite une question en langage naturel."""
        logger.info("Agent: user input: %s", user_input)

        # Prompt systeme dynamique avec les vrais noms de services
        services = [s.name for s in self._app.registry.list_services()]
        system_prompt = _build_system_prompt(services)

        # Contexte AION courant
        context_info = self._build_context()
        enriched_prompt = f"{context_info}\n\nUtilisateur: {user_input}"

        # Appel Ollama
        llm_response = self._client.chat(
            prompt=enriched_prompt,
            system=system_prompt,
            context=self._history[-self._max_history:] if self._history else None,
        )

        # Historique
        self._history.append({"role": "user", "content": user_input})
        self._history.append({"role": "assistant", "content": llm_response})

        return self._parse_and_execute(llm_response)

    def _build_context(self) -> str:
        """Construit un contexte textuel de l etat AION."""
        try:
            services = [s.name for s in self._app.registry.list_services()]
            jobs = list(self._app.scheduler.list_jobs().keys())
            mem_count = self._app.memory.stats()["total"]
            sched_state = "Running" if self._app.scheduler.is_running() else "Stopped"
            return (
                f"[Contexte AION]\n"
                f"Services : {', '.join(services)}\n"
                f"Jobs planifies : {', '.join(jobs) if jobs else 'aucun'}\n"
                f"Memoire : {mem_count} elements\n"
                f"Scheduler : {sched_state}"
            )
        except Exception:
            return "[Contexte AION indisponible]"

    def _parse_and_execute(self, llm_response: str) -> str:
        """Parse la reponse LLM et execute les directives."""
        lines = llm_response.strip().splitlines()
        aion_cmd = None
        aion_create = None
        aion_create_domain = None
        text_lines = []

        for line in lines:
            stripped = line.strip()

            # Nettoyer les underscores echappes par Mistral
            stripped = stripped.replace("\_", "_")

            if stripped.startswith("AION_CMD:"):
                aion_cmd = stripped.replace("AION_CMD:", "", 1).strip()
            elif stripped.startswith("AION_CREATE_DOMAIN:"):
                # Format : AION_CREATE_DOMAIN:<domaine>: <description>
                rest = stripped.replace("AION_CREATE_DOMAIN:", "", 1).strip()
                if ":" in rest:
                    aion_create_domain, aion_create = rest.split(":", 1)
                    aion_create_domain = aion_create_domain.strip()
                    aion_create = aion_create.strip()
                else:
                    aion_create = rest
            elif stripped.startswith("AION_CREATE:"):
                aion_create = stripped.replace("AION_CREATE:", "", 1).strip()
            else:
                text_lines.append(line.replace("\\_", "_"))

        text_response = "\n".join(text_lines).strip()
        output_parts = []

        if text_response:
            output_parts.append(f"🤖 {text_response}")

        # Executer une commande AION
        if aion_cmd:
            aion_cmd = aion_cmd.replace("\\_", "_")

            # Auto-correction : ajouter "run " si c est un nom de service connu
            known = [s.name for s in self._app.registry.list_services()]
            if aion_cmd in known:
                aion_cmd = f"run {aion_cmd}"

            logger.info("Agent: executing command: %s", aion_cmd)
            output_parts.append(f"\n⚡ Execution : {aion_cmd}")
            cmd_result = self._app.handle_command(aion_cmd)
            output_parts.append(cmd_result)

        # Creer un nouveau service
        if aion_create:
            logger.info("Agent: creating service: %s", aion_create)
            output_parts.append(f"\n🔧 Creation de service : {aion_create}")
            create_result = self._creator.create(
                description=aion_create,
                domain=aion_create_domain,
            )
            output_parts.append(create_result)

        return "\n".join(output_parts) if output_parts else llm_response

    def clear_history(self) -> None:
        """Efface l historique de conversation."""
        self._history.clear()
        logger.info("Agent: historique efface")

    def history_count(self) -> int:
        """Retourne le nombre de messages dans l historique."""
        return len(self._history)
