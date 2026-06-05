"""
Registre des domaines de services AION - avec persistance JSON.

Nomenclature : <domaine>_<action>
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DOMAINS_FILE = Path("aion/services/domains.json")

# Domaines par defaut (utilises si domains.json n existe pas)
DEFAULT_DOMAINS: dict[str, str] = {
    "net":    "Services reseau (ping, IP, status, DNS...)",
    "sys":    "Services systeme (CPU, RAM, disque, uptime...)",
    "docker": "Services Docker (conteneurs, images, volumes...)",
    "ai":     "Services IA (ollama, embeddings, generation...)",
    "fs":     "Services fichiers (backup, sync, scan...)",
    "svc":    "Services applicatifs (web, api, daemon...)",
    "demo":   "Services de demonstration et de test",
}


def _load() -> dict[str, str]:
    """Charge les domaines depuis le fichier JSON."""
    if DOMAINS_FILE.exists():
        try:
            data = json.loads(DOMAINS_FILE.read_text(encoding="utf-8"))
            logger.debug("Domains: charges depuis %s", DOMAINS_FILE)
            return data
        except Exception as exc:
            logger.error("Domains: erreur lecture %s : %s", DOMAINS_FILE, exc)
    return dict(DEFAULT_DOMAINS)


def _save(domains: dict[str, str]) -> None:
    """Sauvegarde les domaines dans le fichier JSON."""
    try:
        DOMAINS_FILE.parent.mkdir(parents=True, exist_ok=True)
        DOMAINS_FILE.write_text(
            json.dumps(domains, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.debug("Domains: sauvegardes dans %s", DOMAINS_FILE)
    except Exception as exc:
        logger.error("Domains: erreur sauvegarde : %s", exc)


# Chargement au demarrage
DOMAINS: dict[str, str] = _load()


def get_domain(service_name: str) -> str | None:
    """Extrait le domaine d un nom de service (ex: net_ping -> net)."""
    parts = service_name.split("_", 1)
    return parts[0] if len(parts) >= 2 else None


def is_valid_domain(domain: str) -> bool:
    """Verifie si un domaine est enregistre."""
    return domain in DOMAINS


def add_domain(name: str, description: str) -> bool:
    """Ajoute un domaine et le persiste. Retourne False si deja existant."""
    if name in DOMAINS:
        return False
    DOMAINS[name] = description
    _save(DOMAINS)
    logger.info("Domains: ajout '%s'", name)
    return True


def remove_domain(name: str) -> bool:
    """Supprime un domaine et persiste. Retourne False si inexistant."""
    if name not in DOMAINS:
        return False
    del DOMAINS[name]
    _save(DOMAINS)
    logger.info("Domains: suppression '%s'", name)
    return True


def list_domains() -> dict[str, str]:
    """Retourne tous les domaines enregistres."""
    return dict(DOMAINS)
