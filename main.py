import src.video_downloader.twitch as twitch
import src.video_downloader.youtube as youtube
import src.video_downloader.os_file_queue as FileQueue
from src.video_downloader.storage_manager import StorageManager
from src.twitch_api import api_client
from concurrent.futures import ThreadPoolExecutor
from typing import Set, List
import config
import sys
import os
import argparse
import time
import traceback
import os.path as path
import utils
import threading
import queue

SENTINEL = "STOP_WORKER"
stop_workers = threading.Event()


def process_url(url: str):
    if "twitch.tv" in url:
        print("Twitch url detected.")
        downloader = twitch.TwitchDownloader()
        ttv_streams = path.join(config.STREAM_DOWNLOADS, "twitch_streams")
        config.create_directory_if_not_exists(ttv_streams)
        print(f"Starting twitch stream download: {url}")
        downloader.download_stream_audio(url, ttv_streams)
    elif "youtube.com" in url:
        downloader = youtube.YoutubeDownloader()
        if youtube.is_youtube_playlist(url):
            print(f"Playlist detected: {url}")
            videos = youtube.get_playlist_video_urls(url)
            print(f"Got {len(videos)} videos.")
            download_dir = youtube.get_playlist_download_directory(
                config.STREAM_DOWNLOADS, url
            )
            download_dir = config.create_directory_if_not_exists(download_dir)
            storage_manager = StorageManager(download_dir)
            for i, vid in enumerate(videos):
                print(f"Processing: {i+1}/{len(videos)} ...")
                if stop_workers.is_set():
                    print("Stop workers flag is set. Exiting...")
                    return
                if storage_manager.already_downloaded(vid):
                    print(f"Video already exists. Will skip download: {vid}")
                    continue
                download_audio(downloader, download_dir, storage_manager, vid)
        elif youtube.is_youtube_video(url):
            download_dir = path.join(config.STREAM_DOWNLOADS, "random_videos")
            download_dir = config.create_directory_if_not_exists(download_dir)
            storage_manager = StorageManager(download_dir)
            print(f"Video detected: {url}")
            download_audio(downloader, download_dir, storage_manager, url)
    else:
        print("Invalid platform specified.")
        exit()


def download_audio(
    downloader: youtube.YoutubeDownloader,
    download_dir: str,
    storage_manager: StorageManager,
    url: str,
):
    try:
        print(f"Downloading {url} ...")
        audio_file = downloader.download_audio(url, download_dir)
        print(audio_file)
        with storage_manager.lock:
            storage_manager.mark_successful_download(url)
    except Exception as e:
        with storage_manager.lock:
            storage_manager.troublesome_download(url)
        traceback.print_exc()
        return

    try:
        print(f"Splitting {audio_file} ...")
        split_length_criteria = 60 * 20  # 20 minutes
        if youtube.Utils.audio_length(audio_file) > (split_length_criteria):
            print(
                f"Video is longer than {split_length_criteria} seconds. Splitting video."
            )
            youtube.Utils.split_file_by_tracks(url, audio_file)
        else:
            print(
                f"Video is not longer than {split_length_criteria} seconds. Doing nothing."
            )
            return
    except Exception as e:
        with storage_manager.lock:
            storage_manager.troublesome_split(url)
        traceback.print_exc()


class DownloaderConfig:
    def __init__(self, urls: List[str], num_worker_threads: int, file_queue_mode: bool):
        self.urls: List[str] = urls
        self.num_worker_threads: int = num_worker_threads
        self.file_queue_mode: bool = file_queue_mode


def parse_args() -> DownloaderConfig:
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
    return DownloaderConfig(args.urls, args.num_worker_threads, args.file_queue_mode)


def start_worker_threads(
    num_worker_threads: int, q: queue.Queue, file_queue: FileQueue.OSFileQueue
) -> List[threading.Thread]:
    threads = []
    for _ in range(num_worker_threads):
        t = threading.Thread(target=process_queue, args=(q, file_queue))
        t.setDaemon(True)
        t.start()
        threads.append(t)
    return threads


def process_queue(q: queue.Queue, file_queue: FileQueue.OSFileQueue):
    while True:
        try:
            url = q.get(block=True)
            if url == SENTINEL:
                break
            file_queue.remove_from_input(url)
            file_queue.add_to_ongoing(url)
            process_url(url)
            file_queue.remove_from_ongoing(url)
            file_queue.add_to_finished(url)
            q.task_done()
        except Exception as e:
            traceback.print_exc()


def handle_user_input(q: queue.Queue):
    while True:
        try:
            url = input("Enter URL: ")
            q.put(url)
        except (EOFError, KeyboardInterrupt):
            print("Exiting program...")
            stop_workers.set()
            break


def load_ongoing(q: queue.Queue, file_queue: FileQueue.OSFileQueue):
    urls = file_queue.read_from_ongoing()
    for url in urls:
        url = url.strip()
        q.put(url)


def handle_file_input(q: queue.Queue, file_queue: FileQueue.OSFileQueue):
    queued_urls = set()  # keep track of urls that have been added to the queue
    while not stop_workers.is_set():
        urls = file_queue.read_from_input()
        print(f"{len(urls)} urls found in input file.")
        for url in urls:
            url = url.strip()
            if url not in queued_urls:
                q.put(url)
                queued_urls.add(url)  # add the url to the set of queued urls
        time.sleep(2)  # sleep for 2 seconds


def main():
    args = parse_args()
    file_queue = FileQueue.OSFileQueue(config.STREAM_DOWNLOADS)
    q = queue.Queue()

    for url in set(args.urls):
        file_queue.add_to_input(url)

    load_ongoing(q, file_queue)

    threads = start_worker_threads(args.num_worker_threads, q, file_queue)

    user_input_thread = threading.Thread(target=handle_user_input, args=(q,))
    user_input_thread.setDaemon(True)
    user_input_thread.start()

    file_input_thread = threading.Thread(target=handle_file_input, args=(q, file_queue))
    file_input_thread.setDaemon(True)
    file_input_thread.start()
    try:
        user_input_thread.join()
        file_input_thread.join()
    except KeyboardInterrupt:
        # Exiting program
        pass

    # Add sentinel values to the queue to signal worker threads to exit
    for _ in range(args.num_worker_threads):
        q.put(SENTINEL)

    # Wait for all threads to finish
    for t in threads:
        t.join()


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"Program finished in {end_time - start_time:.2f} seconds.")
