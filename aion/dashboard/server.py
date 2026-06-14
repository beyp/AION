"""Dashboard AION v2 - Sidebar + Console + Domain Router."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

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
memory    = MemoryManager()
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
    mem_stats = memory.stats()
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
            "items":        memory.list_memory(),
            "memory_stats": memory.stats(),
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
    return templates.TemplateResponse(
        request=request, name="sections/fs_search.html", context={},
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
    dr = DomainRouter(executor, memory)
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
        stats = memory.stats()
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
        items = memory.list_memory()
        if not items:
            return "Memoire vide."
        return "\n".join(
            f"  {k} [{v.get('type')}] = {v.get('value')}"
            for k, v in items.items()
        )

    if cmd.startswith("remember ") and "=" in cmd:
        raw = cmd.replace("remember ", "", 1)
        key, val = raw.split("=", 1)
        memory.remember(key.strip(), val.strip())
        return f"Memorise : {key.strip()}"

    if cmd.startswith("recall "):
        key = cmd.replace("recall ", "", 1).strip()
        val = memory.recall(key)
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

    for line in lines:
        if line.startswith("  OPEN:"):
            rest             = line.replace("  OPEN:", "", 1)
            fullpath, relpath = rest.split("|", 1)
            ext              = fullpath.rsplit(".", 1)[-1].lower() if "." in fullpath else ""
            icon             = ext_icons.get(ext, "📄")
            safe_path        = h.escape(fullpath).replace("\\", "\\\\")
            safe_relpath     = h.escape(relpath)
            html_parts.append(
                f'<div class="fs-result-item">'
                f'<span class="fs-icon">{icon}</span>'
                f'<span class="fs-name">{safe_relpath}</span>'
                f'<button class="fs-open-btn" onclick="openFile(\'{safe_path}\', this)">'
                f'↗ Ouvrir</button></div>'
            )
        elif line.startswith("  -"):
            html_parts.append(
                f'<hr style="border-color:var(--border); margin:6px 0;">'
            )
        elif "aucun fichier" in line.lower():
            html_parts.append(
                f'<div style="color:var(--text-dim);padding:16px;text-align:center;">'
                f'😶 {h.escape(line)}</div>'
            )
        elif line.strip():
            html_parts.append(
                f'<div class="stat-row">'
                f'<span style="color:var(--text-dim);font-size:0.82rem;">{h.escape(line)}</span>'
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


@app.post("/services/reload", response_class=HTMLResponse)
async def reload_services():
    registry.reload_services()
    return HTMLResponse(
        f'<span class="badge badge-green">OK {registry.count()} services</span>'
    )
