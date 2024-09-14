import os.path as path
import os
import sys
import threading
import re
from src.media_downloader.atomizer import Atom
import src.media_downloader.constants as const
import src.media_downloader.youtube as youtube
from enum import Enum
from typing import List, Tuple, Optional
from src.system_logger import logger
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor


class StorageFiles(Enum):
    STORAGE_FOLDER = "storage"
    THUMBNAILS_FOLDER = "thumbnails"
    LOCAL_STORAGE = "local_storage.txt"
    FAILED_DOWNLOADS = "failed_downloads.txt"
    FAILED_SPLIT = "failed_split.txt"


class StorageManager:
    def __init__(self, download_dir: str) -> None:
        self.lock = threading.Lock()
        self.download_dir = download_dir
        self.storage_folder = self.ensure_folder_exists(
            path.join(self.download_dir, StorageFiles.STORAGE_FOLDER.value)
        )
        self.thumbnails_folder = self.ensure_folder_exists(
            path.join(self.download_dir, StorageFiles.THUMBNAILS_FOLDER.value)
        )
        self.storage_file = self.ensure_file_exists(
            path.join(self.storage_folder, StorageFiles.LOCAL_STORAGE.value)
        )
        self.failed_downloads = self.ensure_file_exists(
            path.join(self.storage_folder, StorageFiles.FAILED_DOWNLOADS.value)
        )
        self.failed_split = self.ensure_file_exists(
            path.join(self.storage_folder, StorageFiles.FAILED_SPLIT.value)
        )

    @staticmethod
    def ensure_folder_exists(folder_path: str) -> str:
        if not path.exists(folder_path):
            os.makedirs(folder_path)
        return folder_path

    @staticmethod
    def ensure_file_exists(file_path: str) -> str:
        if not path.exists(file_path):
            StorageManager.create_file(file_path)
        return file_path

    @staticmethod
    def read_file(location: str):
        with open(location, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    @staticmethod
    def create_file(location: str):
        with open(location, "w", encoding="utf-8") as f:
            pass
        return location

    def add_entry(self, location: str, url: str, title: str = None, media_path: str = None, thumbnail_path: str = None):
        with self.lock:
            with open(location, "a", encoding="utf-8", errors="replace") as f:
                f.write(f"{url},{title if title else 'None'},{media_path if media_path else 'None'},{thumbnail_path if thumbnail_path else 'None'}\n")
            return location

    def already_downloaded(self, url: str) -> bool:
        with self.lock:
            if not path.exists(self.storage_file):
                return False
            data = self.read_file(self.storage_file)
            data = [
                line.split(",")[0] if "," in line else line
                for line in data.splitlines()
            ]
            return url in data

    def mark_successful_download(self, url: str, title: str = None):
        self.add_entry(self.storage_file, url, title)

    def troublesome_download(self, url: str, title: str = None):
        data = self.read_file(self.failed_downloads)
        data = [
            line.split(",")[0] if "," in line else line for line in data.splitlines()
        ]
        if url not in data:
            self.add_entry(self.failed_downloads, url, title)

    def troublesome_split(self, url: str, title: str = None):
        data = self.read_file(self.failed_split)
        data = [
            line.split(",")[0] if "," in line else line for line in data.splitlines()
        ]
        if url not in data:
            self.add_entry(self.failed_split, url, title)

    def read_entries(self, location: str) -> List[Tuple[str, Optional[str], Optional[str], Optional[str]]]:
        entries = []
        if not path.exists(location):
            return entries
        data = self.read_file(location)
        for line in data.splitlines():
            parts = line.split(",")
            url = parts[0].strip()
            title = parts[1].strip() if len(parts) > 1 and parts[1] != "None" else None
            media_path = parts[2].strip() if len(parts) > 2 and parts[2] != "None" else None
            thumbnail_path = parts[3].strip() if len(parts) > 3 and parts[3] != "None" else None
            entries.append((url, title, media_path, thumbnail_path))
        return entries

    def update_entry_title(self, location: str, url: str, new_title: str):
        with self.lock:
            # Read existing entries
            entries = self.read_entries(location)

            # Update the title for the matching URL
            updated_entries = []
            for entry_url, entry_title, media_path, thumbnail_path in entries:
                if entry_url == url:
                    updated_entries.append((entry_url, new_title, media_path, thumbnail_path))
                else:
                    updated_entries.append((entry_url, entry_title, media_path, thumbnail_path))

            # Write updated entries back to the file
            with open(location, "w", encoding="utf-8", errors="replace") as f:
                for entry_url, entry_title, media_path, thumbnail_path in updated_entries:
                    f.write(f"{entry_url},{entry_title if entry_title else 'None'},{media_path if media_path else 'None'},{thumbnail_path if thumbnail_path else 'None'}\n")

    def generate_atoms(self, refresh_titles: bool = False) -> List[Atom]:
        atoms = []
        file_statuses = {
            StorageFiles.FAILED_DOWNLOADS.value: const.PROCESS_STATUS.FAILED,
            StorageFiles.LOCAL_STORAGE.value: const.PROCESS_STATUS.FINISHED,
        }

        progress_lock = threading.Lock()

        def fetch_title(url, pbar: tqdm, progress_lock: threading.Lock):
            title = youtube.get_video_title(url)
            with progress_lock:
                pbar.update(1)
            return title

        for file_name, status in tqdm(file_statuses.items(), desc="Processing files"):
            file_path = path.join(self.storage_folder, file_name)
            if path.exists(file_path):
                entries = self.read_entries(file_path)
                updated_entries = {url: (title, media_path, thumbnail_path) for url, title, media_path, thumbnail_path in entries}

                if refresh_titles:
                    urls_to_refresh = [url for url, (title, _, _) in entries if not title]

                    with ThreadPoolExecutor(max_workers=15) as executor:
                        with tqdm(
                            total=len(urls_to_refresh),
                            position=0,
                        ) as pbar:
                            new_titles = list(
                                executor.map(
                                    lambda url: fetch_title(url, pbar, progress_lock),
                                    urls_to_refresh,
                                )
                            )

                    for url, new_title in zip(urls_to_refresh, new_titles):
                        title, media_path, thumbnail_path = updated_entries[url]
                        updated_entries[url] = (new_title, media_path, thumbnail_path)

                    for url, (title, media_path, thumbnail_path) in tqdm(
                        updated_entries.items(),
                        desc=f"Processing entries for {file_path}",
                    ):
                        self.update_entry_title(
                            path.join(
                                self.download_dir,
                                StorageFiles.STORAGE_FOLDER.value,
                                file_name,
                            ),
                            url,
                            title,
                        )
                for url, (title, media_path, thumbnail_path) in updated_entries.items():
                    media_path = self._find_file_path(self.download_dir, title)
                    thumbnail_path = self._find_file_path(self.thumbnails_folder, title)
                    a = Atom(
                        url,
                        content_type=const.CONTENT_MODE.AUDIO,
                        download_dir=self.download_dir,
                        content_title=title if title else url.split("/")[-1],
                        media_file_os_path=media_path,
                        thumbnail_os_path=thumbnail_path,
                    )
                    a.update_status(status)
                    atoms.append(a)
        return atoms

    def _normalize_string(self, s: str) -> str:
        # Replace spaces with hyphens
        s = s.replace(' ', '-')
        # Replace all other non-alphanumeric characters with hyphens
        s = re.sub(r'[^a-zA-Z0-9-]', '-', s)
        # Replace multiple consecutive hyphens with a single hyphen
        s = re.sub(r'-+', '-', s)
        # Remove leading and trailing hyphens
        s = s.strip('-')
        return s.lower()

    def _find_file_path(self, dir: str, title: str) -> Optional[str]:
        normalized_title = self._normalize_string(title).lower()
        for file in os.listdir(dir):
            normalized_file_name = self._normalize_string(path.splitext(file)[0])
            if normalized_file_name == normalized_title:
                return path.join(dir, file)
        return None


class LibraryManager:
    def __init__(self, library_dir: str) -> None:
        self.library_dir = library_dir

    def count_atoms(self) -> List[Atom]:
        atoms = []

        # Recursively traverse the directory tree
        for dirpath, dirnames, filenames in os.walk(self.library_dir):
            if "storage" in dirnames:
                # Create a StorageManager instance for this specific download_dir
                storage_manager = StorageManager(dirpath)

                # Generate Atom objects for this specific download_dir
                atoms += storage_manager.generate_atoms(refresh_titles=False)

        # Return the list of Atom objects
        return atoms
