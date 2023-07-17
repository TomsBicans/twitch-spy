from enum import Enum
from typing import Callable, List
import threading
import queue
import traceback
import time
import src.video_downloader.youtube as youtube
import src.video_downloader.twitch as twitch
import src.video_downloader.os_file_queue as FileQueue
import src.video_downloader.constants as const


def preprocess_url(url: str) -> str:
    if "watch?v" in url and "&list=" in url:
        url = url.split("&list=")[0]
    return url


def process_url(url: str, mode: const.CONTENT_MODE) -> const.PROCESS_STATUS:
    if "twitch.tv" in url:
        return twitch.process_twitch_url(url, mode)
    elif "youtube.com" in url:
        return youtube.process_youtube_url(url, mode)
    else:
        print("Invalid platform specified.")
        return const.PROCESS_STATUS.FAILED


def start_worker_threads(
    num_worker_threads: int,
    q: queue.Queue,
    file_queue: FileQueue.OSFileQueue,
    process_function: Callable,
    content_mode: const.CONTENT_MODE,
) -> List[threading.Thread]:
    threads = []
    for _ in range(num_worker_threads):
        t = threading.Thread(
            target=process_function, args=(q, file_queue, content_mode)
        )
        t.setDaemon(True)
        t.start()
        threads.append(t)
    return threads


def process_queue(
    q: queue.Queue, file_queue: FileQueue.OSFileQueue, mode: const.CONTENT_MODE
):
    while True:
        try:
            url = q.get(block=True)
            if url == const.SENTINEL:
                break
            file_queue.input_file.remove(url)
            url = preprocess_url(url)
            file_queue.ongoing_file.add(url)
            status = process_url(url, mode)
            if status == const.PROCESS_STATUS.SUCCESS:
                file_queue.ongoing_file.remove(url)
                file_queue.finished_file.add(url)
            q.task_done()
        except Exception as e:
            traceback.print_exc()


def handle_user_input(q: queue.Queue):
    while True:
        try:
            url = input("Enter URL: ")
            q.put(url)
        except (EOFError, KeyboardInterrupt):
            print("Exiting program...")
            const.stop_workers.set()
            break


def load_ongoing(q: queue.Queue, file_queue: FileQueue.OSFileQueue):
    urls = file_queue.ongoing_file.read()
    for url in urls:
        url = url.strip()
        q.put(url)


def handle_file_input(q: queue.Queue, file_queue: FileQueue.OSFileQueue):
    queued_urls = set()  # keep track of urls that have been added to the queue
    while not const.stop_workers.is_set():
        file_queue.format_input_file()
        urls = file_queue.input_file.read()
        print(f"{len(urls)} urls found in input file.")
        for url in urls:
            url = url.strip()
            if url not in queued_urls:
                q.put(url)
                queued_urls.add(url)  # add the url to the set of queued urls
        time.sleep(2)  # sleep for 2 seconds
