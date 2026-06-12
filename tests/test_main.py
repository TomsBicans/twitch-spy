from types import SimpleNamespace

import pytest

import twitch_spy.cli as cli
import twitch_spy.desktop as desktop
import twitch_spy.main as main_module


def test_existing_instance_is_checked_before_explicit_port(monkeypatch, tmp_path):
    existing = desktop.InstanceInfo(pid=1234, url="http://127.0.0.1:5000")

    class Lock:
        def __init__(self, _path):
            pass

        def read(self):
            return existing

    args = SimpleNamespace(
        output_dir=str(tmp_path),
        android_dest="/sdcard/Music",
        port=5000,
        no_browser=False,
        adb_exe="adb",
        ffmpeg_location="ffmpeg",
        check_tools=False,
        dev=False,
    )
    opened = []
    monkeypatch.setattr(cli, "parse_args", lambda: args)
    monkeypatch.setattr(desktop, "InstanceLock", Lock)
    monkeypatch.setattr(desktop, "user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(desktop, "select_port", lambda _port: pytest.fail("port must not be bound"))
    monkeypatch.setattr(main_module.psutil, "pid_exists", lambda pid: pid == 1234)
    monkeypatch.setattr(main_module.webbrowser, "open", opened.append)

    main_module.main()

    assert opened == [existing.url]
