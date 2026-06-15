"""
CommandParser - interprete les commandes naturelles AION.

Syntaxe supportee :
    <domaine> <action> [args...] [--param valeur]

Exemples :
    ado get item 191614
    ado status change 191614 Done
    ado list
    ado list --state "In Progress" --project "PTG - TMM"
    net status
    net ping 8.8.8.8
    fs search Rapport c:\\temp
    fs search Rapport --path docs
    qm add "RDV demain 10h" --priority urgent --reminder "9:30"
    qm list
    qm list --priority urgent
    qm done 5
    sys cpu
    sys disk
    docker status
"""
import re
import shlex
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedCommand:
    """Resultat du parsing d une commande."""
    domain:     str
    action:     str
    args:       list[str]           = field(default_factory=list)
    params:     dict[str, str]      = field(default_factory=dict)
    raw:        str                 = ""
    valid:      bool                = True
    error:      str                 = ""


def parse_command(command: str) -> ParsedCommand | None:
    """
    Parse une commande AION en domaine + action + args + params.

    Retourne None si la commande n est pas une commande de domaine
    (commence par un mot connu comme domaine).
    """
    command = command.strip()
    if not command:
        return None

    # Essayer de tokeniser (gere les guillemets)
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        # Fallback si guillemets mal formes
        tokens = command.split()

    if not tokens:
        return None

    domain = tokens[0].lower()
    action_tokens = tokens[1:] if len(tokens) > 1 else []

    # Parser les arguments positionnels et les parametres --flag
    args = []
    params = {}
    i = 0
    while i < len(action_tokens):
        token = action_tokens[i]
        if token.startswith("--"):
            key = token[2:].lower()
            # Verifier si la valeur suit
            if i + 1 < len(action_tokens) and not action_tokens[i + 1].startswith("--"):
                params[key] = action_tokens[i + 1]
                i += 2
            else:
                params[key] = "true"
                i += 1
        else:
            args.append(token)
            i += 1

    action = args[0].lower() if args else ""
    positional = args[1:] if len(args) > 1 else []

    return ParsedCommand(
        domain=domain,
        action=action,
        args=positional,
        params=params,
        raw=command,
    )


# ── Aide par domaine et action ────────────────────────────────────────────────

