import threading
import queue
from typing import Callable
import time


class ActivityThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_activity = time.time()

    def update_activity(self):
        self.last_activity = time.time()


class ThreadManager:
    def __init__(self, queue: queue.Queue, worker_function: Callable):
        self.worker_function = worker_function
        self.threads = []
        self.queue = queue

    def worker_wrapper(self):
        while True:
            item = self.queue.get()
            if item is None:  # Sentinel value to indicate thread should stop
                break
            self.worker_function(item)
            threading.current_thread().update_activity()

    def start_threads(self, num_threads: int):
        for _ in range(num_threads):
            t = ActivityThread(target=self.worker_wrapper)
            t.setDaemon(False)
            t.start()
            self.threads.append(t)

    def stop_threads(self, num_to_stop: int):
        # Sort threads by last activity (oldest activity first)
        self.threads.sort(key=lambda t: t.last_activity)

        for _ in range(min(num_to_stop, len(self.threads))):
            self.queue.put(None)  # Sentinel value to indicate thread should stop

        # Remove stopped threads from list
        for _ in range(min(num_to_stop, len(self.threads))):
            t = self.threads.pop(0)
            t.join()

    def adjust_threads(self, target_count: int):
        """
        Adjust the number of threads to the desired target count.
        If the target is more than current, start additional threads.
        If the target is less than current, stop the excess threads.
        """
        current_count = len(self.threads)
        if target_count > current_count:
            self.start_threads(target_count - current_count)
        elif target_count < current_count:
            self.stop_threads(current_count - target_count)


class ContentQueue:
    def __init__(self, content_type, worker_function: Callable, num_threads: int = 4):
        self.queue = queue.Queue()
        self.content_type = content_type
        self.num_threads = num_threads
        self.thread_manager = ThreadManager(self.queue, worker_function)

    def process(self, url: str):
        self.queue.put(url)

    def start_processing(self):
        self.thread_manager.start_threads(self.num_threads)

    def stop_processing(self):
        self.thread_manager.stop_threads(self.num_threads)
