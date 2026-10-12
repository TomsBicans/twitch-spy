from __future__ import annotations

import logging
import sys
import threading
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

from twitch_spy.desktop import open_directory, resource_path

logger = logging.getLogger("ApplicationLogger")


def tray_enabled(requested: bool | None) -> bool:
    if sys.platform != "win32":
        if requested:
            logger.warning("The tray icon is supported only on native Windows.")
        return False
    return requested if requested is not None else bool(getattr(sys, "frozen", False))


class DesktopTray:
    def __init__(self, url: str, log_dir: Path, shutdown: Callable[[], None]) -> None:
        self.url = url
        self.log_dir = log_dir
        self.shutdown = shutdown
        self.icon: Any = None

    def _open_browser(self, *_: object) -> None:
        webbrowser.open(self.url)

    def _open_diagnostics(self, *_: object) -> None:
        webbrowser.open(f"{self.url}/#diagnostics")

    def _open_logs(self, *_: object) -> None:
        try:
            open_directory(self.log_dir)
        except OSError:
            logger.exception("Could not open log directory")

    def _quit(self, *_: object) -> None:
        self.icon.title = "Twitch Spy — stopping"
        threading.Thread(target=self.shutdown, name="tray-shutdown", daemon=True).start()

    def start(self) -> bool:
        try:
            import pystray
            from PIL import Image

            with Image.open(resource_path("packaging", "assets", "twitch-spy.png")) as source:
                artwork = source.copy()
            self.icon = pystray.Icon(
                "twitch-spy", artwork, "Twitch Spy — running",
                menu=pystray.Menu(
                    pystray.MenuItem("Open Twitch Spy", self._open_browser, default=True),
                    pystray.MenuItem("Health and resource usage", self._open_diagnostics),
                    pystray.MenuItem("Open logs folder", self._open_logs),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Quit Twitch Spy", self._quit),
                ),
            )
            ready = threading.Event()

            def setup(icon: Any) -> None:
                icon.visible = True
                ready.set()

            self.icon.run_detached(setup)
            if not ready.wait(timeout=5):
                raise RuntimeError("Windows tray did not become ready")
            logger.info("Windows tray started")
            return True
        except Exception:
            logger.exception("Tray unavailable; continuing without a tray icon")
            self.stop()
            return False

    def stop(self) -> None:
        if self.icon is not None:
            self.icon.stop()
            self.icon = None
