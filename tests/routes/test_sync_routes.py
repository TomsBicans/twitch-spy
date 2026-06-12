import threading

import pytest

from twitch_spy.app import Application
from twitch_spy.routes import sync_routes


def make_application(tmp_path):
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    return Application(frontend_dir=frontend)


def valid_plan_payload():
    return {
        "dirs_to_create": [],
        "files_to_transfer": [],
        "skipped_count": 0,
        "total_transfer_bytes": 0,
    }


@pytest.mark.parametrize(
    "message",
    ["ADB was not found", "ADB could not list devices: access denied"],
)
def test_plan_returns_json_503_when_adb_cannot_start(monkeypatch, tmp_path, message):
    application = make_application(tmp_path)

    class Syncer:
        def device_connected(self):
            raise RuntimeError(message)

    monkeypatch.setattr(sync_routes, "_syncer", Syncer)
    response = application.app.test_client().post("/sync/plan")

    assert response.status_code == 503
    assert response.json == {"error": message}
    application.job_manager.shutdown()


def test_plan_returns_json_503_when_no_device_is_connected(monkeypatch, tmp_path):
    application = make_application(tmp_path)

    class Syncer:
        def device_connected(self):
            return False

    monkeypatch.setattr(sync_routes, "_syncer", Syncer)
    response = application.app.test_client().post("/sync/plan")

    assert response.status_code == 503
    assert response.json == {"error": "No Android device connected via adb"}
    application.job_manager.shutdown()


def test_execute_rejects_overlapping_sync(monkeypatch, tmp_path):
    application = make_application(tmp_path)
    started = threading.Event()
    release = threading.Event()

    class Result:
        def to_dict(self):
            return {"uploaded": 0, "skipped": 0, "failed": 0, "errors": []}

    class Syncer:
        def execute_plan(self, _plan, progress_callback):
            started.set()
            release.wait(timeout=2)
            return Result()

    monkeypatch.setattr(sync_routes, "_syncer", Syncer)
    client = application.app.test_client()
    first = client.post("/sync/execute", json=valid_plan_payload())
    assert first.status_code == 202
    assert started.wait(timeout=1)

    second = client.post("/sync/execute", json=valid_plan_payload())
    assert second.status_code == 409
    assert second.json == {"error": "Android synchronization is already running"}

    release.set()
    thread = application.sync_thread
    if thread:
        thread.join(timeout=2)
    assert not application.has_active_sync()
    application.job_manager.shutdown()
