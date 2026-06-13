from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse
from urllib.request import urlopen
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import psutil


def resource_path(*parts: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root.joinpath(*parts)


def user_data_dir(platform: str | None = None, environ: dict[str, str] | None = None) -> Path:
    platform = platform or sys.platform
    environ = environ or os.environ
    if platform == "win32":
        root = environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(root) / "TwitchSpy"
    root = environ.get("XDG_DATA_HOME")
    return Path(root) / "twitch-spy" if root else Path.home() / ".local" / "share" / "twitch-spy"


def select_port(preferred: int | None = None) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", preferred or 0))
        return int(sock.getsockname()[1])


@dataclass(frozen=True)
class InstanceInfo:
    pid: int
    url: str
    process_started_at: float | None = None


def instance_health_matches(url: str, timeout: float = 0.5) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        return False
    try:
        with urlopen(f"{url.rstrip('/')}/health", timeout=timeout) as response:
            payload = json.load(response)
        return response.status == 200 and payload.get("status") == "ok"
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def process_identity_matches(info: InstanceInfo) -> bool:
    if info.process_started_at is None:
        return False
    try:
        actual = psutil.Process(info.pid).create_time()
    except (psutil.Error, OSError):
        return False
    return abs(actual - info.process_started_at) < 0.01


class InstanceLock:
    def __init__(self, path: Path):
        self.path = path
        self.acquired = False

    def acquire(self, url: str) -> InstanceInfo | None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                existing = self.running_instance()
                if existing:
                    return existing
                self.path.unlink(missing_ok=True)
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "pid": os.getpid(),
                        "url": url,
                        "process_started_at": psutil.Process().create_time(),
                    },
                    handle,
                )
            self.acquired = True
            return None
        raise RuntimeError(f"Could not acquire instance lock: {self.path}")

    def read(self) -> InstanceInfo | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            started_at = data.get("process_started_at")
            return InstanceInfo(
                pid=int(data["pid"]),
                url=str(data["url"]),
                process_started_at=float(started_at) if started_at is not None else None,
            )
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None

    def running_instance(self) -> InstanceInfo | None:
        existing = self.read()
        if not existing or not psutil.pid_exists(existing.pid):
            return None
        if process_identity_matches(existing) or instance_health_matches(existing.url):
            return existing
        return None

    def release(self) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)
            self.acquired = False


def wait_until_ready(url: str, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{url}/health", timeout=1) as response:
                if response.status == 200:
                    return True
        except OSError:
            time.sleep(0.1)
    return False


def bundled_adb() -> str:
    name = "adb.exe" if sys.platform == "win32" else "adb"
    candidate = resource_path("platform-tools", name)
    return str(candidate) if candidate.exists() else name


def bundled_ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def open_when_ready(url: str, opener: Callable[[str], object]) -> None:
    if wait_until_ready(url):
        opener(url)


def is_wsl() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    release = platform.release().lower()
    return "microsoft" in release or "wsl" in release


def open_directory(directory: str | Path) -> None:
    path = Path(directory).resolve()
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    if is_wsl():
        converted = subprocess.run(
            ["wslpath", "-w", str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        subprocess.Popen(
            ["explorer.exe", converted],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    subprocess.Popen(
        ["xdg-open", str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
