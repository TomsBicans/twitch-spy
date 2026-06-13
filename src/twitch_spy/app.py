from __future__ import annotations

import importlib.metadata
import secrets
import subprocess
import threading
import time
from pathlib import Path
from collections.abc import Callable

from flask import Flask, abort, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.serving import BaseWSGIServer, make_server

import twitch_spy.config as config
import twitch_spy.event_dispatcher as event_dispatcher
import twitch_spy.util as util
from twitch_spy.desktop import open_directory, resource_path
from twitch_spy.media_downloader.atomizer import Atom
from twitch_spy.media_downloader.job_manager import JobManager, JobStats
from twitch_spy.media_downloader.storage_manager import LibraryManager
from twitch_spy.routes.home_routes import home_routes
from twitch_spy.routes.sync_routes import sync_routes
from twitch_spy.socket_instance import socketio
from twitch_spy.system_logger import logger


def app_version() -> str:
    try:
        return importlib.metadata.version("twitch-spy")
    except importlib.metadata.PackageNotFoundError:
        return "0.1.0"


class Application:
    def __init__(
        self,
        frontend_dir: Path | None = None,
        disconnect_grace: float = 30.0,
        development: bool = False,
    ):
        self.frontend_dir = frontend_dir or resource_path("client", "dist")
        self.disconnect_grace = disconnect_grace
        self.development = development
        self.shutdown_token = secrets.token_urlsafe(32)
        self.shutdown_event = threading.Event()
        self.sync_thread: threading.Thread | None = None
        self.sync_lock = threading.Lock()
        self.connected_clients = 0
        self.had_browser_client = False
        self.disconnect_timer: threading.Timer | None = None
        self.server: BaseWSGIServer | None = None

        self.app = Flask(__name__, static_folder=None)
        development_frontend = development or not self.frontend_dir.exists()
        if development_frontend:
            CORS(
                self.app,
                resources={
                    r"/*": {
                        "origins": [
                            "http://localhost:5173",
                            "http://127.0.0.1:5173",
                        ]
                    }
                },
            )
        self.app.register_blueprint(home_routes)
        self.app.register_blueprint(sync_routes)
        self.app.config[util.MagicStrings.APP] = self
        socketio.init_app(
            self.app,
            cors_allowed_origins=(
                ["http://localhost:5173", "http://127.0.0.1:5173"]
                if development_frontend
                else None
            ),
        )
        self._register_desktop_routes()
        self._register_socket_lifecycle()

        self.event_dispatcher = event_dispatcher.EventDispatcher()
        for event, listener in (
            (event_dispatcher.Events.JOB_UPDATE.value, event_dispatcher.atom_status_listener),
            (event_dispatcher.Events.JOB_CREATED.value, event_dispatcher.atom_status_listener),
            (event_dispatcher.Events.JOB_RENDER.value, event_dispatcher.atom_status_listener),
            (event_dispatcher.Events.STATISTICS_UPDATE.value, event_dispatcher.statistics_listener),
        ):
            self.event_dispatcher.register_listener(event, listener)
        self.job_manager = JobManager(job_update_callback=self.job_update_callback, max_workers=3)
        self.audio_library = LibraryManager(config.AUDIO_LIBRARY)
        for atom in self.audio_library.count_atoms():
            self.job_manager.add_job_to_archive(atom)

    def _register_desktop_routes(self) -> None:
        @self.app.get("/health")
        def health():
            return jsonify({"status": "ok", "version": app_version()})

        @self.app.post("/shutdown")
        def shutdown():
            if request.headers.get("X-Twitch-Spy-Shutdown") != self.shutdown_token:
                abort(403)
            threading.Timer(0.1, self.request_shutdown).start()
            return jsonify({"status": "shutting-down"})

        @self.app.post("/open-music-directory")
        def open_music_directory():
            if (
                not self.development
                and request.headers.get("X-Twitch-Spy-Shutdown") != self.shutdown_token
            ):
                abort(403)
            try:
                open_directory(config.AUDIO_LIBRARY)
            except (OSError, subprocess.SubprocessError) as exc:
                logger.warning("Could not open music directory: %s", exc)
                return jsonify({"error": f"Could not open music directory: {exc}"}), 503
            return jsonify({"status": "opened"})

        @self.app.get("/")
        @self.app.get("/<path:frontend_path>")
        def frontend(frontend_path: str = ""):
            requested = self.frontend_dir / frontend_path
            if frontend_path and requested.is_file():
                return send_from_directory(self.frontend_dir, frontend_path)
            index = self.frontend_dir / "index.html"
            if not index.is_file():
                return jsonify({"error": "Frontend is not built. Run the Vite development server or npm run build."}), 503
            html = index.read_text(encoding="utf-8").replace("__TWITCH_SPY_SHUTDOWN_TOKEN__", self.shutdown_token)
            return html

    def _register_socket_lifecycle(self) -> None:
        @socketio.on("connect")
        def connected():
            self.connected_clients += 1
            self.had_browser_client = True
            if self.disconnect_timer:
                self.disconnect_timer.cancel()

        @socketio.on("disconnect")
        def disconnected():
            self.connected_clients = max(0, self.connected_clients - 1)
            if not self.development and self.had_browser_client and self.connected_clients == 0:
                self.disconnect_timer = threading.Timer(self.disconnect_grace, self._shutdown_if_idle)
                self.disconnect_timer.daemon = True
                self.disconnect_timer.start()

    def _shutdown_if_idle(self) -> None:
        if self.development:
            return
        if self.connected_clients == 0 and not self.has_active_sync() and not self.job_manager.has_active_jobs():
            self.request_shutdown()
        elif self.connected_clients == 0:
            self.disconnect_timer = threading.Timer(5.0, self._shutdown_if_idle)
            self.disconnect_timer.daemon = True
            self.disconnect_timer.start()

    def start_sync(self, target: Callable[[], None]) -> bool:
        def run() -> None:
            try:
                target()
            except Exception:
                logger.exception("Android synchronization failed")
            finally:
                with self.sync_lock:
                    if self.sync_thread is threading.current_thread():
                        self.sync_thread = None

        with self.sync_lock:
            if self.sync_thread is not None and self.sync_thread.is_alive():
                return False
            thread = threading.Thread(target=run, daemon=True, name="android-sync")
            self.sync_thread = thread
            try:
                thread.start()
            except Exception:
                self.sync_thread = None
                raise
        return True

    def has_active_sync(self) -> bool:
        with self.sync_lock:
            return self.sync_thread is not None and self.sync_thread.is_alive()

    def job_update_callback(self, job: Atom, stats: JobStats):
        self.event_dispatcher.dispatch_event(event_dispatcher.Events.JOB_UPDATE.value, job)
        self.event_dispatcher.dispatch_event(event_dispatcher.Events.STATISTICS_UPDATE.value, stats)

    def request_shutdown(self) -> None:
        self.shutdown_event.set()
        if self.server is not None:
            self.server.shutdown()

    def main_web(self, port: int = 5000):
        self.server = make_server("127.0.0.1", port, self.app, threaded=True)
        try:
            self.server.serve_forever()
        finally:
            if self.disconnect_timer:
                self.disconnect_timer.cancel()
            self.job_manager.shutdown()


def main(port: int = 5000, development: bool = False):
    application = Application(development=development)
    application.main_web(port=port)


if __name__ == "__main__":
    started = time.time()
    main()
    logger.info("Program finished in %.2f seconds.", time.time() - started)
