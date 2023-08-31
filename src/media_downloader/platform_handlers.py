from typing import Callable, List, Optional
import os.path as path
from src.media_downloader.atomizer import Atom
import src.media_downloader.youtube as youtube
import src.media_downloader.twitch as twitch
import src.media_downloader.constants as const
from src.media_downloader.storage_manager import StorageManager
from src.system_logger import logger
from src.media_downloader.constants import lock
from abc import ABC, abstractmethod


class PlatformHandler(ABC):
    @abstractmethod
    def atomize(self, atom: Atom) -> List[Atom]:
        pass

    @abstractmethod
    def process(self, atom: Atom) -> Atom:
        return atom

    @abstractmethod
    def select_content_handler(self, atom: Atom) -> Callable:
        pass


class YouTubeHandler(PlatformHandler):
    CONTENT_TYPE_TO_DIR = {
        const.CONTENT_MODE.AUDIO: "random_audio",
        const.CONTENT_MODE.VIDEO: "random_videos",
        const.CONTENT_MODE.STREAM: "random_videos",
    }

    CONTENT_TYPE_HANDLER = {
        const.CONTENT_MODE.AUDIO: youtube.YoutubeDownloader.download_audio,
        const.CONTENT_MODE.VIDEO: youtube.download_video,
        const.CONTENT_MODE.STREAM: None,
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
                content_title=youtube.get_video_title(atom.url),
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
                content_title=vid.title,
            )
            for vid in video_metadatas
        ]

    def process(self, atom: Atom) -> Atom:
        storage_manager = StorageManager(atom.download_dir)
        if storage_manager.already_downloaded(atom.url):
            atom.update_status(const.PROCESS_STATUS.FINISHED)
            return atom
        content_handler = self.select_content_handler(atom)
        logger.debug(f"content handler: {content_handler} selected for job: {atom}")
        try:
            content_handler(atom)
            with lock:
                storage_manager.mark_successful_download(atom.url)
        except:
            with lock:
                storage_manager.troublesome_download(atom.url)
            atom.update_status(const.PROCESS_STATUS.FAILED)
        return atom

    def select_content_handler(self, atom: Atom) -> Callable:
        res = self.CONTENT_TYPE_HANDLER.get(atom.content_type)
        if res:
            return res
        else:
            return None


class TwitchHandler(PlatformHandler):
    CONTENT_TYPE_TO_DIR = {
        const.CONTENT_MODE.AUDIO: "random_stream_audio",
        const.CONTENT_MODE.VIDEO: "random_stream_videos",
        const.CONTENT_MODE.STREAM: "random_stream_videos",
    }

    CONTENT_TYPE_HANDLER = {
        # Implement in the future
        const.CONTENT_MODE.AUDIO: None,
        const.CONTENT_MODE.VIDEO: None,
        const.CONTENT_MODE.STREAM: None,
    }

    def atomize(self, atom: Atom) -> List[Atom]:
        subdir = self.CONTENT_TYPE_TO_DIR.get(atom.content_type, "")
        new_download_dir = (
            path.join(atom.download_dir, subdir) if subdir else atom.download_dir
        )
        return [Atom(atom.url, atom.content_type, new_download_dir)]

    def process(self, atom: Atom) -> Atom:
        return atom

    def select_content_handler(self, atom: Atom) -> Callable:
        res = self.CONTENT_TYPE_HANDLER.get(atom.content_type)
        if res:
            return res
        else:
            return None


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

    @staticmethod
    def get_platform_handler(job: Atom) -> PlatformHandler:
        handler = Atomizer.PLATFORM_HANDLERS.get(job.platform)
        if handler:
            return handler
        else:
            return None
