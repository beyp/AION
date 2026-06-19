"""Dashboard AION v2 - Sidebar + Console + Domain Router."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# Charger le .env pour GROQ_API_KEY, ADO_PAT etc.
try:
    from dotenv import load_dotenv
    # Chercher le .env dans le répertoire du projet AION
    _env_path = Path(__file__).parent.parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
    else:
        load_dotenv()  # chercher dans le répertoire courant
except ImportError:
    pass  # python-dotenv optionnel

from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from aion.core.config_loader import ConfigLoader
from aion.core.domain_router import DomainRouter
from aion.core.executor import ServiceExecutor
from aion.core.registry import ServiceRegistry
from aion.core.scheduler import AionScheduler
from aion.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates     = Jinja2Templates(directory=str(TEMPLATES_DIR))

registry  = ServiceRegistry()
executor  = ServiceExecutor(registry)
# Ne pas instancier memory globalement — recharger depuis disque a chaque requete
# pour rester synchronise avec la console standard AION
def fresh_mem() -> MemoryManager:
    """Retourne une instance fraiche de MemoryManager (lit memory.json)."""
    return MemoryManager()
scheduler = AionScheduler()
config    = ConfigLoader().load()


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.discover_services()
    scheduler.start()
    logger.info("AION Dashboard started")
    yield
    scheduler.stop()
    logger.info("AION Dashboard stopped")


app = FastAPI(
    title="AION Dashboard",
    version=config.get("app", {}).get("version", "0.7.2"),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Page principale ───────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "version":  config.get("app", {}).get("version", "0.7.2"),
            "app_name": config.get("app", {}).get("name", "AION"),
        },
    )


# ── Sections ─────────────────────────────────────────────────────────────────

@app.get("/section/status", response_class=HTMLResponse)
async def section_status(request: Request):
    mem_stats = fresh_mem().stats()
    jobs = scheduler.list_jobs()
    jobs_with_state = {
        jid: {**info, "state": scheduler.get_job_state(jid)}
        for jid, info in jobs.items()
    }
    return templates.TemplateResponse(
        request=request,
        name="sections/status.html",
        context={
            "version":           config.get("app", {}).get("version", "0.7.2"),
            "service_count":     registry.count(),
            "memory_stats":      mem_stats,
            "scheduler_running": scheduler.is_running(),
            "jobs":              jobs_with_state,
            "job_count":         scheduler.job_count(),
        },
    )


@app.get("/section/services", response_class=HTMLResponse)
async def section_services(request: Request):
    from aion.services.domains import get_domain
    services = registry.list_services()
    grouped: dict[str, list] = {}
    for s in services:
        domain = get_domain(s.name) or "other"
        grouped.setdefault(domain, []).append(s)
    return templates.TemplateResponse(
        request=request,
        name="sections/services.html",
        context={
            "services":      services,
            "grouped":       grouped,
            "service_count": registry.count(),
        },
    )


@app.get("/section/scheduler", response_class=HTMLResponse)
async def section_scheduler(request: Request):
    jobs = scheduler.list_jobs()
    jobs_with_state = {
        jid: {**info, "state": scheduler.get_job_state(jid)}
        for jid, info in jobs.items()
    }
    return templates.TemplateResponse(
        request=request,
        name="sections/scheduler.html",
        context={
            "jobs":              jobs_with_state,
            "job_count":         scheduler.job_count(),
            "scheduler_running": scheduler.is_running(),
            "services":          [s.name for s in registry.list_services()],
        },
    )


@app.get("/section/memory", response_class=HTMLResponse)
async def section_memory(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="sections/memory.html",
        context={
            "items":        fresh_mem().list_memory(),
            "memory_stats": fresh_mem().stats(),
        },
    )


@app.get("/section/network", response_class=HTMLResponse)
async def section_network(request: Request):
    return templates.TemplateResponse(
        request=request, name="sections/network.html", context={},
    )


@app.get("/section/system", response_class=HTMLResponse)
async def section_system(request: Request):
    return templates.TemplateResponse(
        request=request, name="sections/system.html", context={},
    )


@app.get("/section/docker", response_class=HTMLResponse)
async def section_docker(request: Request):
    return templates.TemplateResponse(
        request=request, name="sections/docker.html", context={},
    )


@app.get("/section/quickmind", response_class=HTMLResponse)
async def section_quickmind(request: Request):
    import requests as req
    tasks, qm_online = [], False
    try:
        r = req.get("http://localhost:8765/tasks", timeout=3)
        if r.status_code == 200:
            tasks, qm_online = r.json(), True
    except Exception:
        pass
    return templates.TemplateResponse(
        request=request,
        name="sections/quickmind.html",
        context={
            "tasks":      tasks[:20],
            "qm_online":  qm_online,
            "task_count": len(tasks),
        },
    )


@app.get("/section/ado", response_class=HTMLResponse)
async def section_ado(request: Request):
    return templates.TemplateResponse(
        request=request, name="sections/ado.html", context={},
    )


@app.get("/section/fs_search", response_class=HTMLResponse)
async def section_fs_search(request: Request):
    # Recharger la memoire depuis le disque a chaque appel
    # pour prendre en compte les nouvelles cles ajoutees depuis la console
    from aion.memory.memory_manager import MemoryManager
    path_items = fresh_mem().list_memory(memory_type="path")
    path_keys    = [
        {"key": k, "value": v.get("value", "")}
        for k, v in path_items.items()
    ]
    logger.info("fs_search: %d cle(s) path trouvee(s): %s",
                len(path_keys), [p["key"] for p in path_keys])
    return templates.TemplateResponse(
        request=request,
        name="sections/fs_search.html",
        context={"path_keys": path_keys},
    )


@app.get("/section/timer", response_class=HTMLResponse)
async def section_timer(request: Request):
    return templates.TemplateResponse(
        request=request, name="sections/timer.html", context={},
    )


@app.get("/section/help", response_class=HTMLResponse)
async def section_help(request: Request):
    from aion.core.help_builder import build_help_html
    return templates.TemplateResponse(
        request=request,
        name="sections/help.html",
        context={"help_html": build_help_html(registry)},
    )


@app.get("/section/console", response_class=HTMLResponse)
async def section_console(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="sections/console.html",
        context={"services": [s.name for s in registry.list_services()]},
    )


# ── Run service ───────────────────────────────────────────────────────────────

@app.post("/run/{service_name}", response_class=HTMLResponse)
async def run_service(service_name: str):
    import html as h
    result = executor.execute(service_name, {})
    return HTMLResponse(f'<pre class="cmd-result">{h.escape(result)}</pre>')


# ── Console ───────────────────────────────────────────────────────────────────

@app.post("/console/run", response_class=HTMLResponse)
async def console_run(command: str = Form(...)):
    """Execute une commande AION depuis la console web."""
    import html as h
    cmd = command.strip()
    if not cmd:
        return HTMLResponse("")

    result = _handle_console_command(cmd)

    safe_cmd    = h.escape(cmd)
    safe_result = h.escape(result)
    return HTMLResponse(
        f'<div class="console-line">'
        f'<span class="console-prompt">AION&gt;</span> '
        f'<span class="console-cmd">{safe_cmd}</span>'
        f'</div>'
        f'<div class="console-output">{safe_result}</div>'
    )


def _handle_console_command(cmd: str) -> str:
    """Traite une commande console — domain router + commandes core."""

    # ── 1. Domain Router ──────────────────────────────────────────────────────
    dr = DomainRouter(executor, fresh_mem())
    if dr.can_handle(cmd):
        result = dr.dispatch(cmd)
        if result is not None:
            return result

    # ── 2. Commandes core ─────────────────────────────────────────────────────
    if cmd.startswith("run "):
        import json as _json
        parts        = cmd.replace("run ", "", 1).strip().split(" ", 1)
        service_name = parts[0]
        payload      = {}
        if len(parts) > 1:
            arg = parts[1].strip()
            if arg.startswith("{"):
                try:    payload = _json.loads(arg)
                except: return f"Payload JSON invalide : {arg}"
            elif arg.isdigit():
                payload = {"item_id": int(arg)}
            else:
                payload = {"keywords": arg}
        return executor.execute(service_name, payload)

    if cmd == "services":
        svcs = registry.list_services()
        return "\n".join(f"  - {s.name}: {s.description}" for s in svcs)

    if cmd == "status":
        stats = fresh_mem().stats()
        return (
            f"Version   : {config.get('app', {}).get('version', '?')}\n"
            f"Services  : {registry.count()}\n"
            f"Memory    : {stats['total']} items\n"
            f"Scheduler : {'Running' if scheduler.is_running() else 'Stopped'} "
            f"({scheduler.job_count()} jobs)"
        )

    if cmd == "scheduler":
        jobs = scheduler.list_jobs()
        if not jobs:
            return "Aucun job planifie."
        lines = []
        for jid, info in jobs.items():
            state = scheduler.get_job_state(jid)
            icon  = "⏸" if state == "paused" else "▶"
            lines.append(f"  {icon} {jid} (toutes les {info['interval_seconds']}s)")
        return "\n".join(lines)

    if cmd == "memory":
        items = fresh_mem().list_memory()
        if not items:
            return "Memoire vide."
        return "\n".join(
            f"  {k} [{v.get('type')}] = {v.get('value')}"
            for k, v in items.items()
        )

    if cmd.startswith("remember ") and "=" in cmd:
        raw = cmd.replace("remember ", "", 1)
        key, val = raw.split("=", 1)
        fresh_mem().remember(key.strip(), val.strip())
        return f"Memorise : {key.strip()}"

    if cmd.startswith("recall "):
        key = cmd.replace("recall ", "", 1).strip()
        val = fresh_mem().recall(key)
        return f"{key} = {val}" if val else f"Aucune memoire pour : {key}"

    if cmd.startswith("schedule ") and " every " in cmd:
        parts = cmd.replace("schedule ", "", 1).split(" every ")
        svc_name = parts[0].strip()
        try:
            interval = int(parts[1].strip().rstrip("s"))
            svc = registry.get(svc_name)
            if svc is None:
                return f"Service inconnu : {svc_name}"
            job_id = f"scheduled_{svc_name}"
            _exec = executor
            def run(): _exec.execute(svc_name, {})
            scheduler.add_job(job_id, run, interval_seconds=interval)
            return f"Job planifie : {job_id} (toutes les {interval}s)"
        except Exception as exc:
            return f"Erreur : {exc}"

    if cmd.startswith("unschedule "):
        jid = cmd.replace("unschedule ", "", 1).strip()
        scheduler.remove_job(jid)
        return f"Job supprime : {jid}"

    if cmd == "reload":
        registry.reload_services()
        return f"Services recharges : {registry.count()}"

    if cmd == "shortcuts":
        return dr.all_shortcuts()

    if cmd == "domains":
        from aion.services.domains import list_domains
        domains = list_domains()
        lines = [f"Domaines AION ({len(domains)}) :"]
        for name, desc in domains.items():
            lines.append(f"  - {name:<12} : {desc}")
        return "\n".join(lines)

    if cmd == "help":
        return (
            "Commandes core :\n"
            "  run <service>                 Executer un service\n"
            "  services                      Lister les services\n"
            "  status                        Statut AION\n"
            "  scheduler                     Jobs planifies\n"
            "  schedule <svc> every <N>s     Planifier\n"
            "  unschedule <job_id>           Supprimer un job\n"
            "  memory                        Lister la memoire\n"
            "  remember cle=valeur           Memoriser\n"
            "  recall cle                    Lire\n"
            "  domains                       Lister les domaines\n"
            "  shortcuts                     Raccourcis par domaine\n"
            "  reload                        Recharger les services\n"
            "\nRaccourcis par domaine :\n"
            "  ado get item <id>             Voir un work item\n"
            "  ado status change <id> <etat> Changer statut\n"
            "  ado list                      Lister les items\n"
            "  ado my                        Mes items\n"
            "  ado ?                         Aide ADO\n"
            "  net status / net ping / net myip\n"
            "  sys cpu / sys disk / sys uptime\n"
            "  fs search <mots> [--path dir]\n"
            "  qm add <titre> / qm list / qm done <id>\n"
            "  docker status"
        )

    return f"Commande inconnue : {cmd}\nTape \'help\' ou \'<domaine> ?\' pour l aide."


# ── FS ────────────────────────────────────────────────────────────────────────

@app.post("/fs/search", response_class=HTMLResponse)
async def fs_search(request: Request):
    import html as h
    body       = await request.json()
    keywords   = body.get("keywords", "")
    directory  = body.get("directory", "")
    memory_key = body.get("memory_key", "search_dir")

    result = executor.execute("fs_search", {
        "keywords":   keywords,
        "directory":  directory,
        "memory_key": memory_key,
    })

    lines      = result.splitlines()
    html_parts = []
    ext_icons  = {
        "pdf": "📕", "doc": "📘", "docx": "📘", "xls": "📗", "xlsx": "📗",
        "ppt": "📙", "pptx": "📙", "txt": "📄", "py": "🐍",
        "zip": "📦", "jpg": "🖼", "jpeg": "🖼", "png": "🖼",
        "mp4": "🎬", "mp3": "🎵",
    }

    # Extensions ouvrables directement (pas les .py .exe etc.)
    safe_open_exts  = {"pdf","docx","doc","xlsx","xls","pptx","ppt",
                       "txt","png","jpg","jpeg","gif","mp4","mp3","zip"}
    editable_exts   = {"py","js","ts","html","css","json","yaml","yml",
                       "md","txt","ini","cfg","toml","csv","xml","sql"}

    text_exts = {"py","js","ts","html","css","json","yaml","yml",
                  "md","txt","ini","cfg","toml","csv","xml","sql",
                  "ps1","bat","sh","log","gitignore","env"}

    for line in lines:
        if line.startswith("  OPEN:"):
            rest     = line.replace("  OPEN:", "", 1)
            parts    = rest.split("|")
            fullpath = parts[0].strip()
            relpath  = parts[1].strip() if len(parts) > 1 else parts[0]
            idx_num  = parts[2].strip() if len(parts) > 2 else ""

            ext      = fullpath.rsplit(".", 1)[-1].lower() if "." in fullpath else ""
            icon     = ext_icons.get(ext, "\U0001f4c4")

            # Encoder le chemin comme attribut HTML data-path
            # → pas de problème de guillemets dans onclick !
            safe_fullpath = h.escape(fullpath)
            safe_relpath  = h.escape(relpath)
            idx_label     = f"[{idx_num}] " if idx_num else ""
            is_text       = ext in text_exts

            # Bouton Ouvrir — pour TOUS les fichiers (os.startfile)
            btn_open = (
                f'<button class="fs-open-btn" '
                f'data-path="{safe_fullpath}" '
                f'onclick="fsOpenFile(this)">'
                f'&#x2197; Ouvrir</button>'
            )

            # Bouton Edit — seulement pour fichiers texte/code
            # Ouvre dans le navigateur via /fs/view
            btn_edit = ""
            if is_text:
                btn_edit = (
                    f'<button class="fs-open-btn" '
                    f'style="background:color-mix(in srgb,#007ACC 20%,transparent);'
                    f'border-color:#007ACC55;color:#007ACC;" '
                    f'data-path="{safe_fullpath}" '
                    f'onclick="fsEditFile(this)">'
                    f'&#x1F4DD; Edit</button>'
                )

            html_parts.append(
                f'<div class="fs-result-item">'
                f'<span class="fs-icon">{icon}</span>'
                f'<span class="fs-name" title="{safe_fullpath}">'
                f'{idx_label}{safe_relpath}</span>'
                f'{btn_open}{btn_edit}'
                f'</div>'
            )
        elif "aucun fichier" in line.lower():
            html_parts.append(
                f'<div style="color:var(--text-dim);padding:16px;text-align:center;">'
                f'&#x1F636; {h.escape(line)}</div>'
            )
        elif line.strip() and not line.strip().startswith("fs open") \
                and not line.strip().startswith("fs edit"):
            html_parts.append(
                f'<div class="stat-row">'
                f'<span style="color:var(--text-dim);font-size:0.82rem;">'
                f'{h.escape(line)}</span>'
                f'</div>'
            )

    return HTMLResponse(
        "\n".join(html_parts) if html_parts
        else f'<pre class="cmd-result">{h.escape(result)}</pre>'
    )


@app.post("/fs/open")
async def fs_open(request: Request):
    body = await request.json()
    path = body.get("path", "")
    try:
        import os
        os.startfile(path)
        return JSONResponse({"ok": True})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)})


# ── QuickMind ─────────────────────────────────────────────────────────────────

@app.get("/fs/view", response_class=HTMLResponse)
async def fs_view(request: Request, path: str = ""):
    """Affiche le contenu d un fichier texte dans le navigateur."""
    import html as h
    from pathlib import Path
    try:
        p = Path(path)
        if not p.exists():
            return HTMLResponse(f"<p style='color:red'>Fichier introuvable : {h.escape(path)}</p>")
        content = p.read_text(encoding="utf-8", errors="replace")
        ext     = p.suffix.lstrip(".").lower()
        return HTMLResponse(
            f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>{h.escape(p.name)}</title>
<style>
body{{background:#0f1117;color:#e0e0e0;font-family:"Cascadia Code",Consolas,monospace;
      padding:20px;margin:0;}}
h2{{color:#1e90ff;border-bottom:1px solid #2a2d3e;padding-bottom:8px;}}
pre{{background:#1a1d27;padding:16px;border-radius:8px;overflow:auto;
     font-size:0.85rem;line-height:1.5;white-space:pre-wrap;word-break:break-all;}}
</style></head>
<body>
<h2>&#x1F4DD; {h.escape(p.name)}</h2>
<p style="color:#888;font-size:0.8rem;">{h.escape(str(p))}</p>
<pre>{h.escape(content)}</pre>
</body></html>"""
        )
    except Exception as exc:
        return HTMLResponse(f"<p style='color:red'>Erreur : {h.escape(str(exc))}</p>")


