"""Scheduler AION - planificateur de taches base sur APScheduler."""
import logging
from typing import Any, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class AionScheduler:
    """
    Planificateur de taches pour AION.

    Permet d executer des services ou fonctions a intervalles reguliers,
    en arriere-plan, sans bloquer la boucle principale.

    Usage:
        scheduler = AionScheduler()
        scheduler.add_job("ping_check", ping_fn, interval_seconds=60)
        scheduler.start()
        scheduler.stop()
    """

    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler(timezone="America/Toronto")
        self._jobs: dict[str, dict[str, Any]] = {}
        self._running = False

    def start(self) -> None:
        """Demarre le scheduler en arriere-plan."""
        if not self._running:
            self._scheduler.start()
            self._running = True
            logger.info("Scheduler started")

    def stop(self) -> None:
        """Arrete le scheduler proprement."""
        if self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Scheduler stopped")

    def add_job(
        self,
        job_id: str,
        func: Callable,
        interval_seconds: int = 60,
        args: list | None = None,
        kwargs: dict | None = None,
    ) -> None:
        """
        Ajoute un job planifie.

        Args:
            job_id:           Identifiant unique du job.
            func:             Fonction a executer.
            interval_seconds: Intervalle en secondes.
            args:             Arguments positionnels.
            kwargs:           Arguments nommes.
        """
        if job_id in self._jobs:
            logger.warning("Scheduler: job '%s' already exists, replacing.", job_id)
            self.remove_job(job_id)

        trigger = IntervalTrigger(seconds=interval_seconds)

        self._scheduler.add_job(
            func=func,
            trigger=trigger,
            id=job_id,
            args=args or [],
            kwargs=kwargs or {},
            replace_existing=True,
        )

        self._jobs[job_id] = {
            "func": func.__name__,
            "interval_seconds": interval_seconds,
        }

        logger.info("Scheduler: job '%s' added (every %ds)", job_id, interval_seconds)

    def remove_job(self, job_id: str) -> None:
        """Supprime un job planifie."""
        if job_id not in self._jobs:
            logger.debug("Scheduler: job '%s' not found.", job_id)
            return

        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass

        del self._jobs[job_id]
        logger.info("Scheduler: job '%s' removed", job_id)

    def list_jobs(self) -> dict[str, dict[str, Any]]:
        """Retourne le dictionnaire des jobs enregistres."""
        return dict(self._jobs)

    def job_count(self) -> int:
        """Retourne le nombre de jobs enregistres."""
        return len(self._jobs)

    def is_running(self) -> bool:
        """Indique si le scheduler est actif."""
        return self._running

    def pause_job(self, job_id: str) -> bool:
        """Met en pause un job."""
        if job_id not in self._jobs:
            return False
        self._scheduler.pause_job(job_id)
        logger.info("Scheduler: job '%s' paused", job_id)
        return True

    def resume_job(self, job_id: str) -> bool:
        """Reprend un job mis en pause."""
        if job_id not in self._jobs:
            return False
        self._scheduler.resume_job(job_id)
        logger.info("Scheduler: job '%s' resumed", job_id)
        return True

    def get_job_state(self, job_id: str) -> str:
        """Retourne l etat reel d un job : running, paused ou unknown."""
        try:
            job = self._scheduler.get_job(job_id)
            if job is None:
                return "unknown"
            return "paused" if job.next_run_time is None else "running"
        except Exception:
            return "unknown"

