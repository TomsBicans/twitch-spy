import threading
import os.path as path
import os
from typing import List


class QueueFile:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.file_lock = threading.Lock()
        if not path.isfile(filepath):
            open(filepath, "w").close()

    def read(self) -> List[str]:
        with self.file_lock:
            with open(self.filepath, "r") as file:
                lines = file.readlines()
        return lines

    def add(self, url: str):
        url = url.strip()
        with self.file_lock:
            with open(self.filepath, "r") as file:
                lines = file.readlines()
                lines = [line.strip() for line in lines]
            if url not in lines:
                with open(self.filepath, "a") as file:
                    file.write(url + "\n")

    def remove(self, url):
        with self.file_lock:
            with open(self.filepath, "r") as file:
                lines = file.readlines()
            with open(self.filepath, "w") as file:
                for line in lines:
                    if line.strip("\n") != url:
                        file.write(line)


class OSFileQueue:
    def __init__(self, library_location: str, file_type: str):
        self.work_dir = path.join(library_location, ".work_stats")
        os.makedirs(self.work_dir, exist_ok=True)

        self.input_file = QueueFile(path.join(self.work_dir, f"{file_type}_input.txt"))
        self.ongoing_file = QueueFile(
            path.join(self.work_dir, f"{file_type}_ongoing.txt")
        )
        self.finished_file = QueueFile(
            path.join(self.work_dir, f"{file_type}_finished.txt")
        )

    def format_input_file(self):
        def gather_unique_urls(lines: List[str]):
            unique_urls = []
            for line in lines:
                urls = line.strip().split()
                for url in urls:
                    if url not in unique_urls:
                        unique_urls.append(url)
            return unique_urls

        lines = self.input_file.read()
        unique_urls = gather_unique_urls(lines)
        with self.input_file.file_lock:
            with open(self.input_file.filepath, "w") as file:
                for url in unique_urls:
                    file.write(url + "\n")
