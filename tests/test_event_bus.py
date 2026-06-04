"""Tests unitaires pour l EventBus."""
import pytest
from aion.core.event_bus import EventBus


@pytest.fixture
def bus():
    return EventBus()


def test_subscribe_and_emit(bus):
    received = []

    def handler(data):
        received.append(data)

    bus.subscribe("test.event", handler)
    bus.emit("test.event", {"key": "value"})

    assert len(received) == 1
    assert received[0]["key"] == "value"


def test_multiple_subscribers(bus):
    results = []

    bus.subscribe("multi", lambda d: results.append("A"))
    bus.subscribe("multi", lambda d: results.append("B"))
    bus.emit("multi", {})

    assert "A" in results
    assert "B" in results


def test_emit_no_subscribers_does_not_crash(bus):
    bus.emit("no.one.listening", {"data": 42})


def test_unsubscribe(bus):
    results = []

    def handler(data):
        results.append(data)

    bus.subscribe("ev", handler)
    bus.unsubscribe("ev", handler)
    bus.emit("ev", {"x": 1})

    assert results == []


def test_emit_with_no_data(bus):
    called = []
    bus.subscribe("empty", lambda d: called.append(d))
    bus.emit("empty")
    assert called == [{}]


def test_list_events(bus):
    bus.subscribe("event.a", lambda d: None)
    bus.subscribe("event.b", lambda d: None)
    events = bus.list_events()
    assert "event.a" in events
    assert "event.b" in events


def test_subscriber_count(bus):
    bus.subscribe("counted", lambda d: None)
    bus.subscribe("counted", lambda d: None)
    assert bus.subscriber_count("counted") == 2


def test_clear(bus):
    bus.subscribe("to.clear", lambda d: None)
    bus.clear()
    assert bus.list_events() == []
