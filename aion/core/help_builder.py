"""
HelpBuilder - genere le help AION dynamiquement.

Le help est construit a partir de :
1. Les commandes statiques (noyau AION)
2. Les services enregistres (auto-discovers)
3. Les domaines enregistres
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aion.core.registry import ServiceRegistry
    from aion.services.domains import DOMAINS


# Commandes statiques du noyau AION
STATIC_COMMANDS: list[tuple[str, str, str]] = [
    # (categorie, commande, description)
    # ── Core ──────────────────────────────────────────────────────────────────
    ("Core",    "help",                           "Affiche ce message d aide"),
    ("Core",    "status",                         "Statut general d AION"),
    ("Core",    "services",                       "Liste les services disponibles"),
    ("Core",    "domains",                        "Liste les domaines de services"),
    ("Core",    "reload services",                "Recharge les services sans redemarrer"),
    ("Core",    "info <service>",                 "Details d un service"),
    ("Core",    "run <service>",                  "Execute un service"),
    ("Core",    "create service <description>",   "Cree un nouveau service via IA"),
    ("Core",    "quit / exit",                    "Quitte AION"),
    # ── Domaines ──────────────────────────────────────────────────────────────
    ("Domains", "domain add <nom> <desc>",        "Ajouter un domaine"),
    ("Domains", "domain remove <nom>",            "Supprimer un domaine"),
    # ── Memoire ───────────────────────────────────────────────────────────────
    ("Memory",  "memory",                         "Lister toute la memoire"),
    ("Memory",  "memory list [type]",             "Filtrer par type"),
    ("Memory",  "memory show <cle>",              "Detail d un element"),
    ("Memory",  "memory search <texte>",          "Recherche dans la memoire"),
    ("Memory",  "memory stats",                   "Statistiques memoire"),
    ("Memory",  "remember <cle>=<valeur>",        "Memoriser une information"),
    ("Memory",  "remember path <cle>=<chemin>",   "Memoriser un chemin local"),
    ("Memory",  "recall <cle>",                   "Lire une valeur"),
    ("Memory",  "forget <cle>",                   "Supprimer une entree"),
    # ── EventBus ──────────────────────────────────────────────────────────────
    ("Events",  "events",                         "Lister les evenements actifs"),
    # ── Scheduler ─────────────────────────────────────────────────────────────
    ("Scheduler", "scheduler",                    "Statut du planificateur"),
    ("Scheduler", "schedule <svc> every <N>s",    "Planifier un service"),
    ("Scheduler", "unschedule <job_id>",          "Supprimer un job"),
    ("Scheduler", "pause job <job_id>",           "Mettre un job en pause"),
    ("Scheduler", "resume job <job_id>",          "Reprendre un job"),
    # ── Notifications ─────────────────────────────────────────────────────────
    ("Notify",  "notify on",                      "Activer les notifications"),
    ("Notify",  "notify off",                     "Desactiver les notifications"),
    ("Notify",  "notify status",                  "Etat des notifications"),
    ("Notify",  "notify test",                    "Envoyer une notification test"),
    # ── IA Ollama ─────────────────────────────────────────────────────────────
    ("AI",      "ai",                             "Entrer en mode conversation IA"),
    ("AI",      "ask <question>",                 "Question one-shot a l IA"),
    ("AI",      "ai status",                      "Etat de la connexion Ollama"),
    ("AI",      "ai models",                      "Lister les modeles disponibles"),
    ("AI",      "ai model <nom>",                 "Changer de modele"),
    # ── API & Dashboard ───────────────────────────────────────────────────────
    ("API",     "api start",                      "Demarrer le serveur API (port 8000)"),
    ("API",     "  -> Dashboard",                 "http://127.0.0.1:8000/dashboard"),
    ("API",     "  -> Swagger",                   "http://127.0.0.1:8000/docs"),
    # ── ADO (Azur DevOps)──────────────────────────────────────────────────────
    ("ADO",  "ado get item <id>",             "Voir un work item"),
    ("ADO",  "ado status change <id> <etat>", "Changer le statut"),
    ("ADO",  "ado list [--state <etat>]",     "Lister les items"),
    # ── NET (Network)──────────────────────────────────────────────────────
    ("NET",  "net status",                    "Statut reseau complet"),
    # ── SYS (System)──────────────────────────────────────────────────────
    ("SYS",  "sys cpu / disk / uptime",       "Monitoring systeme"),
    # ── FS0 (File Search)──────────────────────────────────────────────────────
    ("FS",   "fs search <mots> --key <cle>",  "Rechercher des fichiers"),
    ("FS",   "fs open/edit <n>",              "Ouvrir le fichier #n"),
    # ── QM (QuickMind)──────────────────────────────────────────────────────
    ("QM",   "qm add/list/done",              "Gestion QuickMind"),
    ]


def build_help(registry: "ServiceRegistry | None" = None) -> str:
    """
    Genere le texte d aide complet d AION.

    Args:
        registry: ServiceRegistry optionnel pour inclure les services.
    """
    lines = []
    col_w = 36  # largeur colonne commande

    # ── En-tete ───────────────────────────────────────────────────────────────
    lines.append("Commandes AION disponibles :")
    lines.append("")

    # ── Commandes statiques groupees par categorie ────────────────────────────
    current_cat = None
    for cat, cmd, desc in STATIC_COMMANDS:
        if cat != current_cat:
            if current_cat is not None:
                lines.append("")
            lines.append(f"{cat} :")
            current_cat = cat
        lines.append(f"  {cmd:<{col_w}} {desc}")

    # ── Services dynamiques ───────────────────────────────────────────────────
    if registry is not None:
        services = registry.list_services()
        if services:
            lines.append("")
            lines.append("Services disponibles (run <nom>) :")

            # Grouper par domaine
            try:
                from aion.services.domains import get_domain, DOMAINS as DOM
                grouped: dict[str, list] = {}
                for s in services:
                    domain = get_domain(s.name) or "other"
                    grouped.setdefault(domain, []).append(s)

                for domain, svcs in sorted(grouped.items()):
                    dom_desc = DOM.get(domain, "")
                    lines.append(f"  [{domain}]  {dom_desc}")
                    for s in svcs:
                        lines.append(f"    run {s.name:<{col_w-4}} {s.description}")
            except Exception:
                for s in services:
                    lines.append(f"  run {s.name:<{col_w-4}} {s.description}")

    lines.append("")
    lines.append("Astuce : tape le debut d une commande + Tab pour l autocompletion (dashboard).")

    return "\n".join(lines)


def build_help_html(registry: "ServiceRegistry | None" = None) -> str:
    """Version HTML du help pour le dashboard."""
    import html as h

    lines = build_help(registry).splitlines()
    html_parts = ["<div style=\"font-family: monospace; font-size:0.83rem;\">"]

    for line in lines:
        if not line:
            html_parts.append("<br>")
        elif line.endswith(":") and not line.startswith(" "):
            # Titre de categorie
            safe = h.escape(line)
            html_parts.append(
                f'<div style="color:var(--accent); font-weight:600; margin-top:8px;">{safe}</div>'
            )
        elif line.startswith("  run "):
            # Commande run — mettre le nom en couleur
            parts = line.strip().split(None, 2)
            if len(parts) >= 2:
                svc_name = parts[1]
                desc = parts[2] if len(parts) > 2 else ""
                safe_svc  = h.escape(svc_name)
                safe_desc = h.escape(desc)
                html_parts.append(
                    f'<div style="padding:1px 12px;">'
                    f'<span style="color:var(--accent2);">run {safe_svc:<30}</span>'
                    f'<span style="color:var(--text-dim);"> {safe_desc}</span>'
                    f'</div>'
                )
        elif line.startswith("  ["):
            # Label domaine
            safe = h.escape(line)
            html_parts.append(
                f'<div style="color:var(--orange); padding:2px 12px; margin-top:4px;">{safe}</div>'
            )
        elif line.startswith("  "):
            # Commande normale
            parts = line.strip().split(None, 1) if "  " in line.strip() else [line.strip(), ""]
            # Trouver la description (apres les espaces)
            stripped = line.strip()
            # Chercher position apres la commande
            cmd_end = max(stripped.find("  "), len(stripped))
            cmd_part = stripped[:cmd_end].strip()
            desc_part = stripped[cmd_end:].strip()
            safe_cmd  = h.escape(cmd_part)
            safe_desc = h.escape(desc_part)
            html_parts.append(
                f'<div style="padding:1px 12px;">'
                f'<span style="color:var(--text);">{safe_cmd:<35}</span>'
                f'<span style="color:var(--text-dim);"> {safe_desc}</span>'
                f'</div>'
            )
        else:
            safe = h.escape(line)
            html_parts.append(
                f'<div style="color:var(--text-dim); font-style:italic; margin-top:8px; padding:0 12px;">{safe}</div>'
            )

    html_parts.append("</div>")
    return "\n".join(html_parts)
