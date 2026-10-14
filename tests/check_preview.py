"""Check the latest Windows build: make check-preview (requires Microsoft Edge)."""

import json
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright

from scripts.build import selected_artifacts

root = Path(__file__).resolve().parents[1]
artifact = selected_artifacts(root, "windows")[0]
with socket.socket() as candidate:
    candidate.bind(("127.0.0.1", 0))
    port = candidate.getsockname()[1]
base = f"http://127.0.0.1:{port}"
with tempfile.TemporaryDirectory(prefix="twitch-spy-ui-") as data:
    process = subprocess.Popen([
        str(artifact),
        "--no-browser", "--port", str(port), "--output-dir", data,
    ], creationflags=subprocess.CREATE_NO_WINDOW, env={**os.environ, "LOCALAPPDATA": str(Path(data) / "profile")})
    try:
        for _ in range(150):
            try:
                with urlopen(f"{base}/health", timeout=1):
                    break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("Backend did not start")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, channel="msedge")
            page = browser.new_page(viewport={"width": 1440, "height": 1080})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"{base}/#diagnostics")
            page.get_by_role("heading", name="Health and resource usage").wait_for()
            page.get_by_text("Backend running", exact=False).wait_for()
            page.get_by_text("Windows tray started", exact=False).wait_for()
            page.get_by_role("button", name="Pause", exact=True).click()
            page.get_by_role("button", name="Resume", exact=True).wait_for()
            page.screenshot(path=str(root / "dist/diagnostics-preview.png"), full_page=True)
            page.get_by_role("button", name="Close", exact=True).click()
            assert page.get_by_role("heading", name="Health and resource usage").count() == 0
            page.get_by_role("button", name="Health and logs", exact=True).click()
            page.get_by_role("heading", name="Health and resource usage").wait_for()
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(root / "dist/diagnostics-mobile.png"), full_page=True)
            assert page.get_by_role("region", name="Health and resource usage").evaluate("e => e.getBoundingClientRect().right <= innerWidth")
            token = page.locator('meta[name="twitch-spy-shutdown-token"]').get_attribute("content")
            request = Request(f"{base}/diagnostics", headers={
                "X-Twitch-Spy-Shutdown": token, "X-Twitch-Spy-Diagnostics": "1",
            })
            with urlopen(request) as response:
                snapshot = json.load(response)
            assert snapshot["tray_active"]
            assert snapshot["memory_bytes"] > 0
            assert not errors, errors
            browser.close()
        request = Request(f"{base}/shutdown", method="POST", headers={"X-Twitch-Spy-Shutdown": token})
        urlopen(request).close()
        process.wait(timeout=15)
        assert process.returncode == 0
        print("Packaged tray, desktop/mobile diagnostics, pause, navigation and shutdown passed")
    finally:
        if process.poll() is None:
            html = urlopen(base).read().decode()
            token = html.split('name="twitch-spy-shutdown-token" content="', 1)[1].split('"', 1)[0]
            urlopen(Request(f"{base}/shutdown", method="POST", headers={"X-Twitch-Spy-Shutdown": token})).close()
            process.wait(timeout=15)
