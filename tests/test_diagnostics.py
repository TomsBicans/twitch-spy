from types import SimpleNamespace

import pytest

from twitch_spy.app import Application
from twitch_spy.diagnostics import ProcessMetrics, recent_logs
import twitch_spy.diagnostics as diagnostics


def test_diagnostics_requires_headers_and_packaged_token():
    application = Application()
    try:
        client = application.app.test_client()
        assert client.get("/diagnostics").status_code == 403
        assert client.get("/diagnostics", headers={"X-Twitch-Spy-Diagnostics": "1"}).status_code == 403
        response = client.get("/diagnostics", headers={
            "X-Twitch-Spy-Diagnostics": "1",
            "X-Twitch-Spy-Shutdown": application.shutdown_token,
        })
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert response.json["memory_bytes"] > 0
        assert response.json["cpu_percent"] is None
        assert response.json["status"] == "running"
    finally:
        application.job_manager.shutdown()


def test_development_diagnostics_requires_custom_header():
    application = Application(development=True)
    try:
        client = application.app.test_client()
        assert client.get("/diagnostics").status_code == 403
        assert client.get("/diagnostics", headers={"X-Twitch-Spy-Diagnostics": "1"}).status_code == 200
    finally:
        application.job_manager.shutdown()


def test_logs_are_bounded_and_missing_file_is_empty(tmp_path):
    path = tmp_path / "application.log"
    assert recent_logs(path) == ""
    path.write_text("old entry\n" * 100 + "latest\n", encoding="utf-8")
    assert recent_logs(path, max_bytes=40, max_lines=2) == "old entry\nlatest"


def test_metrics_include_children_and_handle_process_exit(monkeypatch):
    clock = [10.0]
    cpu_time = [1.0]

    class Process:
        pid = 42

        def __init__(self, pid=42):
            self.pid = pid

        def children(self, recursive):
            return [Process(43), Process(44)]

        def oneshot(self):
            from contextlib import nullcontext
            return nullcontext()

        def create_time(self):
            if self.pid == 44:
                raise diagnostics.psutil.NoSuchProcess(44)
            return 1.0

        def cpu_times(self):
            return SimpleNamespace(user=cpu_time[0], system=0.0)

        def memory_info(self):
            return SimpleNamespace(rss=1024)

        def name(self):
            return "backend" if self.pid == 42 else "ffmpeg"

        def num_threads(self):
            return 2

    monkeypatch.setattr(diagnostics.psutil, "Process", Process)
    monkeypatch.setattr(diagnostics.time, "monotonic", lambda: clock[0])
    metrics = ProcessMetrics()
    first = metrics.snapshot()
    assert first["cpu_percent"] is None
    assert first["memory_bytes"] == 2048
    assert metrics.snapshot() == first
    clock[0] += 2
    cpu_time[0] += 1
    assert metrics.snapshot()["cpu_percent"] == pytest.approx(100)
    assert metrics.snapshot()["threads"] == 4
