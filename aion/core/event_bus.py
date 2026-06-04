"""EventBus - systeme de publication/souscription d evenements pour AION."""
import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EventBus:
    """
    Bus d evenements simple pour AION.

    Permet aux services et composants de communiquer de maniere
    decouple via des evenements nommes.

    Usage:
        bus = EventBus()
        bus.subscribe("network.down", my_handler)
        bus.emit("network.down", {"host": "8.8.8.8"})
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable[[dict[str, Any]], None]) -> None:
        """Abonne un handler a un evenement."""
        if handler not in self._subscribers[event]:
            self._subscribers[event].append(handler)
            logger.debug("EventBus: subscribed to '%s'", event)

    def unsubscribe(self, event: str, handler: Callable) -> None:
        """Desabonne un handler d un evenement."""
        if event in self._subscribers and handler in self._subscribers[event]:
            self._subscribers[event].remove(handler)
            logger.debug("EventBus: unsubscribed from '%s'", event)

    def emit(self, event: str, data: dict[str, Any] | None = None) -> None:
        """Emet un evenement vers tous les handlers abonnes."""
        payload = data or {}
        handlers = self._subscribers.get(event, [])

        if not handlers:
            logger.debug("EventBus: no subscribers for '%s'", event)
            return

        logger.info("EventBus: emit '%s' -> %d handler(s)", event, len(handlers))

        for handler in handlers:
            try:
                handler(payload)
            except Exception as exc:
                logger.error(
                    "EventBus: handler %s raised an error for event '%s': %s",
                    handler.__name__,
                    event,
                    exc,
                )

    def list_events(self) -> list[str]:
        """Retourne la liste des evenements ayant au moins un abonne."""
        return [event for event, handlers in self._subscribers.items() if handlers]

    def subscriber_count(self, event: str) -> int:
        """Retourne le nombre d abonnes a un evenement."""
        return len(self._subscribers.get(event, []))

    def clear(self) -> None:
        """Supprime tous les abonnements."""
        self._subscribers.clear()
        logger.debug("EventBus: all subscribers cleared")
