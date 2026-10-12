import sys
from types import SimpleNamespace

from twitch_spy import cli, tray
from twitch_spy.app import Application
from twitch_spy.socket_instance import socketio


def test_tray_defaults_and_overrides(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert tray.tray_enabled(None)
    assert not tray.tray_enabled(False)
    monkeypatch.setattr(sys, "frozen", False)
    assert not tray.tray_enabled(None)
    assert tray.tray_enabled(True)
    monkeypatch.setattr(sys, "platform", "linux")
    assert not tray.tray_enabled(True)


def test_cli_tray_switches(monkeypatch):
    for argument, expected in (([], None), (["--tray"], True), (["--no-tray"], False)):
        monkeypatch.setattr(sys, "argv", ["twitch-spy", *argument])
        assert cli.parse_args().tray is expected


def test_tray_keeps_backend_alive_without_browser(monkeypatch):
    application = Application()
    application.keep_running = True
    stopped = []
    monkeypatch.setattr(application, "request_shutdown", lambda: stopped.append(True))
    try:
        client = socketio.test_client(application.app)
        client.disconnect()
        application._shutdown_if_idle()
        assert application.disconnect_timer is None
        assert not stopped
    finally:
        application.job_manager.shutdown()


def test_tray_actions_and_cleanup(monkeypatch, tmp_path):
    calls = []

    class Image:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def copy(self):
            return self

    class Icon:
        def __init__(self, *_args, **_kwargs):
            pass

        def run_detached(self, setup):
            setup(self)

        def stop(self):
            calls.append("stopped")

    class Menu:
        SEPARATOR = None

        def __init__(self, *_args):
            pass

    monkeypatch.setitem(sys.modules, "pystray", SimpleNamespace(Icon=Icon, Menu=Menu, MenuItem=lambda *a, **kw: a))
    monkeypatch.setitem(sys.modules, "PIL", SimpleNamespace(Image=SimpleNamespace(open=lambda _: Image())))
    monkeypatch.setattr(tray.webbrowser, "open", calls.append)
    monkeypatch.setattr(tray, "open_directory", calls.append)
    desktop = tray.DesktopTray("http://localhost:5173", tmp_path, lambda: None)
    assert desktop.start()
    desktop._open_browser()
    desktop._open_diagnostics()
    desktop._open_logs()
    desktop.stop()
    desktop.stop()
    assert calls == ["http://localhost:5173", "http://localhost:5173/#diagnostics", tmp_path, "stopped"]