@app.post("/fs/edit")
async def fs_edit(request: Request):
    """Ouvre un fichier dans VS Code."""
    body = await request.json()
    path = body.get("path", "")
    try:
        import subprocess
        subprocess.Popen(["code", path])
        return JSONResponse({"ok": True})
    except FileNotFoundError:
        # VS Code pas dans PATH — essayer chemin complet Windows
        import os
        username = os.environ.get("USERNAME", "")
        vscode_paths = [
            rf"C:\Users\{username}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
            r"C:\Program Files\Microsoft VS Code\Code.exe",
        ]
        for vp in vscode_paths:
            if os.path.exists(vp):
                subprocess.Popen([vp, path])
                return JSONResponse({"ok": True})
        return JSONResponse({"ok": False, "error": "VS Code introuvable. Ajoute 'code' dans le PATH."})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)})


@app.post("/quickmind/task", response_class=HTMLResponse)
async def qm_create_task(
    title:    str = Form(...),
    priority: str = Form("normal"),
    category: str = Form(""),
):
    import requests as req
    try:
        body: dict[str, Any] = {"title": title, "priority": priority}
        if category: body["category"] = category
        r = req.post("http://localhost:8765/task", json=body, timeout=5)
        r.raise_for_status()
        data = r.json()
        return HTMLResponse(
            f'<div class="alert-success">OK Tache #{data.get("id","?")} creee : {title}</div>'
        )
    except Exception as exc:
        return HTMLResponse(f'<div class="alert-error">ERREUR : {exc}</div>')


