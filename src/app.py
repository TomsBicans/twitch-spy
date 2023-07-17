import logging
from flask import Flask
import src.video_downloader.os_file_queue as FileQueue
import src.video_downloader.core as vcore
import src.video_downloader.constants as vconst
import src.util as util
from typing import List
import config
import argparse
import time
import threading
import queue

# Routes
from src.routes.home_routes import home_routes


class SystemConfiguration:
    def __init__(self, urls: List[str], num_worker_threads: int, file_queue_mode: bool):
        self.urls: List[str] = urls
        self.num_worker_threads: int = num_worker_threads
        self.file_queue_mode: bool = file_queue_mode


def parse_args() -> SystemConfiguration:
    parser = argparse.ArgumentParser(
        description="Download and convert videos from different platforms"
    )
    parser.add_argument("urls", nargs="*", help="URLs of the videos to download")
    parser.add_argument(
        "--num-worker-threads",
        type=int,
        default=4,
        help="Number of worker threads (default: 4)",
    )
    parser.add_argument(
        "--file-queue-mode",
        type=bool,
        default=False,
        help="Should the program listen to the file queue.",
    )
    args = parser.parse_args()
    return SystemConfiguration(args.urls, args.num_worker_threads, args.file_queue_mode)


class Application:
    def __init__(self):
        self.audio_file_queue = FileQueue.OSFileQueue(config.STREAM_DOWNLOADS, "audio")
        self.video_file_queue = FileQueue.OSFileQueue(config.STREAM_DOWNLOADS, "video")
        self.app = Flask(__name__, template_folder="../templates")
        self.app.register_blueprint(home_routes)

    def main_cli(self):
        args = parse_args()
        audio_q = queue.Queue()
        video_q = queue.Queue()

        for url in set(args.urls):
            self.audio_file_queue.add_to_input(url)

        vcore.load_ongoing(audio_q, self.audio_file_queue)

        audio_threads = vcore.start_worker_threads(
            args.num_worker_threads,
            audio_q,
            self.audio_file_queue,
            vcore.process_queue,
            vconst.CONTENT_MODE.AUDIO,
        )

        video_threads = vcore.start_worker_threads(
            args.num_worker_threads,
            video_q,
            self.video_file_queue,
            vcore.process_queue,
            vconst.CONTENT_MODE.VIDEO,
        )

        user_input_thread = threading.Thread(
            target=vcore.handle_user_input, args=(audio_q,)
        )
        user_input_thread.setDaemon(True)
        user_input_thread.start()

        audio_file_input_thread = threading.Thread(
            target=vcore.handle_file_input, args=(audio_q, self.audio_file_queue)
        )
        audio_file_input_thread.setDaemon(True)
        audio_file_input_thread.start()

        video_file_input_thread = threading.Thread(
            target=vcore.handle_file_input, args=(video_q, self.video_file_queue)
        )
        video_file_input_thread.setDaemon(True)
        video_file_input_thread.start()

        try:
            user_input_thread.join()
            audio_file_input_thread.join()
            video_file_input_thread.join()
        except KeyboardInterrupt:
            pass

        for _ in range(args.num_worker_threads):
            video_q.put(vconst.SENTINEL)
            audio_q.put(vconst.SENTINEL)

        for t in audio_threads:
            t.join()
        for t in video_threads:
            t.join()

    def main_web(self):
        self.app.config[util.MagicStrings.APP] = self
        self.app.run(debug=True)


def main():
    my_app = Application()

    cli_thread = threading.Thread(target=my_app.main_cli)
    cli_thread.start()

    my_app.main_web()

    cli_thread.join()


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"Program finished in {end_time - start_time:.2f} seconds.")
