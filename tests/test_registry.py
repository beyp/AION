from aion.core.registry import ServiceRegistry


def test_default_services_are_registered():
    registry = ServiceRegistry()
    registry.register_default_services()

    assert registry.get("hello") is not None
    assert registry.get("system_info") is not None
