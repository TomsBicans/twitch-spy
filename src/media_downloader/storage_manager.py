import os.path as path
import os
import sys
import threading
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

    def add_entry(self, location: str, url: str, title: str = None):
        with self.lock:
            with open(location, "a", encoding="utf-8", errors="replace") as f:
                f.write(f"{url},{title if title else 'None'}\n")
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

    def read_entries(self, location: str) -> List[Tuple[str, Optional[str]]]:
        entries = []
        if not path.exists(location):
            return entries
        data = self.read_file(location)
        for line in data.splitlines():
            if "," in line:
                url, title = line.split(",", 1)
                if (
                    title == "None"
                ):  # Convert the string 'None' to the Python None object
                    title = None
            else:
                url = line
                title = None
            entries.append((url.strip(), title))
        return entries

    def update_entry_title(self, location: str, url: str, new_title: str):
        with self.lock:
            # Read existing entries
            entries = self.read_entries(location)

            # Update the title for the matching URL
            updated_entries = []
            for entry_url, entry_title in entries:
                if entry_url == url:
                    updated_entries.append((entry_url, new_title))
                else:
                    updated_entries.append((entry_url, entry_title))

            # Write updated entries back to the file
            with open(location, "w", encoding="utf-8", errors="replace") as f:
                for entry_url, entry_title in updated_entries:
                    f.write(f"{entry_url},{entry_title if entry_title else 'None'}\n")

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
                updated_entries = {url: title for url, title in entries}

                if refresh_titles:
                    urls_to_refresh = [url for url, title in entries if not title]

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
                        updated_entries[url] = new_title

                    for url, title in tqdm(
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
                for url, title in updated_entries.items():
                    a = Atom(
                        url,
                        content_type=const.CONTENT_MODE.AUDIO,
                        download_dir=self.download_dir,
                        content_title=title if title else url.split("/")[-1],
                    )
                    a.update_status(status)
                    atoms.append(a)
        return atoms


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
