import os.path as path
import os
import sys
import threading
from src.media_downloader.atomizer import Atom
import src.media_downloader.constants as const
from typing import List


class StorageManager:
    def __init__(self, download_dir: str) -> None:
        self.lock = threading.Lock()
        self.download_dir = download_dir
        self.storage_folder = path.join(self.download_dir, "storage")
        if not path.exists(self.storage_folder):
            os.makedirs(self.storage_folder)
        self.storage_file = path.join(self.storage_folder, "local_storage.txt")
        if not path.exists(self.storage_file):
            self.create_file(self.storage_file)
        self.failed_downloads = path.join(self.storage_folder, "failed_downloads.txt")
        if not path.exists(self.failed_downloads):
            self.create_file(self.failed_downloads)
        self.failed_split = path.join(self.storage_folder, "failed_split.txt")
        if not path.exists(self.failed_split):
            self.create_file(self.failed_split)

    @staticmethod
    def read_file(location: str):
        with open(location, "r") as f:
            return f.read()

    @staticmethod
    def create_file(location: str):
        with open(location, "w") as f:
            pass
        return location

    def add_entry(self, location: str, url: str, title: str = None):
        with self.lock:
            with open(location, "a") as f:
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


class LibraryManager:
    def __init__(self, library_dir: str) -> None:
        self.library_dir = library_dir

    def count_atoms(self) -> List[Atom]:
        atoms = []

        # Recursively traverse the directory tree
        for dirpath, dirnames, filenames in os.walk(self.library_dir):
            if "storage" in dirnames:
                storage_path = os.path.join(dirpath, "storage")

                # Read the text files and assign statuses based on the file
                file_statuses = {
                    "failed_downloads.txt": const.PROCESS_STATUS.FAILED,
                    "local_storage.txt": const.PROCESS_STATUS.FINISHED,
                }

                for file_name, status in file_statuses.items():
                    file_path = os.path.join(storage_path, file_name)

                    if os.path.exists(file_path):
                        with open(file_path, "r") as f:
                            urls = f.readlines()

                            # Extract URLs and create Atom objects with respective statuses
                            for url in urls:
                                url = (
                                    url.strip()
                                )  # Remove any trailing whitespaces or newlines
                                # Extracting title from the URL (here, we'll use the last part of the URL as a title)
                                title = url.split("/")[-1] if "/" in url else url
                                a = Atom(
                                    url,
                                    content_type=const.CONTENT_MODE.AUDIO,
                                    download_dir=dirpath,
                                    content_title=title,
                                )
                                a.update_status(status)
                                atoms.append(a)

        # Return the list of Atom objects
        return atoms
