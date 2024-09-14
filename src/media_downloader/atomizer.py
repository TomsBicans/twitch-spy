from typing import List, Optional
import uuid
import os.path as path
from urllib.parse import urlparse
import src.media_downloader.constants as const


class Atom:
    def __init__(
        self,
        url: str,
        content_type: const.CONTENT_MODE,
        download_dir: str,
        content_title: Optional[str] = None,
        media_file_os_path: Optional[str] = None,
        thumbnail_os_path: Optional[str] = None,
    ) -> None:
        self.id = uuid.uuid4()
        self.url = url
        self.url_valid = self._is_url_valid(url)
        self.platform = self._determine_platform(url)
        self.single_item = self._is_single_item(url)
        self.content_type = content_type
        self.content_title = content_title
        self.download_dir = download_dir
        self.status = const.PROCESS_STATUS.QUEUED
        self.media_file_os_path = media_file_os_path or None
        self.thumbnail_os_path = thumbnail_os_path or None

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
            return "watch?v=" in url and "list=" not in url and "list=LL&" not in url
        elif platform == const.PLATFORM.TWITCH:
            # I do not know if there is any thing as a multiple item in twitch streaming service
            return True
        elif platform == const.PLATFORM.UNDEFINED:
            return True

    @staticmethod
    def _is_url_valid(url: str) -> bool:
        try:
            result = urlparse(url)
            return result.scheme in ["http", "https"] and bool(result.netloc)
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

    def to_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "url_valid": self.url_valid,
            "platform": self.platform.name,
            "single_item": self.single_item,
            "content_type": self.content_type.name,
            "download_dir": self.download_dir,
            "status": self.status.name,
        }
