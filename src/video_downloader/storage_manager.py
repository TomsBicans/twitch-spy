import os.path as path
import os
import sys
import threading


def read_file(location: str):
    with open(location, "r") as f:
        return f.read()


def create_file(location: str):
    with open(location, "w") as f:
        pass
    return location


def append_to_file(location: str, data: str):
    with open(location, "a") as f:
        f.write(data + "\n")
    return location


class StorageManager:
    def __init__(self, download_dir: str) -> None:
        self.lock = threading.Lock()
        self.download_dir = download_dir
        self.storage_folder = path.join(self.download_dir, "storage")
        if not path.exists(self.storage_folder):
            os.makedirs(self.storage_folder)
        self.storage_file = path.join(self.storage_folder, "local_storage.txt")
        if not path.exists(self.storage_file):
            create_file(self.storage_file)
        self.failed_downloads = path.join(self.storage_folder, "failed_downloads.txt")
        if not path.exists(self.failed_downloads):
            create_file(self.failed_downloads)
        self.failed_split = path.join(self.storage_folder, "failed_split.txt")
        if not path.exists(self.failed_split):
            create_file(self.failed_split)

    def already_downloaded(self, url: str) -> bool:
        if not path.exists(self.storage_file):
            return False
        data = read_file(self.storage_file)
        data = data.splitlines()
        if not url in data:
            return False
        return True

    def mark_successful_download(self, url: str):
        append_to_file(self.storage_file, url)

    def troublesome_download(self, url: str):
        if not url in read_file(self.failed_downloads):
            append_to_file(self.failed_downloads, url)

    def troublesome_split(self, url: str):
        if not url in read_file(self.failed_split):
            append_to_file(self.failed_split, url)
