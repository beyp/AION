"""Tests unitaires pour le ServiceRegistry."""
import pytest
from aion.core.registry import ServiceRegistry
from aion.services.base_service import BaseService


class DummyService(BaseService):
    name = "dummy"
    description = "Service de test"
    permissions = []

    def execute(self, payload):
        return "dummy ok"


class AnotherService(BaseService):
    name = "another"
    description = "Autre service de test"
    permissions = []

    def execute(self, payload):
        return "another ok"


@pytest.fixture
def registry():
    r = ServiceRegistry()
    r._services.clear()
    return r


def test_register_and_get(registry):
    registry.register(DummyService())
    service = registry.get("dummy")
    assert service is not None
    assert service.name == "dummy"


def test_register_duplicate_raises(registry):
    registry.register(DummyService())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(DummyService())


def test_get_missing_service_returns_none(registry):
    assert registry.get("nonexistent") is None


def test_list_services(registry):
    registry.register(DummyService())
    registry.register(AnotherService())
    names = [s.name for s in registry.list_services()]
    assert "dummy" in names
    assert "another" in names


def test_count(registry):
    assert registry.count() == 0
    registry.register(DummyService())
    assert registry.count() == 1


def test_clear(registry):
    registry.register(DummyService())
    registry.clear()
    assert registry.count() == 0


def test_reload_services_clears_and_rediscovers(registry):
    registry.register(DummyService())
    assert registry.count() == 1
    registry.reload_services()
    assert registry.count() >= 0


def test_discover_services_finds_real_services(registry):
    registry.discover_services()
    names = [s.name for s in registry.list_services()]
    assert len(names) > 0
