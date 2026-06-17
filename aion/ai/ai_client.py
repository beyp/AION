"""
AiClient - Client IA universel pour AION.

Detecte automatiquement le backend disponible :
  1. Groq (si GROQ_API_KEY configure)      <- prioritaire, rapide, gratuit
  2. Ollama local (si ollama serve actif)  <- fallback local
  3. Aucun                                 <- message d aide

Usage transparent : meme interface que OllamaClient et GroqClient.
"""
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class AiClient:
    """
    Client IA universel — abstraction sur Groq ou Ollama.

    Choisit automatiquement le meilleur backend disponible.
    Peut etre force via config.yaml : ai.backend = "groq" | "ollama" | "auto"
    """

    def __init__(
        self,
        backend:    str  = "auto",
        groq_key:   str  = "",
        ollama_url: str  = "http://localhost:11434",
        model:      str  = "",
        timeout:    int  = 30,
    ) -> None:
        self._backend    = backend
        self._groq_key   = groq_key or os.getenv("GROQ_API_KEY", "")
        self._ollama_url = ollama_url
        self._timeout    = timeout
        self._client     = None
        self._client_type = "none"

        # Modele par defaut selon le backend
        self._model_groq   = model or "llama3-8b-8192"
        self._model_ollama = model or "mistral:latest"

        self._init_client()

    def _init_client(self) -> None:
        """Initialise le meilleur client disponible."""
        from aion.ai.groq_client   import GroqClient
        from aion.ai.ollama_client import OllamaClient

        # Forcer Groq
        if self._backend == "groq":
            self._client      = GroqClient(self._groq_key, self._model_groq, self._timeout)
            self._client_type = "groq"
            logger.info("AiClient: backend force = Groq (%s)", self._model_groq)
            return

        # Forcer Ollama
        if self._backend == "ollama":
            self._client      = OllamaClient(self._ollama_url, self._model_ollama, self._timeout)
            self._client_type = "ollama"
            logger.info("AiClient: backend force = Ollama (%s)", self._model_ollama)
            return

        # Auto : Groq en priorite si cle disponible
        if self._groq_key:
            groq = GroqClient(self._groq_key, self._model_groq, self._timeout)
            if groq.is_available():
                self._client      = groq
                self._client_type = "groq"
                logger.info("AiClient: auto -> Groq (%s)", self._model_groq)
                return
            else:
                logger.warning("AiClient: cle Groq presente mais API inaccessible")

        # Fallback Ollama
        ollama = OllamaClient(self._ollama_url, self._model_ollama, self._timeout)
        if ollama.is_available():
            self._client      = ollama
            self._client_type = "ollama"
            logger.info("AiClient: auto -> Ollama (%s)", self._model_ollama)
            return

        # Aucun backend
        self._client      = None
        self._client_type = "none"
        logger.warning("AiClient: aucun backend IA disponible")

    @property
    def model(self) -> str:
        if self._client:
            return self._client.model
        return "aucun"

    @model.setter
    def model(self, value: str) -> None:
        if self._client:
            self._client.model = value

    @property
    def backend(self) -> str:
        return self._client_type

    def is_available(self) -> bool:
        if not self._client:
            return False
        return self._client.is_available()

    def list_models(self) -> list[str]:
        if not self._client:
            return []
        return self._client.list_models()

    def chat(
        self,
        prompt:  str,
        system:  str | None = None,
        context: list[dict[str, Any]] | None = None,
    ) -> str:
        if not self._client:
            return (
                "IA non disponible.\n"
                "  Option 1 (recommande) : Groq gratuit\n"
                "    1. Cree un compte : https://console.groq.com\n"
                "    2. Cree une API key\n"
                "    3. Ajoute dans .env : GROQ_API_KEY=gsk_...\n"
                "  Option 2 : Ollama local\n"
                "    ollama serve"
            )
        return self._client.chat(prompt, system=system, context=context)

    def generate(self, prompt: str, system: str | None = None) -> str:
        if not self._client:
            return "IA non disponible."
        return self._client.generate(prompt, system=system)

    def refresh(self) -> str:
        """Reinitialise le client (utile apres ajout d une cle API)."""
        self._init_client()
        return f"AiClient: backend = {self._client_type} ({self.model})"

    def status_info(self) -> dict:
        """Retourne les infos de statut pour l affichage."""
        return {
            "backend":     self._client_type,
            "model":       self.model,
            "available":   self.is_available(),
            "groq_key":    bool(self._groq_key),
            "ollama_url":  self._ollama_url,
        }
