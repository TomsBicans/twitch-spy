# twitch-spy

A self-hosted music library manager. Paste YouTube URLs — individual videos, playlists, or channels — and the system
downloads, tags, and organizes them into a local audio library with a real-time web UI.

---

## Features

- **Bulk URL ingestion** — accepts single videos, playlists, channels, and mixed input (newline or comma separated).
  JSON arrays are also parsed automatically.
- **Atomization** — any input is broken down into the smallest downloadable unit (individual tracks) before processing.
  Playlists expand into per-track jobs automatically.
- **Parallel downloads** — jobs run concurrently via a thread pool, maximizing throughput on network-bound workloads.
- **Deduplication** — URLs are normalized (e.g. `music.youtube.com` → `www.youtube.com`) and checked against the local
  archive before queuing, so re-submitting the same tracks is safe.
- **Metadata & thumbnails** — each track gets its title and cover art embedded via yt-dlp and ffmpeg.
- **Real-time UI** — a React frontend receives live job status updates over Socket.IO. The library grid, queue counters,
  and now-playing dock all update without polling.
- **Android sync** — one-way library sync to an Android device over ADB. The UI computes a sync plan (new files,
  directories to create, bytes to transfer) before executing, with per-file progress reporting.
- **Audio player** — built-in browser player with album-art-derived ambient color, progress bar, and volume control.

---

## Preview

![Library UI](docs/ui_preview.jpg)

---

## Stack

| Layer              | Technology                                        |
|--------------------|---------------------------------------------------|
| Backend            | Python · Flask · Flask-SocketIO · yt-dlp · ffmpeg |
| Frontend           | React · TypeScript · Vite · Socket.IO client      |
| Package management | uv (Python) · npm (frontend)                      |
| Android sync       | adb (WSL-compatible)                              |

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv)
- ffmpeg

Prebuilt desktop releases do not require Python, Node.js, FFmpeg, or ADB to be installed.

```bash
# Install ffmpeg (Debian/Ubuntu/WSL)
make install-ffmpeg
```

---

## Installation

```bash
# Install Python dependencies
make install

# Install frontend dependencies
cd client && npm install
```

---

## Running

Start the API server and the frontend dev server in two separate terminals:

```bash
# Terminal 1 — backend (Flask + Socket.IO)
make run_api

# Terminal 2 — frontend (Vite dev server)
make run_web
```

Then open [http://localhost:5173](http://localhost:5173) in your browser.

`make run_api` fixes the development backend at `127.0.0.1:5000`, which is where the Vite proxy sends API and Socket.IO traffic. It also passes `--no-browser` and `--dev`, because Vite owns the development UI at port 5173 and needs its origin enabled for Socket.IO. Packaged desktop builds still select an available port and open the browser automatically.

The `--output-dir` flag (set in the Makefile) controls where the development library and logs are written. It is `./data` for `make run_api`.

### Desktop releases

Version tags publish native x86_64 artifacts for Windows and Linux:

- `twitch-spy-vX.Y.Z-windows-x64.exe`
- `twitch-spy-vX.Y.Z-linux-x86_64.AppImage`

The desktop application opens its local UI in the default browser and stores persistent data in `%LOCALAPPDATA%\TwitchSpy` on Windows or `$XDG_DATA_HOME/twitch-spy` on Linux (defaulting to `~/.local/share/twitch-spy`). Use the UI's **Quit application** button to stop the local server.

Useful runtime overrides are `--output-dir`, `--port`, `--no-browser`, `--adb-exe`, and `--ffmpeg-location`.

Local release builds mirror CI:

```bash
# Build for the current native platform (WSL defaults to Linux)
make build

# Linux or WSL: produce the Linux AppImage
make build-linux

# Explicit WSL alias
make build-wsl

# From WSL: stage and run the build using native Windows Python
make build-windows

# Build both artifacts sequentially
make build-all

# Run tests, frontend lint, and frontend build
make verify

# Smoke-test an existing Linux AppImage
make smoke-linux

# Smoke-test whichever desktop artifacts currently exist
make smoke

# Generate .sha256 files
make checksums

# Show generated artifacts
make artifacts
```

All build logic is implemented by one Python command. Make targets are convenience aliases:

```bash
uv run python scripts/build.py build --target linux
uv run python scripts/build.py build --target windows
uv run python scripts/build.py build --target all
uv run python scripts/build.py verify
uv run python scripts/build.py smoke --target all
uv run python scripts/build.py checksums --target all
```

On native Windows, run the same `scripts/build.py` command from a Windows terminal. From WSL, a Windows target is copied to a temporary Windows-side staging directory and executed with `py.exe -3.13`; the finished EXE is copied back to `dist/`. Use `--keep-staging` to retain that directory for diagnostics.

Build prerequisites are Python 3.13, uv, and Node.js/npm on the native target platform. The orchestrator installs project dependencies and downloads platform-tools/appimagetool, but it does not install Python, uv, or Node. PyInstaller still runs natively, so a normal Linux host cannot produce the Windows executable and Windows cannot produce the Linux AppImage.

Windows binaries are initially unsigned and may trigger SmartScreen. Android devices can still require manufacturer USB drivers on Windows or udev rules and USB permissions on Linux.

---

## Usage

1. Paste one or more YouTube URLs into the input box — single videos, playlists, channels, or a mix.
2. Click **Queue downloads**. The backend atomizes the input and enqueues individual track jobs.
3. Watch the queue counters and library grid update in real time as tracks finish downloading.
4. Click any card in the library to play it in the browser.
5. Use the **Sync to device** panel to push new tracks to a connected Android device over ADB.

## Useful scripts

Extract all individual links from a music.youtube.com private (not publically accessible) playlist:

1. Open the playlist in a popular browser (chrome, firefox, e.t.c)
2. Open console (F12)
3. Execute this script in console. It will copy all the links to your clipboard as a JSON array.

```javascript
copy(
    [...document.querySelectorAll('ytmusic-responsive-list-item-renderer')]
        .map(el => el.querySelector('yt-formatted-string a')?.href)
        .filter(Boolean)
        .map(u => u.split('&')[0])
)
```

4. Paste the JSON array with the links in this application and bulk download all the resources.
