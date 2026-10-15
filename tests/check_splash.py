"""Check the latest Windows build's splash lifecycle and capture its rendering."""

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.request import Request, urlopen

from PIL import ImageGrab
import psutil

from scripts.build import available_port


user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
user32.GetWindowDpiAwarenessContext.argtypes = [wintypes.HWND]
user32.GetWindowDpiAwarenessContext.restype = ctypes.c_void_p
user32.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
user32.GetDpiForWindow.argtypes = [wintypes.HWND]
callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
root = Path(__file__).resolve().parents[1]
artifact = root / "dist" / json.loads((root / "dist/latest-windows.json").read_text())["artifact"]
port = available_port()
base = f"http://127.0.0.1:{port}"
with tempfile.TemporaryDirectory(prefix="splash-check-") as temporary:
    env = os.environ.copy()
    env["LOCALAPPDATA"] = temporary
    env.pop("PYINSTALLER_SUPPRESS_SPLASH_SCREEN", None)
    process = subprocess.Popen([str(artifact), "--port", str(port), "--output-dir", temporary], env=env)
    seen = False
    ready = False
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            pids = {process.pid, *(child.pid for child in psutil.Process(process.pid).children(recursive=True))}
            windows = []

            @callback_type
            def inspect(hwnd: int, _: int) -> bool:
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                title = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(hwnd, title, 256)
                if pid.value in pids and title.value == "Twitch Spy is starting" and user32.IsWindowVisible(hwnd):
                    windows.append(hwnd)
                return True

            user32.EnumWindows(inspect, 0)
            if windows and not seen:
                hwnd = windows[0]
                awareness = user32.GetAwarenessFromDpiAwarenessContext(user32.GetWindowDpiAwarenessContext(hwnd))
                assert awareness == 1, awareness
                print("Splash DPI:", user32.GetDpiForWindow(hwnd), "awareness:", awareness, flush=True)
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom)).save(root / "dist/startup-fixed.png")
                seen = True
            try:
                with urlopen(base + "/health", timeout=0.2) as response:
                    ready = json.load(response)["status"] == "ok"
            except OSError:
                pass
            if ready and seen and not windows:
                break
            time.sleep(0.05)
        assert seen, "Splash never appeared"
        assert ready, "Server did not become ready"
        assert not windows, "Splash remained visible after server became ready"
        assert process.poll() is None, "Application exited unexpectedly"
        print("Packaged splash appeared, used native DPI, and closed while app remained running.", flush=True)
    finally:
        if ready:
            html = urlopen(base, timeout=2).read().decode()
            token = html.split('name="twitch-spy-shutdown-token" content="', 1)[1].split('"', 1)[0]
            request = Request(base + "/shutdown", method="POST", headers={"X-Twitch-Spy-Shutdown": token})
            urlopen(request, timeout=2).read()
            process.wait(timeout=10)
        elif process.poll() is None:
            for child in psutil.Process(process.pid).children(recursive=True):
                child.terminate()
            process.terminate()
            process.wait(timeout=10)
