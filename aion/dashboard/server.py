"""Dashboard web AION - interface visuelle via FastAPI + Jinja2 + htmx."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from aion.core.config_loader import ConfigLoader
from aion.core.executor import ServiceExecutor
from aion.core.registry import ServiceRegistry
from aion.core.scheduler import AionScheduler
from aion.memory.memory_manager import MemoryManager
from aion.api.server import (
    app as api_app,
    registry,
    executor,
    memory,
    scheduler,
    config,
)

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ── Routes Dashboard ───────────────────────────────────────────────────────────

@api_app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard(request: Request):
    """Page principale du dashboard AION."""
    mem_stats = memory.stats()
    jobs = scheduler.list_jobs()
    jobs_with_state = {
        job_id: {
            **info,
            "state": scheduler.get_job_state(job_id),
        }
        for job_id, info in jobs.items()
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "version": config.get("app", {}).get("version", "0.4.0"),
            "services": registry.list_services(),
            "service_count": registry.count(),
            "memory_stats": mem_stats,
            "scheduler_running": scheduler.is_running(),
            "jobs": jobs_with_state,
            "job_count": scheduler.job_count(),
        },
    )


@api_app.get("/dashboard/services", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard_services(request: Request):
    """Fragment htmx : liste des services (refresh partiel)."""
    return templates.TemplateResponse(
        "fragments/services.html",
        {
            "request": request,
            "services": registry.list_services(),
            "service_count": registry.count(),
        },
    )


@api_app.get("/dashboard/status", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard_status(request: Request):
    """Fragment htmx : statut general (refresh partiel)."""
    mem_stats = memory.stats()
    return templates.TemplateResponse(
        "fragments/status.html",
        {
            "request": request,
            "version": config.get("app", {}).get("version", "0.4.0"),
            "service_count": registry.count(),
            "memory_stats": mem_stats,
            "scheduler_running": scheduler.is_running(),
            "job_count": scheduler.job_count(),
        },
    )


@api_app.get("/dashboard/scheduler", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard_scheduler(request: Request):
    """Fragment htmx : liste des jobs (refresh partiel)."""
    jobs = scheduler.list_jobs()
    jobs_with_state = {
        job_id: {**info, "state": scheduler.get_job_state(job_id)}
        for job_id, info in jobs.items()
    }
    return templates.TemplateResponse(
        "fragments/scheduler.html",
        {
            "request": request,
            "jobs": jobs_with_state,
            "job_count": scheduler.job_count(),
            "scheduler_running": scheduler.is_running(),
        },
    )


@api_app.get("/dashboard/memory", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard_memory(request: Request):
    """Fragment htmx : memoire persistante (refresh partiel)."""
    items = memory.list_memory()
    return templates.TemplateResponse(
        "fragments/memory.html",
        {
            "request": request,
            "items": items,
            "memory_stats": memory.stats(),
        },
    )
