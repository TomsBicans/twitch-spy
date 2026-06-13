import twitch_spy.app as app_module
from twitch_spy.app import Application
from twitch_spy.socket_instance import socketio


def test_health_frontend_spa_and_shutdown_auth(tmp_path):
    frontend = tmp_path / "dist"
    (frontend / "assets").mkdir(parents=True)
    (frontend / "index.html").write_text('<meta name="twitch-spy-shutdown-token" content="__TWITCH_SPY_SHUTDOWN_TOKEN__"><div id="root"></div>', encoding="utf-8")
    (frontend / "assets" / "app.js").write_text("ok", encoding="utf-8")
    application = Application(frontend_dir=frontend)
    client = application.app.test_client()

    assert client.get("/health").json["status"] == "ok"
    assert client.get("/assets/app.js").data == b"ok"
    assert b'id="root"' in client.get("/client/route").data
    assert client.get("/socket.io/?EIO=4&transport=polling").status_code == 200
    assert client.post("/shutdown").status_code == 403
    assert client.post("/open-music-directory").status_code == 403


def test_open_music_directory_uses_configured_library(monkeypatch, tmp_path):
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    application = Application(frontend_dir=frontend)
    opened = []
    monkeypatch.setattr(app_module, "open_directory", opened.append)

    response = application.app.test_client().post(
        "/open-music-directory",
        headers={"X-Twitch-Spy-Shutdown": application.shutdown_token},
    )

    assert response.status_code == 200
    assert response.json == {"status": "opened"}
    assert opened == [app_module.config.AUDIO_LIBRARY]
    application.job_manager.shutdown()


def test_open_music_directory_returns_json_error(monkeypatch, tmp_path):
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    application = Application(frontend_dir=frontend)
    monkeypatch.setattr(
        app_module,
        "open_directory",
        lambda _path: (_ for _ in ()).throw(OSError("file manager unavailable")),
    )

    response = application.app.test_client().post(
        "/open-music-directory",
        headers={"X-Twitch-Spy-Shutdown": application.shutdown_token},
    )

    assert response.status_code == 503
    assert "file manager unavailable" in response.json["error"]
    application.job_manager.shutdown()


def test_development_can_open_music_directory_without_packaged_token(monkeypatch, tmp_path):
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    application = Application(frontend_dir=frontend, development=True)
    opened = []
    monkeypatch.setattr(app_module, "open_directory", opened.append)

    response = application.app.test_client().post("/open-music-directory")

    assert response.status_code == 200
    assert opened == [app_module.config.AUDIO_LIBRARY]
    application.job_manager.shutdown()


def test_development_mode_accepts_vite_socket_origin(tmp_path):
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    application = Application(frontend_dir=frontend, development=True)
    client = application.app.test_client()

    response = client.get(
        "/socket.io/?EIO=4&transport=polling",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200


def test_development_disconnect_does_not_schedule_shutdown(monkeypatch, tmp_path):
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    application = Application(frontend_dir=frontend, development=True)
    timers = []
    monkeypatch.setattr(app_module.threading, "Timer", lambda *_args, **_kwargs: timers.append(True))

    client = socketio.test_client(application.app)
    client.disconnect()

    assert timers == []
    application.job_manager.shutdown()


def test_packaged_disconnect_schedules_shutdown(monkeypatch, tmp_path):
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    application = Application(frontend_dir=frontend)
    timers = []

    class Timer:
        daemon = False

        def __init__(self, delay, callback):
            timers.append((delay, callback))

        def start(self):
            pass

    monkeypatch.setattr(app_module.threading, "Timer", Timer)
    client = socketio.test_client(application.app)
    client.disconnect()

    assert len(timers) == 1
    assert timers[0][0] == application.disconnect_grace
    application.job_manager.shutdown()


def test_sync_lifecycle_rejects_overlap_and_clears_after_failure(tmp_path):
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    application = Application(frontend_dir=frontend)
    started = app_module.threading.Event()
    release = app_module.threading.Event()

    def active_sync():
        started.set()
        release.wait(timeout=2)

    assert application.start_sync(active_sync)
    assert started.wait(timeout=1)
    assert application.has_active_sync()
    assert not application.start_sync(lambda: None)
    release.set()
    application.sync_thread.join(timeout=2)
    assert not application.has_active_sync()

    failed = app_module.threading.Event()

    def failing_sync():
        try:
            raise RuntimeError("sync failed")
        finally:
            failed.set()

    assert application.start_sync(failing_sync)
    assert failed.wait(timeout=1)
    application.sync_thread.join(timeout=2) if application.sync_thread else None
    assert not application.has_active_sync()
    application.job_manager.shutdown()


def test_server_exit_shuts_down_download_workers(monkeypatch, tmp_path):
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    application = Application(frontend_dir=frontend)
    calls = []

    class Server:
        def serve_forever(self):
            calls.append("serve")

    monkeypatch.setattr(app_module, "make_server", lambda *_args, **_kwargs: Server())
    monkeypatch.setattr(application.job_manager, "shutdown", lambda: calls.append("shutdown"))

    application.main_web(port=5000)

    assert calls == ["serve", "shutdown"]
