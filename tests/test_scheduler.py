"""Tests unitaires pour le Scheduler AION."""
import time
import pytest
from aion.core.scheduler import AionScheduler


@pytest.fixture
def scheduler():
    s = AionScheduler()
    yield s
    s.stop()


def test_add_job_and_list(scheduler):
    def dummy():
        pass

    scheduler.add_job("test_job", dummy, interval_seconds=60)
    jobs = scheduler.list_jobs()
    assert "test_job" in jobs


def test_remove_job(scheduler):
    def dummy():
        pass

    scheduler.add_job("removable", dummy, interval_seconds=60)
    scheduler.remove_job("removable")
    jobs = scheduler.list_jobs()
    assert "removable" not in jobs


def test_job_executes(scheduler):
    counter = {"n": 0}

    def increment():
        counter["n"] += 1

    scheduler.add_job("counter_job", increment, interval_seconds=1)
    scheduler.start()
    time.sleep(2.5)
    scheduler.stop()

    assert counter["n"] >= 2


def test_remove_nonexistent_job_does_not_crash(scheduler):
    scheduler.remove_job("ghost_job")


def test_job_count(scheduler):
    scheduler.add_job("j1", lambda: None, interval_seconds=60)
    scheduler.add_job("j2", lambda: None, interval_seconds=60)
    assert scheduler.job_count() == 2


def test_is_running(scheduler):
    assert not scheduler.is_running()
    scheduler.start()
    assert scheduler.is_running()
    scheduler.stop()
    assert not scheduler.is_running()


def test_pause_and_resume(scheduler):
    scheduler.add_job("pausable", lambda: None, interval_seconds=60)
    scheduler.start()
    assert scheduler.pause_job("pausable") is True
    assert scheduler.resume_job("pausable") is True
    scheduler.stop()


def test_pause_nonexistent_returns_false(scheduler):
    assert scheduler.pause_job("ghost") is False


def test_resume_nonexistent_returns_false(scheduler):
    assert scheduler.resume_job("ghost") is False