@app.post("/quickmind/done/{task_id}", response_class=HTMLResponse)
async def qm_done(task_id: int):
    import requests as req
    try:
        r = req.post(f"http://localhost:8765/task/{task_id}/done", timeout=5)
        r.raise_for_status()
        return HTMLResponse('<span class="badge badge-green">Done</span>')
    except Exception as exc:
        return HTMLResponse(f'<span class="badge badge-red">Erreur : {exc}</span>')


# ── ADO ───────────────────────────────────────────────────────────────────────

@app.post("/ado/get", response_class=HTMLResponse)
async def ado_get(request: Request):
    import html as h
    body   = await request.json()
    result = executor.execute("ado_get_item", body)
    return HTMLResponse(f'<pre class="ado-result">{h.escape(result)}</pre>')


@app.post("/ado/update", response_class=HTMLResponse)
async def ado_update(request: Request):
    import html as h
    body   = await request.json()
    result = executor.execute("ado_update_item", body)
    ok     = "OK" in result or "mis a jour" in result
    color  = "var(--green)" if ok else "var(--red)"
    return HTMLResponse(
        f'<pre class="ado-result" style="color:{color};">{h.escape(result)}</pre>'
    )


@app.post("/ado/search", response_class=HTMLResponse)
async def ado_search_route(request: Request):
    import html as h, re
    body   = await request.json()
    result = executor.execute("ado_search_items", body)
    lines  = result.splitlines()

    # Couleurs par statut pour le dashboard
    state_classes = {
        "Active":      "state-active",
        "In Progress": "state-inprogress",
        "In Review":   "state-inprogress",
        "Done":        "state-done",
        "Closed":      "state-done",
        "New":         "state-new",
        "ToDo":        "state-new",
        "In Analysis": "state-new",
        "Removed":     "state-removed",
        "On hold":     "state-removed",
    }
    type_colors = {
        "[Bug]":     "#e74c3c",
        "[Task]":    "#27ae60",
        "[Story]":   "#2980b9",
        "[Feature]": "#8e44ad",
        "[Epic]":    "#d35400",
    }

    html_parts = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Ligne item avec prefix ITEM:
        if "ITEM:" in line:
            # Format : ITEM:id|type|state|  display_text
            try:
                meta_part  = line.split("ITEM:")[1].split("|")
                wi_id      = meta_part[0]
                wi_type    = meta_part[1]
                wi_state   = meta_part[2]
                display    = "|".join(meta_part[3:]).strip()
                if display.startswith("|"):
                    display = display[1:]

                state_cls  = state_classes.get(wi_state, "state-new")
                type_label = f"[{wi_type[:5]}]"
                type_color = type_colors.get(f"[{wi_type.split()[0]}]", "#888")

                safe_display = h.escape(display[:80])
                html_parts.append(
                    f'<div class="ado-item-row" style="cursor:pointer;" '
                    f'onclick="document.getElementById(\'ado-update-id\').value=\'{wi_id}\';'
                    f'adoTab(\'update\');adoLoadItem();">'
                    f'<span class="ado-id">#{wi_id}</span>'
                    f'<span style="color:{type_color};font-size:0.75rem;padding:1px 6px;'
                    f'background:color-mix(in srgb,{type_color} 15%,transparent);'
                    f'border-radius:8px;">{h.escape(type_label)}</span>'
                    f'<span class="ado-state {state_cls}">{h.escape(wi_state)}</span>'
                    f'<span class="ado-title">{safe_display}</span>'
                    f'<span style="color:var(--text-dim);font-size:0.72rem;">✏</span>'
                    f'</div>'
                )
            except Exception:
                html_parts.append(
                    f'<div class="stat-row">'
                    f'<span style="color:var(--text-dim);font-size:0.82rem;">'
                    f'{h.escape(stripped)}</span></div>'
                )
        elif stripped.startswith("-"):
            html_parts.append('<hr style="border-color:var(--border);margin:6px 0;">')
        elif "aucun item" in stripped.lower():
            html_parts.append(
                f'<div style="color:var(--text-dim);padding:16px;text-align:center;">'
                f'😶 {h.escape(stripped)}</div>'
            )
        elif stripped:
            html_parts.append(
                f'<div class="stat-row">'
                f'<span style="color:var(--text-dim);font-size:0.82rem;">'
                f'{h.escape(stripped)}</span></div>'
            )

    return HTMLResponse(
        "\n".join(html_parts) if html_parts
        else f'<pre class="ado-result">{h.escape(result)}</pre>'
    )


