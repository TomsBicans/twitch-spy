from enum import Enum
from typing import Callable, List
import threading
import queue
import traceback
import time
from urllib.parse import urlparse
import src.media_downloader.youtube as youtube
import src.media_downloader.twitch as twitch
import src.media_downloader.os_file_queue as FileQueue
import src.media_downloader.constants as const
from src.system_logger import logger


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


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
        return const.PROCESS_STATUS.INVALID


def process_queue(
    q: queue.Queue, file_queue: FileQueue.OSFileQueue, mode: const.CONTENT_MODE
):
    while True:
        try:
            url = q.get(block=True)
            if url == const.SENTINEL or url is None:
                break
            if not is_valid_url(url):
                logger.warning(f"This is an invalid URL: {url}")
                q.task_done()
                continue
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


def handle_user_input(q: queue.Queue, shutdown_event: threading.Event):
    while True:
        try:
            url = input("Enter URL: ")
            q.put(url)
        except (EOFError, KeyboardInterrupt):
            print("Exiting program...")
            shutdown_event.set()
            break


def load_ongoing(q: queue.Queue, file_queue: FileQueue.OSFileQueue):
    urls = file_queue.ongoing_file.read()
    for url in urls:
        url = url.strip()
        q.put(url)
