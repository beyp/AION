"""Tests unitaires pour le ServiceExecutor."""
import pytest
from aion.core.executor import ServiceExecutor
from aion.core.registry import ServiceRegistry
from aion.services.base_service import BaseService


class EchoService(BaseService):
    name = "echo"
    description = "Retourne le payload"
    permissions = []

    def execute(self, payload):
        return f"echo: {payload.get('msg', 'empty')}"


class FailingService(BaseService):
    name = "failing"
    description = "Service qui plante"
    permissions = []

    def execute(self, payload):
        raise RuntimeError("Erreur simulee")


@pytest.fixture
def executor():
    registry = ServiceRegistry()
    registry._services.clear()
    registry.register(EchoService())
    registry.register(FailingService())
    return ServiceExecutor(registry)


def test_execute_known_service(executor):
    result = executor.execute("echo", {"msg": "hello"})
    assert "echo" in result


def test_execute_unknown_service(executor):
    result = executor.execute("ghost")
    assert "ghost" in result


def test_execute_failing_service(executor):
    result = executor.execute("failing")
    assert result is not None
    assert len(result) > 0


def test_execute_without_payload(executor):
    result = executor.execute("echo")
    assert result is not None
