"""Service timer - compte a rebours avec notification et bip de fin."""
import threading
import time
from typing import Any

from aion.services.base_service import BaseService


def _parse_duration(raw: str) -> int | None:
    """
    Parse une duree en secondes depuis plusieurs formats :
      "5m", "30s", "1h", "1h30m", "90", "2m30s", "1:30"
    Retourne None si invalide.
    """
    raw = raw.strip().lower().replace(" ", "")
    if not raw:
        return None

    total = 0

    # Format mm:ss ou hh:mm:ss
    if ":" in raw:
        parts = raw.split(":")
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
            return None

    # Format avec unites : 1h30m45s
    import re
    pattern = re.findall(r"(\d+)([hms]?)", raw)
    has_unit = any(unit for _, unit in pattern)

    if has_unit:
        for value, unit in pattern:
            v = int(value)
            if unit == "h":
                total += v * 3600
            elif unit == "m":
                total += v * 60
            elif unit == "s" or unit == "":
                total += v
        return total if total > 0 else None

    # Nombre seul → secondes
    try:
        v = int(raw)
        return v if v > 0 else None
    except ValueError:
        return None


def _fmt_duration(seconds: int) -> str:
    """Formatte une duree en texte lisible."""
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}m{s:02d}s" if s else f"{m}m"
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    if s:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{h}h{m:02d}m"
    return f"{h}h"


def _beep(count: int = 3) -> None:
    """Emet des bips systeme (Windows winsound ou fallback ASCII)."""
    try:
        import winsound
        for _ in range(count):
            winsound.Beep(880, 300)
            time.sleep(0.15)
    except Exception:
        try:
            # Fallback : bip ASCII + son systeme
            import ctypes
            for _ in range(count):
                ctypes.windll.user32.MessageBeep(0)
                time.sleep(0.2)
        except Exception:
            # Dernier recours : caractere ASCII bip
            for _ in range(count):
                print("\a", end="", flush=True)
                time.sleep(0.2)


class TimerService(BaseService):
    """
    Compte a rebours avec notification et bip de fin.

    Payload :
        duration : str  - Duree (ex: "5m", "30s", "1h30m", "2:30", "90")
        message  : str  - Message de notification (defaut: "Temps ecoule !")
        beeps    : int  - Nombre de bips (defaut: 3, 0 pour desactiver)

    Exemples :
        run timer {"duration": "5m"}
        run timer {"duration": "25m", "message": "Pause Pomodoro !", "beeps": 5}
        run timer {"duration": "1:30", "message": "Reunion dans 30s"}
    """

    name        = "timer"
    description = "Compte a rebours avec notification toast et bip de fin"
    permissions = []
    domain      = "timer"

    # Timers actifs : {timer_id: {"thread": t, "remaining": n, "message": m}}
    _active_timers: dict[str, dict] = {}
    _lock = threading.Lock()

    def execute(self, payload: dict[str, Any]) -> str:
        duration_raw = str(payload.get("duration", "")).strip()
        message      = payload.get("message", "Temps ecoule !").strip()
        beeps        = int(payload.get("beeps", 3))

        if not duration_raw:
            return (
                "timer : duree obligatoire.\n"
                "  Exemples : timer 5m | timer 25m Pause ! | timer 1:30"
            )

        seconds = _parse_duration(duration_raw)
        if seconds is None or seconds <= 0:
            return (
                f"timer : duree invalide : {duration_raw!r}\n"
                "  Formats : 5m | 30s | 1h30m | 1:30 | 90 (secondes)"
            )

        duration_str = _fmt_duration(seconds)
        timer_id     = f"timer_{len(self._active_timers) + 1}"

        def _run():
            with self._lock:
                self._active_timers[timer_id] = {
                    "remaining": seconds,
                    "message":   message,
                    "duration":  duration_str,
                }

            # Decompte
            remaining = seconds
            while remaining > 0:
                with self._lock:
                    if timer_id not in self._active_timers:
                        return  # annule
                    self._active_timers[timer_id]["remaining"] = remaining
                time.sleep(1)
                remaining -= 1

            # Fin du timer
            with self._lock:
                self._active_timers.pop(timer_id, None)

            # Bips
            if beeps > 0:
                _beep(beeps)

            # Notification toast
            try:
                from aion.notifications.notifier import AionNotifier
                notifier = AionNotifier()
                notifier.notify(
                    title=f"⏰ AION Timer — {duration_str}",
                    message=message,
                    duration=8,
                )
            except Exception:
                pass

            # Log console
            print(f"\n⏰ Timer {duration_str} termine : {message}")
            print("AION> ", end="", flush=True)

        t = threading.Thread(target=_run, daemon=True, name=f"aion-{timer_id}")
        t.start()

        return (
            f"⏰ Timer demarre : {duration_str}\n"
            f"   Message  : {message}\n"
            f"   ID       : {timer_id}\n"
            f"   Annuler  : timer cancel {timer_id}"
        )

    @classmethod
    def list_timers(cls) -> dict:
        with cls._lock:
            return dict(cls._active_timers)

    @classmethod
    def cancel_timer(cls, timer_id: str) -> bool:
        with cls._lock:
            if timer_id in cls._active_timers:
                del cls._active_timers[timer_id]
                return True
            return False
