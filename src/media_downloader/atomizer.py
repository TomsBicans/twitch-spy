from enum import Enum
from typing import Callable, List
import threading
import queue
import traceback
import time
import os.path as path
from urllib.parse import urlparse
import src.media_downloader.youtube as youtube
import src.media_downloader.twitch as twitch
import src.media_downloader.os_file_queue as FileQueue
import src.media_downloader.constants as const
from src.system_logger import logger


class Atom:
    def __init__(
        self, url: str, content_type: const.CONTENT_MODE, base_download_dir: str
    ) -> None:
        self.url = url
        self.platform = self._determine_platform(url)
        self.single_item = self._is_single_item(url)
        self.content_type = content_type
        self.download_dir = self._determine_download_dir(url, base_download_dir)

    @staticmethod
    def _determine_platform(url: str) -> const.PLATFORM:
        if "twitch.tv" in url:
            return const.PLATFORM.TWITCH
        elif "youtube.com" in url or "youtu.be" in url:
            return const.PLATFORM.YOUTUBE
        else:
            return const.PLATFORM.UNDEFINED

    @staticmethod
    def _is_single_item(url: str) -> bool:
        platform = Atom._determine_platform(url)
        if platform == const.PLATFORM.YOUTUBE:
            # Playlist or single video
            return "watch?v=" in url and "list=" not in url
        elif platform == const.PLATFORM.TWITCH:
            # I do not know if there is any thing as a multiple item in twitch
            return True
        elif platform == const.PLATFORM.UNDEFINED:
            return True

    def _determine_download_dir(self, url: str, base_download_dir: str) -> [str, None]:
        if Atom._is_single_item(url):
            # Random audio download directory.
            if self.content_type == const.CONTENT_MODE.AUDIO:
                return path.join(base_download_dir, "audio_library", "random_audio")
            elif self.content_type == const.CONTENT_MODE.VIDEO:
                return path.join(base_download_dir, "video_library", "random_videos")
        else:
            ...
        ...


class Atomizer:
    @staticmethod
    def atomize_urls(urls: List[str]):
        """"""
        ...

    @staticmethod
    def atomize(atom: Atom):
        ...


def is_url_valid(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except [ValueError, Exception]:
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
            if not is_url_valid(url):
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
