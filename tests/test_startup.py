import logging
import sys
import socket
import time
from types import SimpleNamespace
from pathlib import Path

import pytest

from twitch_spy.startup import StartupProgress
from twitch_spy.desktop import bundled_ffmpeg


def test_splash_receives_logs_and_closes_once(monkeypatch):
    messages = []
    closed = []
    splash = SimpleNamespace(
        is_alive=lambda: True,
        update_text=messages.append,
        close=lambda: closed.append(True),
    )
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "pyi_splash", splash)
    progress = StartupProgress()
    try:
        logging.getLogger("startup-test").warning("Loading\nsettings")
        assert messages == ["Loading settings"]
    finally:
        progress.close()
        progress.close()
    assert closed == [True]
    assert progress not in logging.getLogger().handlers


def test_disconnected_splash_does_not_abort_startup(monkeypatch):
    def disconnected(message):
        raise OSError("Disconnected")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "pyi_splash", SimpleNamespace(
        is_alive=lambda: True, update_text=disconnected,
    ))
    progress = StartupProgress()
    progress.update("Starting")
    progress.close()


def test_frozen_ffmpeg_does_not_launch_probe(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.delenv("IMAGEIO_FFMPEG_EXE", raising=False)
    binary = tmp_path / "imageio_ffmpeg" / "binaries" / "ffmpeg-win-x86_64.exe"
    binary.parent.mkdir(parents=True)
    binary.touch()
    monkeypatch.setitem(sys.modules, "imageio_ffmpeg", None)
    assert bundled_ffmpeg() == str(binary)


def test_ffmpeg_explicit_environment_override(monkeypatch):
    monkeypatch.setenv("IMAGEIO_FFMPEG_EXE", "custom-ffmpeg")
    assert bundled_ffmpeg() == "custom-ffmpeg"


@pytest.fixture
def bootloader_interpreter():
    tkinter = pytest.importorskip("tkinter")
    interpreter = tkinter.Tcl()
    interpreter.eval("""
        set auto_path {}
        proc .root.canvas {args} {}
        proc wm {args} {set ::window_config([lindex $args 0]) [lrange $args 1 end]}
        proc winfo {command args} {
            if {$command eq "fpixels"} {return 144}
            return 1920
        }
        proc after {args} {}
        trace add variable status_text write [list canvas_text_update .root.canvas vartext]
    """)
    script = Path(__file__).resolve().parents[1] / "packaging" / "startup.tcl"
    interpreter.eval(script.read_text(encoding="utf-8"))
    return interpreter


def test_bootloader_log_wall_is_bounded_and_treats_messages_as_text(bootloader_interpreter):
    interpreter = bootloader_interpreter
    for index in range(100):
        interpreter.setvar("status_text", f"file {index} [exit]; $value\nnext line")
    lines = interpreter.splitlist(interpreter.getvar("startup_lines"))
    assert len(lines) == 8
    assert "file 99 [exit]; $value next line" in lines[-1]
    interpreter.eval("startup_tick")


def test_bootloader_scales_window_for_150_percent_display(bootloader_interpreter):
    interpreter = bootloader_interpreter
    assert interpreter.getvar("width") == 930
    assert interpreter.getvar("height") == 570
    assert interpreter.splitlist(interpreter.getvar("window_config(geometry)"))[1].startswith("930x570+")


def test_bootloader_processes_progress_and_close_over_real_socket(bootloader_interpreter):
    templates = pytest.importorskip("PyInstaller.building.splash_templates")
    interpreter = bootloader_interpreter
    interpreter.eval("proc exit {} {set ::closed 1}; set closed 0")
    interpreter.eval(templates.ipc_script)
    port = int(interpreter.getvar("env(_PYI_SPLASH_IPC)"))
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2) as connection:
            connection.sendall(b"update_text(Opening your browser...)\r\x04")
            deadline = time.monotonic() + 2
            while not int(interpreter.getvar("closed")) and time.monotonic() < deadline:
                interpreter.eval("update")
                time.sleep(0.01)
        assert int(interpreter.getvar("closed")) == 1
        assert "Opening your browser..." in interpreter.splitlist(interpreter.getvar("startup_lines"))[-1]
    finally:
        interpreter.eval("close $server_socket")
