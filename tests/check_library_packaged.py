"""Verify the latest Windows build with 1,600 temporary library tracks."""

import csv
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib.request import Request, urlopen

import psutil


root = Path(__file__).resolve().parents[1]
artifact = root / "dist" / json.loads((root / "dist/latest-windows.json").read_text())["artifact"]
with socket.socket() as listener:
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
base = f"http://127.0.0.1:{port}"
with tempfile.TemporaryDirectory(prefix="library-packaged-") as temporary:
    directory = Path(temporary)
    library = directory / "stream_downloads/audio_library"
    (library / "storage").mkdir(parents=True)
    (library / "thumbnails").mkdir()
    with (library / "storage/local_storage.txt").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        for index in range(1600):
            title = f"Track {index:04d}"
            writer.writerow([f"https://youtube.com/watch?v={index}", title, "None", "None"])
            (library / f"{title}.mp3").write_bytes(b"audio")
            (library / "thumbnails" / f"{title}.jpg").write_bytes(b"artwork")
    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(directory / "profile")
    env["PYINSTALLER_SUPPRESS_SPLASH_SCREEN"] = "1"
    started = time.perf_counter()
    process = subprocess.Popen(
        [str(artifact), "--no-browser", "--no-tray", "--port", str(port), "--output-dir", temporary], env=env,
    )
    ready = False
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                with urlopen(base + "/health", timeout=0.2) as response:
                    ready = json.load(response)["status"] == "ok"
                if ready:
                    break
            except OSError:
                pass
            time.sleep(0.05)
        assert ready, "Server did not become ready"
        print(f"Packaged server ready in {time.perf_counter()-started:.2f}s including extraction", flush=True)
        jobs = {}
        offset = 0
        while time.monotonic() < deadline:
            with urlopen(base + f"/library?offset={offset}", timeout=2) as response:
                page = json.load(response)
            jobs.update((job["id"], job) for job in page["jobs"])
            offset += len(page["jobs"])
            if page["next_offset"] is None and page["scan"]["state"] != "loading":
                break
            time.sleep(0.01)
        assert page["scan"] == {"state": "complete", "processed": 1600, "error": None}, page["scan"]
        assert len(jobs) == 1600, len(jobs)
        first = next(iter(jobs.values()))
        assert "thumbnail_image_in_base64" not in first
        assert urlopen(base + first["thumbnail_url"], timeout=2).read() == b"artwork"
        assert urlopen(base + "/audio/Track%200000", timeout=2).read() == b"audio"
        print("Passed: all 1600 tracks, lazy artwork, audio endpoint, completed background status", flush=True)
        log = (directory / "logs/application.log").read_text(encoding="utf-8")
        for line in log.splitlines():
            if "Restored " in line or "Application ready after" in line:
                print(line)
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