# ── Scheduler actions ─────────────────────────────────────────────────────────

@app.post("/scheduler/pause/{job_id}", response_class=HTMLResponse)
async def pause_job(job_id: str):
    scheduler.pause_job(job_id)
    return HTMLResponse('<span class="badge badge-orange">Paused</span>')


@app.post("/scheduler/resume/{job_id}", response_class=HTMLResponse)
async def resume_job(job_id: str):
    scheduler.resume_job(job_id)
    return HTMLResponse('<span class="badge badge-green">Running</span>')


@app.post("/scheduler/remove/{job_id}", response_class=HTMLResponse)
async def remove_job(job_id: str):
    scheduler.remove_job(job_id)
    return HTMLResponse('<span class="badge badge-red">Supprime</span>')


@app.get("/api/memory/paths")
async def get_memory_paths():
    """Retourne les cles memoire de type path pour l autocompletion."""
    items = fresh_mem().list_memory(memory_type="path")
    result = []
    for key, item in items.items():
        result.append({
            "key":   key,
            "value": item.get("value", ""),
        })
    return result


# ── Voice results store — stockage temporaire des pages de résultats ────────
import time, uuid, html as _html
_VOICE_RESULTS: dict[str, dict] = {}  # {uid: {data, expires_at, query}}
_VOICE_RESULT_TTL = 300  # 5 minutes

