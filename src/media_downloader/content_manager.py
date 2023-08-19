import src.media_downloader.os_file_queue as FileQueue
import src.media_downloader.constants as vconst
import src.media_downloader.core as vcore
import src.media_downloader.queue_manager as queue_manager
import threading
from typing import Callable
import queue
import time


class ContentManager:
    def __init__(
        self,
        shutdown_event: threading.Event,
        content_type: vconst.CONTENT_MODE,
        worker_function: Callable,
        num_worker_threads: int,
        download_directory: str,
    ):
        self.shutdown_event = shutdown_event
        self.content_type = content_type
        self.file_queue = FileQueue.OSFileQueue(download_directory, content_type)
        self.content_queue = queue_manager.ContentQueue(
            content_type, worker_function, num_worker_threads
        )
        self.file_input_thread = None

    def add_url(self, url):
        self.file_queue.input_file.add(url)

    def start_processing(self):
        vcore.load_ongoing(self.content_queue.queue, self.file_queue)
        self.content_queue.start_processing()

        self.file_input_thread = threading.Thread(
            target=self.handle_file_input,
            args=(self.content_queue.queue, self.file_queue),
        )
        self.file_input_thread.setDaemon(False)
        self.file_input_thread.start()

    def stop_processing(self):
        self.content_queue.stop_processing()
        self.file_input_thread.join()

    def handle_file_input(self, q: queue.Queue, file_queue: FileQueue.OSFileQueue):
        queued_urls = set()  # keep track of urls that have been added to the queue
        while not self.shutdown_event.is_set():
            file_queue.format_input_file()
            urls = file_queue.input_file.read()
            # print(f"{len(urls)} urls found in input file.")
            for url in urls:
                url = url.strip()
                if url not in queued_urls:
                    q.put(url)
                    queued_urls.add(url)  # add the url to the set of queued urls
            time.sleep(1)  # sleep for 1 seconds