DOMAIN_HELP: dict[str, dict[str, list[tuple[str, str]]]] = {
    "ado": {
        "_desc": "Azure DevOps - gestion des work items",
        "get": [
            ("ado get item <id>",                     "Voir les details d un work item"),
            ("ado get item 191614",                   "Exemple"),
        ],
        "status": [
            ("ado status change <id> <etat>",         "Changer le statut d un item"),
            ("ado status change 191614 Done",          "Exemple"),
            ("ado status change 191614 Done --comment \"Termine\"", "Avec commentaire"),
        ],
        "list": [
            ("ado list",                              "Lister les items (projet defaut)"),
            ("ado list --state \"In Progress\"",   "Filtrer par etat"),
            ("ado list --type Bug --state Active",    "Filtrer par type et etat"),
            ("ado list --project \"PTG - TMM\"",   "Autre projet"),
        ],
        "my": [
            ("ado my",                                "Mes items assignes"),
            ("ado my --state \"In Progress\"",     "Mes items en cours"),
        ],
        "search": [
            ("ado search <texte>",                    "Rechercher dans les titres"),
        ],
        "open": [
            ("ado open <id>",                         "Ouvrir dans le navigateur"),
        ],
        "project": [
            ("ado project \"PTG - TMM\"",           "Changer le projet par defaut"),
            ("ado project",                            "Voir le projet actif"),
        ],
    },
    "net": {
        "_desc": "Services reseau",
        "status": [("net status",              "Statut reseau complet (IP locale, publique, hostname)")],
        "ping":   [
            ("net ping",                       "Ping 8.8.8.8 (defaut)"),
            ("net ping 192.168.1.1",           "Ping un hote specifique"),
            ("net ping --host 192.168.1.1",    "Avec parametre nomme"),
        ],
        "myip":   [("net myip",               "Afficher l IP publique")],
    },
    "sys": {
        "_desc": "Services systeme",
        "cpu":    [("sys cpu",    "Utilisation CPU et RAM")],
        "disk":   [("sys disk",   "Etat des partitions disque")],
        "uptime": [("sys uptime", "Temps de fonctionnement")],
        "info":   [("sys info",   "Informations systeme (OS, Python)")],
    },
    "fs": {
        "_desc": "Services fichiers",
        "search": [
            ("fs search <mots-cles>",                       "Recherche (dossier memorise: search_dir)"),
            ("fs search Rapport 2026",                      "Exemple multi-mots"),
            ("fs search Rapport --path c:\\Users\\docs", "Chemin direct"),
            ("fs search Rapport --key docs",                "Cle memoire specifique"),
        ],
    },
    "qm": {
        "_desc": "QuickMind - gestion des taches",
        "add": [
            ("qm add <titre>",                           "Creer une tache (priorite: normal)"),
            ("qm add \"RDV 10h\"",                    "Exemple"),
            ("qm add \"RDV 10h\" --priority urgent",  "Avec priorite"),
            ("qm add \"RDV 10h\" --priority high --reminder \"09:30\"", "Avec rappel"),
            ("qm add \"RDV 10h\" --category Travail", "Avec categorie"),
        ],
        "list": [
            ("qm list",                                  "Lister les taches actives"),
            ("qm list --priority urgent",                "Filtrer par priorite"),
            ("qm list --status in_progress",             "Filtrer par statut"),
        ],
        "done": [
            ("qm done <id>",                             "Marquer une tache comme terminee"),
            ("qm done 5",                                "Exemple"),
        ],
        "health": [("qm health",                         "Verifier que QuickMind tourne")],
    },
    "docker": {
        "_desc": "Services Docker",
        "status": [("docker status", "Lister les conteneurs actifs")],
    },
    "timer": {
        "_desc": "Compte a rebours avec notification et bip",
        "5m": [
            ("timer 5m",                          "Timer de 5 minutes"),
            ("timer 25m Pause Pomodoro !",        "Timer avec message"),
            ("timer 1h30m Reunion terminee",      "Timer 1h30"),
            ("timer 90",                          "90 secondes"),
            ("timer 2:30 Temps ecoule",           "Format mm:ss"),
            ("timer 5m --beeps 5",                "Avec 5 bips de fin"),
            ("timer 5m --beeps 0",                "Sans bip"),
        ],
        "status": [
            ("timer status",                      "Lister les timers actifs"),
        ],
        "cancel": [
            ("timer cancel <id>",                 "Annuler un timer"),
            ("timer cancel timer_1",              "Exemple"),
        ],
    },
}


def get_domain_help(domain: str, action: str = "") -> str:
    """Retourne l aide pour un domaine ou une action specifique."""
    domain = domain.lower()
    action = action.lower()

    if domain not in DOMAIN_HELP:
        domains = ", ".join(DOMAIN_HELP.keys())
        return f"Domaine inconnu : {domain}\nDomaines disponibles : {domains}\nTape <domaine> ? pour l aide."

    d_help = DOMAIN_HELP[domain]
    desc   = d_help.get("_desc", "")

    if action and action in d_help:
        # Aide specifique a une action
        lines = [f"{domain} {action} — Aide :", ""]
        for cmd, explanation in d_help[action]:
            lines.append(f"  {cmd:<55} {explanation}")
        return "\n".join(lines)

    # Aide generale du domaine
    lines = [f"{domain} — {desc}", ""]
    for key, entries in d_help.items():
        if key == "_desc":
            continue
        lines.append(f"  Actions : {key}")
        for cmd, explanation in entries[:2]:  # Max 2 exemples par action
            lines.append(f"    {cmd:<53} {explanation}")
    lines.append("")
    lines.append(f"  Aide detaillee : {domain} <action> ?  (ex: {domain} {list(k for k in d_help if k != '_desc')[0]} ?)")
    return "\n".join(lines)