def _cleanup_voice_results():
    """Supprime les résultats expirés."""
    now = time.time()
    expired = [k for k, v in _VOICE_RESULTS.items() if v.get("expires_at", 0) < now]
    for k in expired:
        del _VOICE_RESULTS[k]

def _store_voice_result(query: str, action: str, voice_response: str,
                        service_result: str | None, params: dict) -> str:
    """Stocke un résultat vocal et retourne son UID."""
    _cleanup_voice_results()
    uid = str(uuid.uuid4())[:8]
    _VOICE_RESULTS[uid] = {
        "query":          query,
        "action":         action,
        "voice_response": voice_response,
        "service_result": service_result or "",
        "params":         params,
        "created_at":     time.time(),
        "expires_at":     time.time() + _VOICE_RESULT_TTL,
    }
    return uid


def _build_result_html(uid: str, data: dict, base_url: str) -> str:
    """Génère la page HTML de résultat pour l iPhone."""
    query          = _html.escape(data.get("query", ""))
    action         = _html.escape(data.get("action", ""))
    voice_response = _html.escape(data.get("voice_response", ""))
    service_result = data.get("service_result", "")
    params         = data.get("params", {})
    created        = time.strftime("%H:%M:%S", time.localtime(data.get("created_at", 0)))
    expires_in     = max(0, int(data.get("expires_at", 0) - time.time()))

    # Formatter le résultat de service selon l action
    result_html = ""
    if service_result:
        lines = service_result.splitlines()
        if action == "search_all":
            # Résultats de recherche universelle ADO + QM
            ado_section = ""
            qm_section  = ""
            current = "ado"
            ado_items = []
            for line in lines:
                line = line.strip()
                if not line:
                    if ado_items:
                        current = "qm"
                    continue
                if current == "ado" and "#" in line:
                    import re as _re
                    m = _re.search(r'#(\d+)', line)
                    if m:
                        ado_id  = m.group(1)
                        project = params.get("project","PTG - TMM D2").replace(" ","%20")
                        url     = f"https://dev.azure.com/Premiertech/{project}/_workitems/edit/{ado_id}"
                        ado_items.append(
                            f'<a href="{url}" class="item-card">'
                            f'<span class="item-id">#{ado_id}</span>'
                            f'<span class="item-text">{_html.escape(line)}</span>'
                            f'<span class="item-arrow">&#x279C;</span></a>'
                        )
                elif current == "qm":
                    qm_section += f'<div class="item-card">{_html.escape(line)}</div>'
            if ado_items:
                ado_section = "<h3 style='color:#0078d4;font-size:0.82rem;margin:10px 0 6px;'>&#x1F535; Azure DevOps</h3>" + "".join(ado_items)
            if qm_section:
                qm_section = "<h3 style='color:#4caf50;font-size:0.82rem;margin:10px 0 6px;'>&#x2705; QuickMind</h3>" + qm_section
            result_html = ado_section + qm_section or f'<div class="info-line">Aucun résultat.</div>'
        elif action in ("ado_search_items", "ado_get_item"):
            # Résultat ADO — formatter en cards
            cards = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if "#" in line and ("[" in line or "→" in line):
                    # Ligne item ADO
                    ado_url = ""
                    ado_id  = ""
                    import re
                    m = re.search(r'#(\d+)', line)
                    if m:
                        ado_id  = m.group(1)
                        project = params.get("project", "PTG - TMM D2").replace(" ", "%20")
                        ado_url = f"https://dev.azure.com/Premiertech/{project}/_workitems/edit/{ado_id}"
                    clean = _html.escape(line)
                    if ado_url:
                        cards.append(
                            f'<a href="{ado_url}" class="item-card">'
                            f'<span class="item-id">#{ado_id}</span>'
                            f'<span class="item-text">{clean}</span>'
                            f'<span class="item-arrow">&#x279C;</span>'
                            f'</a>'
                        )
                    else:
                        cards.append(f'<div class="info-line">{clean}</div>')
                else:
                    cards.append(f'<div class="info-line">{_html.escape(line)}</div>')
            result_html = "
