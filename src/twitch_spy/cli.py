import argparse
from typing import List


class SystemConfiguration:
    def __init__(self, urls: List[str], num_worker_threads: int, file_queue_mode: bool, output_dir: str, android_dest: str):
        self.urls: List[str] = urls
        self.num_worker_threads: int = num_worker_threads
        self.file_queue_mode: bool = file_queue_mode
        self.output_dir: str = output_dir
        self.android_dest: str = android_dest


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
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./data",
        help="Directory for logs and stream downloads (default: ./data)",
    )
    parser.add_argument(
        "--android-dest",
        type=str,
        default="/sdcard/SdCardBackup/Music",
        help="Android destination root path for sync (default: /sdcard/SdCardBackup/Music)",
    )
    args = parser.parse_args()
    return SystemConfiguration(args.urls, args.num_worker_threads, args.file_queue_mode, args.output_dir, args.android_dest)
