"""Client Groq pour AION - LLM cloud ultra-rapide et gratuit."""
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

GROQ_API_URL    = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_MODEL = "llama3-8b-8192"

# Modeles disponibles sur Groq (gratuit)
GROQ_MODELS = {
    "llama3-8b-8192":        "Llama 3 8B  — rapide, usage general",
    "llama3-70b-8192":       "Llama 3 70B — plus puissant",
    "mixtral-8x7b-32768":    "Mixtral 8x7B — contexte long (32K)",
    "gemma2-9b-it":          "Gemma 2 9B  — Google",
    "llama-3.1-8b-instant":  "Llama 3.1 8B instant — le plus rapide",
}


class GroqClient:
    """
    Client HTTP pour l API Groq (LLM cloud, gratuit jusqu a 14400 req/jour).

    Compatible avec la meme interface qu OllamaClient pour faciliter
    le remplacement transparent dans AionAgent.

    Usage:
        client = GroqClient(api_key="gsk_...")
        if client.is_available():
            response = client.chat("Quel est l etat du reseau ?")
    """

    def __init__(
        self,
        api_key: str = "",
        model:   str = GROQ_DEFAULT_MODEL,
        timeout: int = 30,
    ) -> None:
        self.api_key  = api_key
        self.model    = model
        self.timeout  = timeout
        self.base_url = GROQ_API_URL

    def is_available(self) -> bool:
        """Verifie si la cle API est configuree et si Groq repond."""
        if not self.api_key:
            return False
        try:
            r = requests.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=5,
            )
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """Retourne les modeles Groq disponibles."""
        try:
            r = requests.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=5,
            )
            r.raise_for_status()
            data = r.json()
            return [m["id"] for m in data.get("data", [])
                    if not m.get("id", "").startswith("whisper")]
        except Exception as exc:
            logger.error("Groq: impossible de lister les modeles: %s", exc)
            return list(GROQ_MODELS.keys())

    def chat(
        self,
        prompt:  str,
        system:  str | None = None,
        context: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Envoie un prompt a Groq et retourne la reponse.

        Compatible avec l interface OllamaClient.chat().
        """
        if not self.api_key:
            return "Groq : cle API non configuree. Ajoute GROQ_API_KEY dans .env"

        messages = []
        if system:
            messages.append({"role": "system", "content": system})

        # Filtrer le contexte : Groq accepte seulement user/assistant
        # et le contenu doit etre une string non vide
        if context:
            for msg in context:
                role    = msg.get("role", "")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content and content.strip():
                    messages.append({"role": role, "content": str(content)})

        # S assurer que le prompt n est pas vide
        prompt_clean = prompt.strip() if prompt else "?"
        messages.append({"role": "user", "content": prompt_clean})

        # Groq : alterner user/assistant obligatoire
        # Verifier qu on ne commence pas par assistant
        if messages and messages[0].get("role") == "assistant":
            messages = [m for m in messages if m.get("role") != "assistant"][:1] + messages

        payload = {
            "model":       self.model,
            "messages":    messages,
            "temperature": 0.7,
            "max_tokens":  1024,
        }

        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()

        except requests.exceptions.ConnectionError:
            return "Groq : impossible de joindre api.groq.com. Verifie ta connexion."
        except requests.exceptions.Timeout:
            return f"Groq : timeout ({self.timeout}s). Reessaie."
        except requests.exceptions.HTTPError as exc:
            if r.status_code == 401:
                return "Groq : cle API invalide. Verifie GROQ_API_KEY dans .env"
            if r.status_code == 429:
                return "Groq : quota depasse. Attends quelques secondes."
            # Afficher le detail de l erreur pour debug
            try:
                err_detail = r.json().get("error", {}).get("message", str(exc))
            except Exception:
                err_detail = str(exc)
            logger.error("Groq 400 detail: %s", err_detail)
            return f"Groq : erreur HTTP {r.status_code} : {err_detail}"
        except Exception as exc:
            logger.error("Groq: erreur chat: %s", exc)
            return f"Groq : erreur -> {exc}"

    def generate(self, prompt: str, system: str | None = None) -> str:
        """Mode generate — alias de chat() pour compatibilite OllamaClient."""
        return self.chat(prompt, system=system)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }
