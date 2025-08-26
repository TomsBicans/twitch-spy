from flask import Flask
from flask_cors import CORS
from src.media_downloader.job_manager import JobManager, JobStats
from src.media_downloader.storage_manager import LibraryManager
from src.media_downloader.atomizer import Atom
from src.socket_instance import socketio
import src.event_dispatcher as event_dispatcher
import config
import src.util as util
import src.cli as cli
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
        self.app = Flask(__name__, template_folder="../templates")
        CORS(self.app, resources={r"/*": {"origins": "http://localhost:5173"}})
        self.app.register_blueprint(home_routes)
        socketio.init_app(self.app)

        self.event_dispatcher = event_dispatcher.EventDispatcher()
        self.event_dispatcher.register_listener(
            event_dispatcher.Events.JOB_UPDATE.value,
            event_dispatcher.atom_status_listener,
        )
        self.event_dispatcher.register_listener(
            event_dispatcher.Events.JOB_CREATED.value,
            event_dispatcher.atom_status_listener,
        )
        self.event_dispatcher.register_listener(
            event_dispatcher.Events.JOB_RENDER.value,
            event_dispatcher.atom_status_listener,
        )
        self.event_dispatcher.register_listener(
            event_dispatcher.Events.STATISTICS_UPDATE.value,
            event_dispatcher.statistics_listener,
        )
        self.job_manager = JobManager(
            job_update_callback=self.job_update_callback, max_workers=3
        )
        # Initialize already processed jobs.
        self.audio_library = LibraryManager(config.AUDIO_LIBRARY)
        archive = self.audio_library.count_atoms()
        for atom in archive:
            self.job_manager.add_job_to_archive(atom)

    def job_update_callback(self, job: Atom, stats: JobStats):
        """Callback to handle job updates."""
        self.event_dispatcher.dispatch_event(
            event_dispatcher.Events.JOB_UPDATE.value, job
        )
        self.event_dispatcher.dispatch_event(
            event_dispatcher.Events.STATISTICS_UPDATE.value, stats
        )

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