".join(cards)
        elif action in ("qm_list_tasks",):
            # Tâches QuickMind
            cards = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                prio_color = "#f44336" if "urgent" in line.lower() else                              "#ff9800" if "high" in line.lower() else "#1e90ff"
                cards.append(
                    f'<div class="item-card" style="border-left:3px solid {prio_color};">'
                    f'{_html.escape(line)}</div>'
                )
            result_html = "
".join(cards)
        else:
            # Résultat générique — préformaté
            result_html = f'<pre class="result-pre">{_html.escape(service_result)}</pre>'

    # Action badge color
    action_colors = {
        "ado_search_items": "#0078d4", "ado_get_item": "#0078d4",
        "qm_add_task": "#4caf50", "qm_list_tasks": "#4caf50",
        "net_myip": "#1e90ff", "net_status": "#1e90ff",
        "sys_cpu": "#9c27b0", "sys_disk": "#9c27b0",
        "timer": "#ff9800",
    }
    action_color = action_colors.get(action, "#888")

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0">
<meta http-equiv="refresh" content="{expires_in}">
<title>AION — {query[:30]}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  background:#0f1117;color:#e0e0e0;min-height:100vh;}}
.header{{background:#151821;border-bottom:2px solid #1e90ff;
  padding:14px 16px;display:flex;align-items:center;gap:10px;}}
