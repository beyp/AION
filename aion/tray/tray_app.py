"""Icone AION dans le System Tray Windows via pystray."""
import logging
import subprocess
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import pystray
from PIL import Image, ImageDraw

if TYPE_CHECKING:
    from aion.core.app import AionApp

logger = logging.getLogger(__name__)


def _create_icon_image() -> Image.Image:
    """Cree une icone AION simple si aucun fichier .ico n est disponible."""
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Cercle bleu AION
    draw.ellipse([4, 4, size - 4, size - 4], fill=(30, 144, 255), outline=(255, 255, 255), width=3)
    # Lettre A au centre
    draw.text((22, 16), "A", fill=(255, 255, 255))
    return image


class AionTrayApp:
    """
    Icone AION dans le System Tray Windows.

    Fournit un menu contextuel pour :
    - Voir le statut d AION
    - Activer / desactiver les notifications toast
    - Ouvrir le dashboard web
    - Quitter AION
    """

    def __init__(self, app: "AionApp") -> None:
        self._app = app
        self._icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None

    def _build_menu(self) -> pystray.Menu:
        """Construit le menu contextuel dynamique."""
        notifier = self._app.notifier
        notif_label = (
            "🔔 Notifications : ON  (cliquer pour desactiver)"
            if notifier.enabled
            else "🔕 Notifications : OFF (cliquer pour activer)"
        )

        return pystray.Menu(
            pystray.MenuItem(
                f"🤖 AION v{self._app.AION_VERSION}",
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: (
                    f"✅ Services : {self._app.registry.count()}  |  "
                    f"Jobs : {self._app.scheduler.job_count()}"
                ),
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                notif_label,
                self._toggle_notifications,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "🌐 Ouvrir le Dashboard",
                self._open_dashboard,
            ),
            pystray.MenuItem(
                "⚡ Lancer l API REST",
                self._start_api,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "📄 Ouvrir les logs",
                self._open_logs,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "⛔ Quitter AION",
                self._quit,
            ),
        )

    def _toggle_notifications(self, icon: pystray.Icon, item) -> None:
        """Bascule les notifications toast ON/OFF."""
        new_state = self._app.notifier.toggle()
        state_str = "activees" if new_state else "desactivees"
        logger.info("Tray: notifications %s", state_str)
        # Rafraichir le menu
        icon.menu = self._build_menu()
        icon.update_menu()
        # Notifier si on vient de reactiver
        if new_state:
            self._app.notifier.notify_info("Notifications activees ✅")

    def _open_dashboard(self, icon: pystray.Icon, item) -> None:
        """Ouvre le dashboard dans le navigateur."""
        try:
            import webbrowser
            webbrowser.open("http://127.0.0.1:8000")
        except Exception as exc:
            logger.error("Tray: impossible d ouvrir le dashboard: %s", exc)

    def _start_api(self, icon: pystray.Icon, item) -> None:
        """Lance le serveur API REST."""
        try:
            subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "aion.api.server:app",
                 "--host", "127.0.0.1", "--port", "8000"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("Tray: API REST demarree")
            self._app.notifier.notify_info("API REST demarree -> http://127.0.0.1:8000")
        except Exception as exc:
            logger.error("Tray: impossible de demarrer l API: %s", exc)

    def _open_logs(self, icon: pystray.Icon, item) -> None:
        """Ouvre le fichier de logs dans le bloc-notes."""
        try:
            log_path = Path("logs/aion.log")
            if log_path.exists():
                subprocess.Popen(["notepad.exe", str(log_path)])
            else:
                logger.warning("Tray: fichier de logs introuvable: %s", log_path)
        except Exception as exc:
            logger.error("Tray: impossible d ouvrir les logs: %s", exc)

    def _quit(self, icon: pystray.Icon, item) -> None:
        """Quitte AION proprement depuis le systray."""
        logger.info("Tray: arret demande via systray")
        self._app.notifier.notify_info("AION s arrete...")
        icon.stop()
        self._app.request_stop()

    def start(self) -> None:
        """Demarre l icone systray dans un thread separe."""
        try:
            icon_path = Path("assets/aion.ico")
            if icon_path.exists():
                image = Image.open(icon_path)
            else:
                image = _create_icon_image()

            self._icon = pystray.Icon(
                name="AION",
                icon=image,
                title="AION - AI Agent Orchestrator Node",
                menu=self._build_menu(),
            )

            self._thread = threading.Thread(
                target=self._icon.run,
                daemon=True,
                name="aion-tray",
            )
            self._thread.start()
            logger.info("Tray: icone systray demarree")

        except Exception as exc:
            logger.error("Tray: impossible de demarrer le systray: %s", exc)

    def stop(self) -> None:
        """Arrete l icone systray."""
        if self._icon:
            try:
                self._icon.stop()
                logger.info("Tray: icone systray arretee")
            except Exception as exc:
                logger.error("Tray: erreur a l arret: %s", exc)

    def update_menu(self) -> None:
        """Rafraichit le menu (appeler apres un changement d etat)."""
        if self._icon:
            try:
                self._icon.menu = self._build_menu()
                self._icon.update_menu()
            except Exception:
                pass
