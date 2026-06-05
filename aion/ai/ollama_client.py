"""Client Ollama pour AION - connexion au LLM local."""
import logging
from typing import Any, Generator

import requests

logger = logging.getLogger(__name__)

OLLAMA_DEFAULT_URL = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "llama3"


class OllamaClient:
    """
    Client HTTP pour Ollama (LLM local).

    Permet d envoyer des prompts au modele local et de recevoir
    des reponses en mode normal ou streaming.

    Usage:
        client = OllamaClient()
        if client.is_available():
            response = client.chat("Quel est l etat du reseau ?")
    """

    def __init__(
        self,
        base_url: str = OLLAMA_DEFAULT_URL,
        model: str = OLLAMA_DEFAULT_MODEL,
        timeout: int = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        """Verifie si Ollama est en cours d execution."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """Retourne la liste des modeles disponibles localement."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            logger.error("Ollama: impossible de lister les modeles: %s", exc)
            return []

    def chat(
        self,
        prompt: str,
        system: str | None = None,
        context: list[dict[str, Any]] | None = None,
    ) -> str:
        """Envoie un prompt - tente /api/chat puis fallback sur /api/generate."""

        # Tentative avec /api/chat
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": prompt})

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": False},
                timeout=self.timeout,
            )
            if response.status_code == 404:
                # Fallback sur /api/generate
                logger.warning("Ollama: /api/chat non disponible, fallback sur /api/generate")
                return self.generate(prompt, system=system)

            response.raise_for_status()
            return response.json().get("message", {}).get("content", "").strip()

        except requests.exceptions.ConnectionError:
            return "Ollama non disponible. Verifie qu Ollama est lance (ollama serve)."
        except requests.exceptions.Timeout:
            return f"Timeout : le modele {self.model} n a pas repondu en {self.timeout}s."
        except Exception as exc:
            logger.error("Ollama: erreur chat: %s", exc)
            return f"Erreur Ollama : {exc}"

    def generate(self, prompt: str, system: str | None = None) -> str:
        """
        Mode generate (sans historique) - plus rapide pour les commandes courtes.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()

        except requests.exceptions.ConnectionError:
            return "Ollama non disponible. Verifie qu Ollama est lance (ollama serve)."
        except requests.exceptions.Timeout:
            return f"Timeout : le modele {self.model} n a pas repondu en {self.timeout}s."
        except Exception as exc:
            logger.error("Ollama: erreur generate: %s", exc)
            return f"Erreur Ollama : {exc}"
