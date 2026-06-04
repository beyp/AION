"""Serveur FastAPI pour AION - expose les services via HTTP."""
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from aion.core.config_loader import ConfigLoader
from aion.core.executor import ServiceExecutor
from aion.core.registry import ServiceRegistry
from aion.core.scheduler import AionScheduler
from aion.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

# ── Modeles Pydantic ───────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    payload: dict[str, Any] = {}


class MemorySetRequest(BaseModel):
    value: str
    memory_type: str = "info"


class ScheduleRequest(BaseModel):
    service_name: str
    interval_seconds: int = 60


# ── Composants globaux ─────────────────────────────────────────────────────────

registry = ServiceRegistry()
executor = ServiceExecutor(registry)
memory = MemoryManager()
scheduler = AionScheduler()
config = ConfigLoader().load()


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.discover_services()
    scheduler.start()
    logger.info("AION API started")
    yield
    scheduler.stop()
    logger.info("AION API stopped")


# ── Application FastAPI ────────────────────────────────────────────────────────

app = FastAPI(
    title="AION API",
    description="AI Agent Orchestrator Node - REST API",
    version=config.get("app", {}).get("version", "0.4.0"),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes : Status ────────────────────────────────────────────────────────────

@app.get("/", tags=["Status"])
def root():
    """Point d entree - verifie qu AION est en ligne."""
    app_cfg = config.get("app", {})
    return {
        "name": app_cfg.get("name", "AION"),
        "version": app_cfg.get("version", "0.4.0"),
        "status": "online",
    }


@app.get("/status", tags=["Status"])
def status():
    """Retourne le statut complet d AION."""
    mem_stats = memory.stats()
    return {
        "version": config.get("app", {}).get("version", "0.4.0"),
        "services": registry.count(),
        "memory": {
            "persistent": mem_stats["total"],
            "temporary": mem_stats["temporary_total"],
            "by_type": mem_stats["by_type"],
        },
        "scheduler": {
            "running": scheduler.is_running(),
            "jobs": scheduler.job_count(),
        },
    }


# ── Routes : Services ──────────────────────────────────────────────────────────

@app.get("/services", tags=["Services"])
def list_services():
    """Liste tous les services disponibles."""
    return {
        "count": registry.count(),
        "services": [
            {
                "name": s.name,
                "description": s.description,
                "permissions": s.permissions,
            }
            for s in registry.list_services()
        ],
    }


@app.get("/services/{service_name}", tags=["Services"])
def get_service(service_name: str):
    """Retourne les details d un service specifique."""
    service = registry.get(service_name)
    if service is None:
        raise HTTPException(status_code=404, detail=f"Service not found: {service_name}")
    return {
        "name": service.name,
        "description": service.description,
        "permissions": service.permissions,
    }


@app.post("/run/{service_name}", tags=["Services"])
def run_service(service_name: str, request: RunRequest = RunRequest()):
    """Execute un service et retourne le resultat."""
    service = registry.get(service_name)
    if service is None:
        raise HTTPException(status_code=404, detail=f"Service not found: {service_name}")
    result = executor.execute(service_name, request.payload)
    return {"service": service_name, "result": result}


@app.post("/services/reload", tags=["Services"])
def reload_services():
    """Recharge tous les services sans redemarrer AION."""
    registry.reload_services()
    return {"message": "Services reloaded", "count": registry.count()}


# ── Routes : Memoire ───────────────────────────────────────────────────────────

@app.get("/memory", tags=["Memory"])
def list_memory(memory_type: str | None = None):
    """Liste la memoire persistante, optionnellement filtree par type."""
    items = memory.list_memory(memory_type=memory_type)
    return {"count": len(items), "items": items}


@app.get("/memory/stats", tags=["Memory"])
def memory_stats():
    """Retourne les statistiques de memoire."""
    return memory.stats()


@app.get("/memory/search", tags=["Memory"])
def search_memory(q: str):
    """Recherche dans la memoire (cles, valeurs, types)."""
    results = memory.search(q)
    return {"query": q, "count": len(results), "results": results}


@app.get("/memory/{key}", tags=["Memory"])
def get_memory(key: str):
    """Retourne un element de memoire par sa cle."""
    item = memory.get_item(key)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Memory key not found: {key}")
    return {"key": key, **item}


@app.put("/memory/{key}", tags=["Memory"])
def set_memory(key: str, request: MemorySetRequest):
    """Cree ou met a jour un element en memoire persistante."""
    memory.remember(key, request.value, memory_type=request.memory_type)
    return {"message": f"Memory saved: {key}", "key": key, "value": request.value}


@app.delete("/memory/{key}", tags=["Memory"])
def delete_memory(key: str):
    """Supprime un element de memoire."""
    if not memory.forget(key):
        raise HTTPException(status_code=404, detail=f"Memory key not found: {key}")
    return {"message": f"Memory deleted: {key}"}


# ── Routes : Scheduler ─────────────────────────────────────────────────────────

@app.get("/scheduler", tags=["Scheduler"])
def list_scheduler_jobs():
    """Liste tous les jobs planifies."""
    return {
        "running": scheduler.is_running(),
        "count": scheduler.job_count(),
        "jobs": scheduler.list_jobs(),
    }


@app.post("/scheduler/jobs", tags=["Scheduler"])
def add_scheduler_job(request: ScheduleRequest):
    """Planifie un service a intervalle regulier."""
    service = registry.get(request.service_name)
    if service is None:
        raise HTTPException(
            status_code=404,
            detail=f"Service not found: {request.service_name}",
        )

    job_id = f"scheduled_{request.service_name}"

    def run():
        executor.execute(request.service_name, {})

    scheduler.add_job(job_id, run, interval_seconds=request.interval_seconds)

    return {
        "message": f"Job scheduled: {job_id}",
        "job_id": job_id,
        "service": request.service_name,
        "interval_seconds": request.interval_seconds,
    }


@app.delete("/scheduler/jobs/{job_id}", tags=["Scheduler"])
def remove_scheduler_job(job_id: str):
    """Supprime un job planifie."""
    scheduler.remove_job(job_id)
    return {"message": f"Job removed: {job_id}"}


@app.post("/scheduler/jobs/{job_id}/pause", tags=["Scheduler"])
def pause_scheduler_job(job_id: str):
    """Met en pause un job planifie."""
    if not scheduler.pause_job(job_id):
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return {"message": f"Job paused: {job_id}"}


@app.post("/scheduler/jobs/{job_id}/resume", tags=["Scheduler"])
def resume_scheduler_job(job_id: str):
    """Reprend un job planifie."""
    if not scheduler.resume_job(job_id):
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return {"message": f"Job resumed: {job_id}"}
