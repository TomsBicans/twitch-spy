from __future__ import annotations

import logging
import sys
import threading
import time
from types import ModuleType


class StartupProgress(logging.Handler):
    """Forward bounded startup messages to the bootloader's splash window."""

    def __init__(self) -> None:
        super().__init__(logging.INFO)
        self.started = time.perf_counter()
        self._mutex = threading.RLock()
        self._splash: ModuleType | None = None
        if getattr(sys, "frozen", False) and sys.platform == "win32":
            import pyi_splash

            self._splash = pyi_splash
        logging.getLogger().addHandler(self)

    def emit(self, record: logging.LogRecord) -> None:
        self.update(record.getMessage())

    def update(self, message: str) -> None:
        with self._mutex:
            if self._splash is not None and self._splash.is_alive():
                clean = " ".join(message.split())[:160]
                try:
                    self._splash.update_text(clean)
                except (OSError, RuntimeError):
                    # A dismissed/disconnected splash must not prevent startup.
                    self._splash = None

    def close(self) -> None:
        logging.getLogger().removeHandler(self)
        with self._mutex:
            if self._splash is not None:
                try:
                    self._splash.close()
                except (OSError, RuntimeError):
                    self._splash = None
                self._splash = None
        super().close()