.header h1{{color:#1e90ff;font-size:1.1rem;}}
.badge{{background:{action_color}22;color:{action_color};border:1px solid {action_color}44;
  padding:3px 10px;border-radius:12px;font-size:0.72rem;font-weight:600;}}
.query{{background:#1a1d27;border-left:3px solid #1e90ff;
  padding:12px 16px;margin:12px;border-radius:0 8px 8px 0;
  font-size:0.9rem;color:#ccc;font-style:italic;}}
.voice-response{{background:#1a1d27;border-radius:10px;padding:14px 16px;
  margin:0 12px 12px;font-size:1rem;line-height:1.5;}}
.voice-response .icon{{font-size:1.3rem;margin-right:8px;}}
.results{{padding:0 12px 20px;}}
.results h2{{font-size:0.78rem;text-transform:uppercase;letter-spacing:1px;
  color:#888;margin-bottom:10px;}}
.item-card{{display:flex;align-items:center;gap:10px;
  background:#1a1d27;border-radius:8px;padding:12px 14px;
  margin-bottom:8px;text-decoration:none;color:#e0e0e0;
  border:1px solid #2a2d3e;}}
.item-card:active{{background:#2a2d3e;}}
.item-id{{color:#1e90ff;font-weight:700;font-size:0.82rem;min-width:50px;flex-shrink:0;}}
.item-text{{flex:1;font-size:0.85rem;}}
.item-arrow{{color:#888;font-size:0.9rem;flex-shrink:0;}}
.info-line{{background:#1a1d27;border-radius:6px;padding:8px 12px;
  margin-bottom:6px;font-size:0.85rem;color:#ccc;}}
.result-pre{{background:#0a0c14;border-radius:8px;padding:14px;
  font-family:"Cascadia Code",Consolas,monospace;font-size:0.78rem;
  color:#4caf50;white-space:pre-wrap;overflow-x:auto;}}
.footer{{text-align:center;padding:16px;color:#444;font-size:0.72rem;}}
.refresh-btn{{display:block;text-align:center;background:#1a1d27;
  border:1px solid #2a2d3e;color:#888;padding:10px;margin:0 12px 12px;
  border-radius:8px;text-decoration:none;font-size:0.85rem;}}
.refresh-btn:active{{background:#2a2d3e;}}
.expires{{color:#555;font-size:0.7rem;text-align:center;padding:4px;}}
</style>
</head>
<body>

<div class="header">
  <span style="font-size:1.4rem;">&#x1F916;</span>
  <h1>AION</h1>
  <span class="badge">{action}</span>
  <span style="margin-left:auto;color:#555;font-size:0.72rem;">{created}</span>
</div>

<div class="query">&#x201C;{query}&#x201D;</div>

<div class="voice-response">
  <span class="icon">&#x1F50A;</span>{voice_response}
</div>

{"<div class='results'><h2>Resultats</h2>" + result_html + "</div>" if result_html else ""}

<a href="{base_url}/voice/result/{uid}" class="refresh-btn">&#x21BA; Rafraichir</a>

<div class="expires">Page disponible encore {expires_in}s &mdash; expire automatiquement</div>

<div class="footer">AION Dashboard &mdash; {base_url}</div>

</body>
</html>"""


@app.get("/voice/result/{uid}", response_class=HTMLResponse)
async def voice_result_page(uid: str, request: Request):
    """Page de résultat vocal — ouverte automatiquement sur l iPhone."""
    _cleanup_voice_results()
    data = _VOICE_RESULTS.get(uid)
    if not data:
        return HTMLResponse(
            "<html><body style='background:#0f1117;color:#e0e0e0;font-family:sans-serif;"
            "display:flex;align-items:center;justify-content:center;height:100vh;'>"
            "<div style='text-align:center;'><h2 style='color:#f44336;'>Page expirée</h2>"
            "<p style='color:#888;margin-top:10px;'>Ce résultat a expiré (5 min max).</p>"
            "<p style='color:#888;margin-top:6px;'>Relancez une commande vocale.</p>"
            "</div></body></html>",
            status_code=410
        )
    base_url = str(request.base_url).rstrip("/")
    return HTMLResponse(_build_result_html(uid, data, base_url))


@app.post("/api/voice")
async def voice_endpoint(request: Request):
    """
    Point d entree pour les raccourcis iPhone / Siri.
    Body : { "text": "commande vocale", "lang": "fr" }
    Retour: { "response": "texte lisible par Siri", "action": "...", "ok": true }
    """
    import os, json as _json

    body = await request.json()
    text = body.get("text", "").strip()

    if not text:
        return {"response": "Je n ai rien compris. Repetez s il vous plait.", "ok": False}

    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        return {"response": "Cle Groq non configuree dans AION.", "ok": False}

    # Normaliser le texte avant envoi à Groq
    # Corriger les erreurs courantes de reconnaissance vocale
    VOICE_ALIASES = {
        # ADO / Azure DevOps
        "ado":          "ADO",
        "azure":        "ADO",
        "azure devo":   "ADO",
        "azure devops": "ADO",
        "azur":         "ADO",
        "azur devops":  "ADO",
        "a d o":        "ADO",
        "ado items":    "ADO items",
        "devops":       "ADO",
        # Commandes courantes
        "mes tâches":   "mes taches",
        "mes tache":    "mes taches",
        "mes tasks":    "mes taches",
        "quickmind":    "QuickMind",
        "quick mind":   "QuickMind",
        "timer":        "timer",
        "minuteur":     "timer",
        "compte à rebours": "timer",
        "pomodoro":     "timer 25 minutes",
    }
    text_lower = text.lower()
    for alias, replacement in VOICE_ALIASES.items():
        if alias in text_lower:
            text = text.replace(alias, replacement)
            text = text.replace(alias.title(), replacement)
            break

    SYSTEM = """Tu es AION, un assistant vocal pour la gestion de projet.
Tu recois des commandes vocales en francais et tu retournes un JSON :
{
  "action": "nom_service_ou_question",
  "params": {},
  "voice_response": "reponse courte a lire (max 2 phrases)"
}

Services disponibles :
- net_myip         → IP publique
- net_status       → statut reseau complet
- net_ping         → ping 8.8.8.8
- sys_cpu          → CPU et RAM
- sys_disk         → disques
- sys_uptime       → uptime machine
- qm_add_task      → params: {title, priority: urgent/high/normal/low, category}
- qm_list_tasks    → lister taches QuickMind
- qm_health        → QuickMind actif ?
- ado_search_items → params: {state, type, assigned: "@me", project: "PTG - TMM D2"}
- ado_get_item     → params: {item_id: 12345}
- timer            → params: {duration: "25m", message: "..."}
- search_all       → recherche simultanee dans ADO + QuickMind, params: {keyword: "mot"}
- question         → repondre sans service

IMPORTANT - Regle de recherche universelle :
Si l utilisateur demande de "chercher", "trouver", "y a-t-il", "recherche",
ou donne un mot-cle sans preciser la source → utiliser search_all.
search_all cherche automatiquement dans ADO ET QuickMind.

Exemples :
"IP public" → {"action":"net_myip","params":{},"voice_response":"Je verifie votre IP."}
"Ajoute RDV demain 14h urgent" → {"action":"qm_add_task","params":{"title":"RDV demain 14h","priority":"urgent"},"voice_response":"J ajoute RDV demain 14h en urgente."}
"Mes items en cours" ou "mes tickets" ou "mon backlog" → {"action":"ado_search_items","params":{"assigned":"@me"},"voice_response":"Je cherche vos items."}
"mes bugs" → {"action":"ado_search_items","params":{"type":"Bug","state":"Active"},"voice_response":"Je cherche vos bugs actifs."}
"cherche formation" ou "y a-t-il quelque chose sur formation" → {"action":"search_all","params":{"keyword":"formation"},"voice_response":"Je recherche formation dans ADO et QuickMind."}
"Timer 25 minutes" → {"action":"timer","params":{"duration":"25m","message":"Pause terminee !"},"voice_response":"Timer 25 minutes lance."}
Reponds UNIQUEMENT avec le JSON, sans texte avant ou apres."""

    import requests as req
    try:
        r = req.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={
                "model":    "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user",   "content": text},
                ],
                "temperature": 0.2,
                "max_tokens":  256,
            },
            timeout=15,
        )
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip()
        if "```" in raw:
            raw = raw.split("```")[1].strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()
        ai = _json.loads(raw)
    except Exception as e:
        return {"response": f"Erreur IA: {str(e)[:80]}", "ok": False}

    action     = ai.get("action", "question")
    params     = ai.get("params", {})
    voice_resp = ai.get("voice_response", "")
    svc_result = None

    # Services sans traitement spécial
    SIMPLE_SERVICES = {
        "net_myip", "net_status", "net_ping",
        "sys_cpu", "sys_disk", "sys_uptime", "sys_info",
        "docker_status", "qm_health", "qm_list_tasks",
    }

    if action in SIMPLE_SERVICES:
        try:
            svc_result = executor.execute(action, params or {})
            # Résumé vocal : 3 premières lignes non vides
            if svc_result:
                lines = [l.strip() for l in svc_result.splitlines() if l.strip()][:3]
                voice_resp = voice_resp + " " + " — ".join(lines)
        except Exception as e:
            voice_resp = f"Service indisponible: {str(e)[:60]}"

    elif action == "qm_add_task":
        try:
            svc_result = executor.execute("qm_add_task", params)
            if svc_result and "erreur" not in svc_result.lower():
                voice_resp = voice_resp
            else:
                voice_resp = "QuickMind n est pas disponible en ce moment."
        except Exception:
            voice_resp = "Impossible de creer la tache. QuickMind actif ?"

    elif action == "ado_search_items":
        try:
            svc_result = executor.execute("ado_search_items", params)
            if svc_result:
                items = [l.strip() for l in svc_result.splitlines()
                         if l.strip() and "#" in l][:3]
                if items:
                    voice_resp = f"J ai trouve {len(items)} item(s) : " + ", ".join(
                        i.split("]")[-1].strip()[:30] for i in items
                    )
                else:
                    voice_resp = "Aucun item trouve avec ces criteres."
        except Exception as e:
            voice_resp = f"Erreur ADO: {str(e)[:60]}"

    elif action == "ado_get_item":
        try:
            svc_result = executor.execute("ado_get_item", params)
            if svc_result:
                lines = [l.strip() for l in svc_result.splitlines() if l.strip()][:4]
                voice_resp = " — ".join(lines)
        except Exception as e:
            voice_resp = f"Erreur ADO: {str(e)[:60]}"

    elif action == "timer":
        try:
            svc_result = executor.execute("timer", params)
        except Exception:
            voice_resp = "Impossible de lancer le timer."

    elif action == "search_all":
        # Recherche simultanée ADO + QuickMind
        keyword  = params.get("keyword", text)
        results  = []
        ado_res  = ""
        qm_res   = ""

        # 1. Recherche ADO
        try:
            ado_params = {"title_contains": keyword, "limit": 5,
                          "project": params.get("project", "PTG - TMM D2")}
            ado_res    = executor.execute("ado_search_items", ado_params)
            ado_lines  = [l.strip() for l in (ado_res or "").splitlines()
                          if l.strip() and "#" in l]
            if ado_lines:
                results.append(f"ADO ({len(ado_lines)}): " + ado_lines[0][:50])
        except Exception:
            pass

        # 2. Recherche QuickMind
        try:
            import requests as _req
            qm_r = _req.get("http://localhost:8765/tasks", timeout=3)
            if qm_r.status_code == 200:
                tasks = qm_r.json()
                kw_low = keyword.lower()
                matching = [t for t in tasks
                            if kw_low in (t.get("title","") or "").lower()
                            or kw_low in (t.get("description","") or "").lower()]
                qm_res = f"{len(matching)} tâche(s) QuickMind"
                if matching:
                    results.append(f"QM ({len(matching)}): " + matching[0].get("title","")[:50])
        except Exception:
            pass

        if results:
            voice_resp  = f"J'ai trouvé des résultats pour '{keyword}'. " + " — ".join(results)
            svc_result  = (ado_res or "") + "

" + (qm_res or "")
        else:
            voice_resp  = f"Aucun résultat trouvé pour '{keyword}' dans ADO ni QuickMind."
            svc_result  = ""

    # Stocker le résultat et générer l URL de la page de détail
    result_uid = _store_voice_result(
        query          = text,
        action         = action,
        voice_response = voice_resp.strip(),
        service_result = svc_result,
        params         = params,
    )
    # Déterminer la meilleure URL pour l iPhone
    # Priorité : 1. IP mémorisée dans AION 2. Host de la requête 3. request.base_url
    _aion_ip = None
    try:
        _mem = memory.recall("aion_public_url") or memory.recall("tailscale_ip")
        if _mem:
            _aion_ip = _mem.strip().rstrip("/")
            if not _aion_ip.startswith("http"):
                _aion_ip = f"http://{_aion_ip}:8000"
    except Exception:
        pass

    if not _aion_ip:
        # Utiliser le host de la requête (correct si appelé via Tailscale/réseau)
        req_host = request.headers.get("host", "")
        if req_host and not req_host.startswith("127") and not req_host.startswith("localhost"):
            scheme   = "https" if request.url.scheme == "https" else "http"
            _aion_ip = f"{scheme}://{req_host}"
        else:
            _aion_ip = str(request.base_url).rstrip("/")

    result_url = f"{_aion_ip}/voice/result/{result_uid}"

    return {
        "response":   voice_resp.strip(),
        "action":     action,
        "params":     params,
        "result":     svc_result,
        "url":        result_url,
        "result_uid": result_uid,
        "ok":         True,
    }


@app.get("/api/ping")
async def api_ping():
    """Test rapide - vérifier qu AION est accessible (depuis iPhone, etc.)."""
    import socket as _sock
    # Récupérer l IP mémorisée
    saved_url = None
    try:
        saved_url = memory.recall("aion_public_url") or memory.recall("tailscale_ip")
    except Exception:
        pass
    try:
        local_ip = _sock.gethostbyname(_sock.gethostname())
    except Exception:
        local_ip = "inconnu"
    return {
        "status":      "ok",
        "message":     "AION répond !",
        "local_ip":    local_ip,
        "saved_url":   saved_url or "non configuré",
        "tip":         "Pour configurer : AION> remember aion_public_url=http://100.102.139.40:8000",
    }


@app.post("/services/reload", response_class=HTMLResponse)
async def reload_services():
    registry.reload_services()
    return HTMLResponse(
        f'<span class="badge badge-green">OK {registry.count()} services</span>'
    )
