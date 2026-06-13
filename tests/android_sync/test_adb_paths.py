import subprocess

from twitch_spy.android_sync.adb_sync import AndroidLibrarySync


def test_native_adb_push_uses_native_path(monkeypatch):
    syncer = AndroidLibrarySync(adb_exe="adb")
    calls = []
    monkeypatch.setattr(syncer, "_run", lambda args, **_kwargs: calls.append(args) or subprocess.CompletedProcess(args, 0, "", ""))
    monkeypatch.setattr(syncer, "_uses_windows_adb_from_wsl", lambda: False)
    assert syncer.push_file("/tmp/song.mp3", "/sdcard/song.mp3")
    assert calls[-1][2] == "/tmp/song.mp3"


def test_wsl_windows_adb_converts_path(monkeypatch):
    syncer = AndroidLibrarySync(adb_exe="adb.exe")
    calls = []
    monkeypatch.setattr(syncer, "_run", lambda args, **_kwargs: calls.append(args) or subprocess.CompletedProcess(args, 0, "", ""))
    monkeypatch.setattr(syncer, "_uses_windows_adb_from_wsl", lambda: True)
    monkeypatch.setattr(syncer, "_wsl_to_windows", lambda _path: "C:\\song.mp3")
    assert syncer.push_file("/tmp/song.mp3", "/sdcard/song.mp3")
    assert calls[-1][2] == "C:\\song.mp3"
