from typing import Callable, List, Optional
import os.path as path
from twitch_spy.media_downloader.atomizer import Atom
import twitch_spy.media_downloader.youtube as youtube
import twitch_spy.media_downloader.constants as const
from twitch_spy.media_downloader.storage_manager import StorageManager
from twitch_spy.system_logger import logger
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
    AUDIO_SUBDIR = "random_audio"

    def atomize(self, atom: Atom) -> List[Atom]:
        if atom.single_item:
            new_download_dir = path.join(atom.download_dir, self.AUDIO_SUBDIR)
            # Title is resolved later during download_audio() from info_dict,
            # avoiding a redundant network round-trip here.
            new_atom = Atom(
                atom.url,
                atom.content_type,
                new_download_dir,
                content_title=None,
            )
            return [new_atom]
        try:
            video_metadatas = youtube.get_playlist_video_urls(atom.url)
            playlist_directory = youtube.get_playlist_download_directory(
                atom.download_dir, atom.url
            )
        except Exception as exc:
            logger.warning("Skipping unsupported URL %s: %s", atom.url, exc)
            return []
        if not video_metadatas:
            logger.warning("No videos found for URL %s, skipping", atom.url)
            return []
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
            storage_manager.mark_successful_download(atom.url, title=atom.content_title)
        except:
            storage_manager.troublesome_download(atom.url, title=atom.content_title)
            atom.update_status(const.PROCESS_STATUS.FAILED)
        return atom

    def select_content_handler(self, atom: Atom) -> Callable:
        return youtube.YoutubeDownloader.download_audio


class Atomizer:
    PLATFORM_HANDLERS = {
        const.PLATFORM.YOUTUBE: YouTubeHandler(),
    }

    @staticmethod
    def atomize_urls(
        urls: List[str],
        content_mode: const.CONTENT_MODE,
        root_download_dir: str,
        on_url: Optional[Callable[[int, int], None]] = None,
    ) -> List[Atom]:
        valid_urls = list(filter(Atom._is_url_valid, urls))
        total = len(valid_urls)
        atoms = []
        for i, url in enumerate(valid_urls, start=1):
            atom = Atom(url, content_mode, root_download_dir)
            handler: PlatformHandler = Atomizer.PLATFORM_HANDLERS.get(atom.platform)
            if handler:
                atoms.extend(handler.atomize(atom))
            else:
                logger.warning("Skipping unsupported URL: %s", url)
            if on_url:
                on_url(i, total)
        return atoms

    @staticmethod
    def get_platform_handler(job: Atom) -> PlatformHandler:
        handler = Atomizer.PLATFORM_HANDLERS.get(job.platform)
        if handler:
            return handler
        else:
            return None
