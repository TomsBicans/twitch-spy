from enum import Enum
from typing import Callable, List, Optional
import threading
import queue
import traceback
import time
import uuid
import os.path as path
from urllib.parse import urlparse
import src.media_downloader.youtube as youtube
import src.media_downloader.twitch as twitch
import src.media_downloader.os_file_queue as FileQueue
import src.media_downloader.constants as const
from src.system_logger import logger
from abc import ABC, abstractmethod


class Atom:
    def __init__(
        self,
        url: str,
        content_type: const.CONTENT_MODE,
        download_dir: str,
        content_name: Optional[str] = None,
    ) -> None:
        self.id = uuid.uuid4()
        self.url = url
        self.url_valid = self._is_url_valid(url)
        self.platform = self._determine_platform(url)
        self.single_item = self._is_single_item(url)
        self.content_type = content_type
        self.content_name = content_name
        self.download_dir = download_dir
        self.status = const.PROCESS_STATUS.QUEUED

    def update_status(self, status: const.PROCESS_STATUS):
        self.status = status

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
            # I do not know if there is any thing as a multiple item in twitch streaming service
            return True
        elif platform == const.PLATFORM.UNDEFINED:
            return True

    @staticmethod
    def _is_url_valid(url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except [ValueError, Exception]:
            return False

    def __str__(self) -> str:
        return (
            f"Atom(id={self.id} "
            f"url={self.url}, "
            f"valid_url={self.url_valid}, "
            f"platform={self.platform.name}, "
            f"single_item={self.single_item}, "
            f"content_type={self.content_type.name}, "
            f"download_dir={self.download_dir}, "
            f"status={self.status})"
        )


class PlatformHandler(ABC):
    @abstractmethod
    def atomize(self, atom: Atom) -> List[Atom]:
        pass


class YouTubeHandler(PlatformHandler):
    CONTENT_TYPE_TO_DIR = {
        const.CONTENT_MODE.AUDIO: "random_audio",
        const.CONTENT_MODE.VIDEO: "random_videos",
        const.CONTENT_MODE.STREAM: "random_videos",
    }

    def atomize(self, atom: Atom) -> List[Atom]:
        if atom.single_item:
            subdir = self.CONTENT_TYPE_TO_DIR.get(atom.content_type, "")
            new_download_dir = (
                path.join(atom.download_dir, subdir) if subdir else atom.download_dir
            )
            new_atom = Atom(
                atom.url,
                atom.content_type,
                new_download_dir,
                content_name=youtube.get_video_title(atom.url),
            )
            return [new_atom]
        video_metadatas = youtube.get_playlist_video_urls(atom.url)
        playlist_directory = youtube.get_playlist_download_directory(
            atom.download_dir, atom.url
        )
        return [
            Atom(
                vid.url,
                atom.content_type,
                playlist_directory,
                content_name=vid.title,
            )
            for vid in video_metadatas
        ]


class TwitchHandler(PlatformHandler):
    CONTENT_TYPE_TO_DIR = {
        const.CONTENT_MODE.AUDIO: "random_stream_audio",
        const.CONTENT_MODE.VIDEO: "random_stream_videos",
        const.CONTENT_MODE.STREAM: "random_stream_videos",
    }

    def atomize(self, atom: Atom) -> List[Atom]:
        subdir = self.CONTENT_TYPE_TO_DIR.get(atom.content_type, "")
        new_download_dir = (
            path.join(atom.download_dir, subdir) if subdir else atom.download_dir
        )
        return [Atom(atom.url, atom.content_type, new_download_dir)]


class Atomizer:
    # Map platforms to their handlers
    PLATFORM_HANDLERS = {
        const.PLATFORM.YOUTUBE: YouTubeHandler(),
        const.PLATFORM.TWITCH: TwitchHandler(),
        # add other platforms here...
    }

    @staticmethod
    def atomize_urls(
        urls: List[str], content_mode: const.CONTENT_MODE, root_download_dir: str
    ) -> List[Atom]:
        valid_urls = list(filter(Atom._is_url_valid, urls))
        atoms = []
        for url in valid_urls:
            atom = Atom(url, content_mode, root_download_dir)
            handler: PlatformHandler = Atomizer.PLATFORM_HANDLERS.get(atom.platform)
            if handler:
                atoms.extend(handler.atomize(atom))
            else:
                atoms.append(atom)  # Default behavior for unsupported platforms
        return atoms


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
            if not Atom._is_url_valid(url):
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
