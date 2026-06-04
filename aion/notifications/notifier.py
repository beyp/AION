"""Gestionnaire de notifications AION - Toast Windows + logs."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class AionNotifier:
    """
    Gestionnaire de notifications pour AION.

    Supporte les notifications toast Windows (plyer).
    Les notifications peuvent etre activees/desactivees via le systray
    ou directement via enable() / disable().

    Usage:
        notifier = AionNotifier()
        notifier.notify("Titre", "Message")
        notifier.enabled = False  # desactiver
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._toaster = None
        self._init_toaster()

    def _init_toaster(self) -> None:
        """Initialise plyer si disponible."""
        try:
            from plyer import notification
            self._toaster = notification
            logger.debug("Notifier: plyer initialise")
        except ImportError:
            logger.warning(
                "Notifier: plyer non disponible - "
                "installez-le avec: pip install plyer"
            )
            self._toaster = None

    def notify(
        self,
        title: str,
        message: str,
        duration: int = 5,
        icon_path: str | None = None,
    ) -> None:
        logger.info("Notification: [%s] %s", title, message)

        if not self.enabled:
            logger.debug("Notifier: notifications desactivees, skipped.")
            return

        if self._toaster is None:
            logger.debug("Notifier: toaster non disponible, skipped.")
            return

        try:
            self._toaster.notify(
                title=title,
                message=message,
                app_name="AION",
                timeout=duration,
            )
        except Exception as exc:
            logger.error("Notifier: erreur lors de l envoi: %s", exc)

    def notify_alert(self, message: str) -> None:
        """Notification d alerte (priorite haute)."""
        self.notify("⚠️ AION Alert", message, duration=8)

    def notify_info(self, message: str) -> None:
        """Notification d information."""
        self.notify("🤖 AION", message, duration=4)

    def toggle(self) -> bool:
        """Bascule l etat des notifications. Retourne le nouvel etat."""
        self.enabled = not self.enabled
        state = "activees" if self.enabled else "desactivees"
        logger.info("Notifier: notifications %s", state)
        return self.enabled

    @property
    def available(self) -> bool:
        """Indique si plyer est disponible."""
        return self._toaster is not None
