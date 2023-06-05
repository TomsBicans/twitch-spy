import threading
import os.path as path
import os
from typing import List


class OSFileQueue:
    def __init__(self, library_location: str):
        self.file_lock = threading.Lock()
        self.work_dir = path.join(library_location, ".work_stats")
        os.makedirs(self.work_dir, exist_ok=True)

        self.input_file = path.join(self.work_dir, "input.txt")
        self.ongoing_file = path.join(self.work_dir, "ongoing.txt")
        self.finished_file = path.join(self.work_dir, "finished.txt")
        # Create the files if they don't exist
        for file in [self.input_file, self.ongoing_file, self.finished_file]:
            if not path.isfile(file):
                open(file, "w").close()

    def format_input_file(self):
        with self.file_lock:
            with open(self.input_file, "r+") as input_file:
                lines = input_file.readlines()
                input_file.seek(0)
                input_file.truncate()

                for line in lines:
                    urls = line.strip().split()
                    unique_urls = set(urls)
                    for url in unique_urls:
                        input_file.write(url + "\n")

    def add_to_input(self, url: str):
        url = url.strip()
        with self.file_lock:
            with open(self.input_file, "r") as file:
                lines = file.readlines()
                lines = [line.strip() for line in lines]
            if url not in lines:
                with open(self.input_file, "a") as file:
                    file.write(url + "\n")

    def read_from_input(self):
        with self.file_lock:
            with open(self.input_file, "r") as file:
                lines = file.readlines()
        return lines

    def read_from_ongoing(self) -> List[str]:
        with self.file_lock:
            with open(self.ongoing_file, "r") as file:
                lines = file.readlines()
        return lines

    def add_to_ongoing(self, url: str):
        url = url.strip()
        with self.file_lock:
            with open(self.ongoing_file, "r") as file:
                lines = file.readlines()
                lines = [line.strip() for line in lines]
            if url not in lines:
                with open(self.ongoing_file, "a") as file:
                    file.write(url + "\n")

    def remove_from_ongoing(self, url):
        with self.file_lock:
            with open(self.ongoing_file, "r") as file:
                lines = file.readlines()
            with open(self.ongoing_file, "w") as file:
                for line in lines:
                    if line.strip("\n") != url:
                        file.write(line)

    def add_to_finished(self, url: str):
        url = url.strip()
        with self.file_lock:
            with open(self.finished_file, "r") as file:
                lines = file.readlines()
                lines = [line.strip() for line in lines]
            if url not in lines:
                with open(self.finished_file, "a") as file:
                    file.write(url + "\n")

    def remove_from_input(self, url):
        with self.file_lock:
            with open(self.input_file, "r") as file:
                lines = file.readlines()
            with open(self.input_file, "w") as file:
                for line in lines:
                    if line.strip("\n") != url:
                        file.write(line)