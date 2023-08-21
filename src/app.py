import logging
from flask import Flask
import src.media_downloader.atomizer as vcore
import src.media_downloader.constants as vconst
from src.media_downloader.content_manager import ContentManager
from src.media_downloader.job_manager import JobManager
from src.media_downloader.atomizer import Atom
from src.socket_instance import socketio
import src.event_dispatcher as event_dispatcher
import src.util as util
import src.cli as cli
import config
import time
import threading
from src.system_logger import logger
from flask import request

# Routes
from src.routes.home_routes import home_routes


class Application:
    def __init__(self):
        args = cli.parse_args()
        self.shutdown_event = threading.Event()
        self.audio_manager = ContentManager(
            self.shutdown_event,
            vconst.CONTENT_MODE.AUDIO.value,
            vcore.process_queue,
            args.num_worker_threads,
            config.STREAM_DOWNLOADS,
        )
        self.video_manager = ContentManager(
            self.shutdown_event,
            vconst.CONTENT_MODE.VIDEO.value,
            vcore.process_queue,
            args.num_worker_threads,
            config.STREAM_DOWNLOADS,
        )
        self.app = Flask(__name__, template_folder="../templates")
        self.app.register_blueprint(home_routes)
        socketio.init_app(self.app)

        self.event_dispatcher = event_dispatcher.EventDispatcher()
        self.event_dispatcher.register_listener(event_dispatcher.atom_status_listener)
        self.job_manager = JobManager(
            job_update_callback=self.job_update_callback, max_workers=5
        )

    def job_update_callback(self, job: Atom):
        """Callback to handle job updates."""
        self.event_dispatcher.dispatch_event("job_update", job)

    def shutdown(self):
        self.shutdown_event.set()
        try:
            self.shutdown_server()
        except RuntimeError as e:
            logger.error(str(e))

    # Add this method to your Application class
    def shutdown_server(self):
        func = request.environ.get("werkzeug.server.shutdown")
        if func is None:
            raise RuntimeError("Not running with the Werkzeug Server")
        func()

    def main_cli(self):
        args = cli.parse_args()
        for url in set(args.urls):
            self.audio_manager.file_queue.input_file.add(url)
            socketio.emit("new_url_added", {"url": url})

        self.audio_manager.start_processing()
        self.video_manager.start_processing()

        while not self.shutdown_event.is_set():
            time.sleep(1)

        logger.info("Shutting down...")
        self.audio_manager.stop_processing()
        self.video_manager.stop_processing()

    def main_web(self):
        self.app.config[util.MagicStrings.APP] = self
        socketio.run(self.app, debug=True)


def main():
    my_app = Application()
    my_app.main_web()
    my_app.shutdown()


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logger.info(f"Program finished in {end_time - start_time:.2f} seconds.")
