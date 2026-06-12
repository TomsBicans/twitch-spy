import json
import os
from pathlib import Path

from twitch_spy.desktop import InstanceLock, resource_path, select_port, user_data_dir


def test_user_data_directories():
    assert user_data_dir("win32", {"LOCALAPPDATA": "C:/Users/test/AppData/Local"}) == Path("C:/Users/test/AppData/Local/TwitchSpy")
    assert user_data_dir("linux", {"XDG_DATA_HOME": "/tmp/share"}) == Path("/tmp/share/twitch-spy")


def test_resource_path_uses_frozen_root(monkeypatch, tmp_path):
    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)
    assert resource_path("client", "dist") == tmp_path / "client" / "dist"


def test_select_port_returns_bindable_port(monkeypatch):
    class FakeSocket:
        def __enter__(self): return self
        def __exit__(self, *_args): pass
        def bind(self, address): assert address == ("127.0.0.1", 0)
        def getsockname(self): return ("127.0.0.1", 43210)

    monkeypatch.setattr("twitch_spy.desktop.socket.socket", lambda *_args: FakeSocket())
    assert select_port() == 43210


def test_instance_lock_returns_running_instance(tmp_path):
    path = tmp_path / "instance.json"
    first = InstanceLock(path)
    assert first.acquire("http://127.0.0.1:1234") is None
    second = InstanceLock(path)
    existing = second.acquire("http://127.0.0.1:5678")
    assert existing.pid == os.getpid()
    assert existing.url.endswith(":1234")
    first.release()


def test_instance_lock_replaces_stale_file(tmp_path):
    path = tmp_path / "instance.json"
    path.write_text(json.dumps({"pid": 99999999, "url": "old"}), encoding="utf-8")
    lock = InstanceLock(path)
    assert lock.acquire("new") is None
    lock.release()
