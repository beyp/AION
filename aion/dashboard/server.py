"""Dashboard AION v2 - Sidebar + Console interactive + Drag & Drop."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from aion.core.config_loader import ConfigLoader
from aion.core.executor import ServiceExecutor
from aion.core.registry import ServiceRegistry
from aion.core.scheduler import AionScheduler
from aion.memory.memory_manager import MemoryManager
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

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
    version=config.get("app", {}).get("version", "0.7.0"),
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
            "version":  config.get("app", {}).get("version", "0.7.0"),
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
            "version":           config.get("app", {}).get("version", "0.7.0"),
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
        request=request,
        name="sections/network.html",
        context={},
    )


@app.get("/section/system", response_class=HTMLResponse)
async def section_system(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="sections/system.html",
        context={},
    )


@app.get("/section/docker", response_class=HTMLResponse)
async def section_docker(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="sections/docker.html",
        context={},
    )


@app.get("/section/quickmind", response_class=HTMLResponse)
async def section_quickmind(request: Request):
    import requests as req
    tasks = []
    qm_online = False
    try:
        r = req.get("http://localhost:8765/tasks", timeout=3)
        if r.status_code == 200:
            tasks = r.json()
            qm_online = True
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


@app.get("/section/console", response_class=HTMLResponse)
async def section_console(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="sections/console.html",
        context={
            "services": [s.name for s in registry.list_services()],
        },
    )


# ── Actions API ───────────────────────────────────────────────────────────────

@app.post("/run/{service_name}", response_class=HTMLResponse)
async def run_service(service_name: str):
    result = executor.execute(service_name, {})
    import html as h
    return HTMLResponse(f'<pre class="cmd-result">{h.escape(result)}</pre>')


@app.post("/console/run", response_class=HTMLResponse)
async def console_run(command: str = Form(...)):
    """Execute une commande AION depuis la console web."""
    import html as h
    cmd = command.strip()
    if not cmd:
        return HTMLResponse("")

    if cmd.startswith("run "):
        svc = cmd.replace("run ", "", 1).strip()
        result = executor.execute(svc, {})

    elif cmd == "services":
        svcs = registry.list_services()
        result = "\n".join(f"  - {s.name}: {s.description}" for s in svcs)

    elif cmd == "status":
        stats = memory.stats()
        result = (
            f"Version   : {config.get('app', {}).get('version', '?')}\n"
            f"Services  : {registry.count()}\n"
            f"Memory    : {stats['total']} items\n"
            f"Scheduler : {'Running' if scheduler.is_running() else 'Stopped'} "
            f"({scheduler.job_count()} jobs)"
        )

    elif cmd == "scheduler":
        jobs = scheduler.list_jobs()
        if not jobs:
            result = "Aucun job planifie."
        else:
            lines = []
            for jid, info in jobs.items():
                state = scheduler.get_job_state(jid)
                icon = "⏸" if state == "paused" else "▶"
                lines.append(f"  {icon} {jid} (toutes les {info['interval_seconds']}s)")
            result = "\n".join(lines)

    elif cmd == "memory":
        items = memory.list_memory()
        if not items:
            result = "Memoire vide."
        else:
            result = "\n".join(
                f"  {k} [{v.get('type')}] = {v.get('value')}"
                for k, v in items.items()
            )

    elif cmd.startswith("remember ") and "=" in cmd:
        raw = cmd.replace("remember ", "", 1)
        key, val = raw.split("=", 1)
        memory.remember(key.strip(), val.strip())
        result = f"Memorise : {key.strip()}"

    elif cmd.startswith("recall "):
        key = cmd.replace("recall ", "", 1).strip()
        val = memory.recall(key)
        result = f"{key} = {val}" if val else f"Aucune memoire pour : {key}"

    elif cmd.startswith("schedule ") and " every " in cmd:
        parts = cmd.replace("schedule ", "", 1).split(" every ")
        svc_name = parts[0].strip()
        try:
            interval = int(parts[1].strip().rstrip("s"))
            svc = registry.get(svc_name)
            if svc is None:
                result = f"Service inconnu : {svc_name}"
            else:
                job_id = f"scheduled_{svc_name}"
                _exec = executor
                def run():
                    _exec.execute(svc_name, {})
                scheduler.add_job(job_id, run, interval_seconds=interval)
                result = f"Job planifie : {job_id} (toutes les {interval}s)"
        except Exception as exc:
            result = f"Erreur : {exc}"

    elif cmd.startswith("unschedule "):
        jid = cmd.replace("unschedule ", "", 1).strip()
        scheduler.remove_job(jid)
        result = f"Job supprime : {jid}"

    elif cmd == "reload":
        registry.reload_services()
        result = f"Services recharges : {registry.count()}"

    elif cmd == "help":
        result = (
            "Commandes disponibles :\n"
            "  run <service>                 Executer un service\n"
            "  services                      Lister les services\n"
            "  status                        Statut AION\n"
            "  scheduler                     Jobs planifies\n"
            "  schedule <svc> every <N>s     Planifier un service\n"
            "  unschedule <job_id>           Supprimer un job\n"
            "  memory                        Lister la memoire\n"
            "  remember cle=valeur           Memoriser\n"
            "  recall cle                    Lire une valeur\n"
            "  reload                        Recharger les services\n"
            "  help                          Cette aide"
        )

    else:
        result = f"Commande inconnue : {cmd}\nTape 'help' pour la liste."

    safe_cmd = h.escape(cmd)
    safe_result = h.escape(result)
    return HTMLResponse(
        f'<div class="console-line">'
        f'<span class="console-prompt">AION&gt;</span> '
        f'<span class="console-cmd">{safe_cmd}</span>'
        f'</div>'
        f'<div class="console-output">{safe_result}</div>'
    )


@app.post("/quickmind/task", response_class=HTMLResponse)
async def qm_create_task(
    title:    str = Form(...),
    priority: str = Form("normal"),
    category: str = Form(""),
):
    import requests as req
    try:
        body: dict[str, Any] = {"title": title, "priority": priority}
        if category:
            body["category"] = category
        r = req.post("http://localhost:8765/task", json=body, timeout=5)
        r.raise_for_status()
        data = r.json()
        return HTMLResponse(
            f'<div class="alert-success">✅ Tache #{data.get("id","?")} creee : {title}</div>'
        )
    except Exception as exc:
        return HTMLResponse(f'<div class="alert-error">❌ Erreur : {exc}</div>')


@app.post("/quickmind/done/{task_id}", response_class=HTMLResponse)
async def qm_done(task_id: int):
    import requests as req
    try:
        r = req.post(f"http://localhost:8765/task/{task_id}/done", timeout=5)
        r.raise_for_status()
        return HTMLResponse('<span class="badge badge-green">✅ Done</span>')
    except Exception as exc:
        return HTMLResponse(f'<span class="badge badge-red">❌ {exc}</span>')


@app.post("/scheduler/pause/{job_id}", response_class=HTMLResponse)
async def pause_job(job_id: str):
    scheduler.pause_job(job_id)
    return HTMLResponse('<span class="badge badge-orange">⏸ Paused</span>')


@app.post("/scheduler/resume/{job_id}", response_class=HTMLResponse)
async def resume_job(job_id: str):
    scheduler.resume_job(job_id)
    return HTMLResponse('<span class="badge badge-green">▶ Running</span>')


@app.post("/scheduler/remove/{job_id}", response_class=HTMLResponse)
async def remove_job(job_id: str):
    scheduler.remove_job(job_id)
    return HTMLResponse('<span class="badge badge-red">🗑 Supprime</span>')


@app.post("/services/reload", response_class=HTMLResponse)
async def reload_services():
    registry.reload_services()
    return HTMLResponse(
        f'<span class="badge badge-green">✅ {registry.count()} services</span>'
    )

@app.post("/fs/search", response_class=HTMLResponse)
async def fs_search(request: Request):
    """Recherche de fichiers par mots-cles."""
    import html as h
    body = await request.json()
    keywords  = body.get("keywords", "")
    directory = body.get("directory", "")
    memory_key = body.get("memory_key", "search_dir")

    result = executor.execute("fs_search", {
        "keywords":   keywords,
        "directory":  directory,
        "memory_key": memory_key,
    })

    # Parser le résultat pour générer le HTML
    lines = result.splitlines()
    html_parts = []

    for line in lines:
        if line.startswith("  OPEN:"):
            # Format : OPEN:<fullpath>|<relpath>
            rest     = line.replace("  OPEN:", "", 1)
            fullpath, relpath = rest.split("|", 1)
            safe_path    = h.escape(fullpath)
            safe_relpath = h.escape(relpath)
            html_parts.append(
                f'<div class="fs-result-item">'
                f'  <span class="fs-icon">📄</span>'
                f'  <span class="fs-name">{safe_relpath}</span>'
                f'  <button class="run-btn" onclick="openFile(\'{safe_path.replace(chr(92), chr(92)+chr(92))}\')">↗ Ouvrir</button>'
                f'</div>'
            )
        elif line.startswith("  ─"):
            html_parts.append('<hr style="border-color:var(--border); margin:8px 0;">')
        elif line.startswith("fs_search : aucun"):
            html_parts.append(
                f'<div style="color:var(--text-dim); padding:12px; text-align:center;">'
                f'😶 {h.escape(line)}</div>'
            )
        elif line.startswith("fs_search :") or line.startswith("  Repertoire") or line.startswith("  Mots-cles"):
            html_parts.append(
                f'<div class="stat-row">'
                f'<span style="color:var(--text-dim); font-size:0.82rem;">{h.escape(line)}</span>'
                f'</div>'
            )

    if not html_parts:
        html_parts.append(
            f'<pre class="cmd-result">{h.escape(result)}</pre>'
        )

    # CSS pour les résultats
    css = """
    <style>
    .fs-result-item {
      display:flex; align-items:center; gap:10px;
      padding:7px 10px; border-radius:6px;
      background:color-mix(in srgb, var(--border) 40%, transparent);
      margin-bottom:4px; font-size:0.83rem;
    }
    .fs-icon { font-size:1rem; }
    .fs-name { flex:1; color:var(--text); word-break:break-all; }
    </style>
    """

    return HTMLResponse(css + "\n".join(html_parts))


@app.post("/fs/open")
async def fs_open(request: Request):
    """Ouvre un fichier avec l application par defaut Windows."""
    body = await request.json()
    path = body.get("path", "")
    try:
        import os
        os.startfile(path)
        return JSONResponse({"ok": True})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)})