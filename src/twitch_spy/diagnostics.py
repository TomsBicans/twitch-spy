from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import psutil


class ProcessMetrics:
    """Sample only this backend and its live descendants, at most once per second."""

    def __init__(self) -> None:
        self.process = psutil.Process()
        self.started = time.monotonic()
        self.lock = threading.Lock()
        self.previous: dict[tuple[int, float], float] = {}
        self.sampled_at: float | None = None
        self.cached: dict[str, Any] = {}

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            now = time.monotonic()
            if self.sampled_at is not None and now - self.sampled_at < 1:
                return self.cached.copy()
            processes = [self.process, *self.process.children(recursive=True)]
            rows = []
            current = {}
            for process in processes:
                try:
                    with process.oneshot():
                        identity = (process.pid, process.create_time())
                        times = process.cpu_times()
                        cpu_time = times.user + times.system
                        previous = self.previous.get(identity)
                        cpu = (
                            max(0.0, (cpu_time - previous) / (now - self.sampled_at) * 100)
                            if previous is not None and self.sampled_at is not None else None
                        )
                        rows.append({
                            "pid": process.pid, "name": process.name(),
                            "cpu_percent": round(cpu, 1) if cpu is not None else None,
                            "memory_bytes": process.memory_info().rss,
                            "threads": process.num_threads(),
                        })
                        current[identity] = cpu_time
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Short-lived FFmpeg processes may exit between enumeration and sampling.
                    continue
            self.cached = {
                "pid": self.process.pid, "uptime_seconds": int(now - self.started),
                "cpu_percent": (
                    round(sum(row["cpu_percent"] or 0 for row in rows), 1)
                    if self.sampled_at is not None else None
                ),
                "memory_bytes": sum(row["memory_bytes"] for row in rows),
                "threads": sum(row["threads"] for row in rows),
                "processes": rows,
            }
            self.previous = current
            self.sampled_at = now
            return self.cached.copy()


def recent_logs(path: Path, max_bytes: int = 64 * 1024, max_lines: int = 200) -> str:
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            start = max(0, handle.tell() - max_bytes)
            handle.seek(start)
            data = handle.read(max_bytes)
        if start:
            data = data.partition(b"\n")[2]
        return "\n".join(data.decode("utf-8", errors="replace").splitlines()[-max_lines:])
    except FileNotFoundError:
        return ""
