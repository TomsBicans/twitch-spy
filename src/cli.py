import argparse
from typing import List


class SystemConfiguration:
    def __init__(self, urls: List[str], num_worker_threads: int, file_queue_mode: bool):
        self.urls: List[str] = urls
        self.num_worker_threads: int = num_worker_threads
        self.file_queue_mode: bool = file_queue_mode


def parse_args() -> SystemConfiguration:
    parser = argparse.ArgumentParser(
        description="Download and convert videos from different platforms"
    )
    parser.add_argument("urls", nargs="*", help="URLs of the videos to download")
    parser.add_argument(
        "--num-worker-threads",
        type=int,
        default=4,
        help="Number of worker threads (default: 4)",
    )
    parser.add_argument(
        "--file-queue-mode",
        type=bool,
        default=False,
        help="Should the program listen to the file queue.",
    )
    args = parser.parse_args()
    return SystemConfiguration(args.urls, args.num_worker_threads, args.file_queue_mode)
