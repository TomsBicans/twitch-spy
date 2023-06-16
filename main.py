import src.video_downloader.twitch as twitch
import src.video_downloader.youtube as youtube
import src.video_downloader.os_file_queue as FileQueue
from src.video_downloader.storage_manager import StorageManager
from src.twitch_api import api_client
from concurrent.futures import ThreadPoolExecutor
from typing import Set, List, Union, Callable
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
from enum import Enum

SENTINEL = "STOP_WORKER"
stop_workers = threading.Event()


class PROCESS_STATUS(Enum):
    SUCCESS = 1
    CANCELLED = 2
    FAILED = 3


class CONTENT_MODE(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    STREAM = "stream"


def process_twitch_url(url: str, mode: CONTENT_MODE) -> PROCESS_STATUS:
    print("Twitch url detected.")
    downloader = twitch.TwitchDownloader()
    ttv_streams = path.join(config.STREAM_DOWNLOADS, "twitch_streams")
    config.create_directory_if_not_exists(ttv_streams)
    print(f"Starting twitch stream download: {url}")
    downloader.download_stream_audio(url, ttv_streams)
    return PROCESS_STATUS.SUCCESS


def process_youtube_url(url: str, mode: CONTENT_MODE) -> PROCESS_STATUS:
    downloader = youtube.YoutubeDownloader()
    if youtube.is_youtube_playlist(url):
        return process_youtube_playlist(url, downloader, mode)
    elif youtube.is_youtube_video(url):
        return process_youtube_video(url, downloader, mode)
    else:
        print("Invalid YouTube URL.")
        return PROCESS_STATUS.FAILED


def process_youtube_playlist(
    url: str, downloader: youtube.YoutubeDownloader, mode: CONTENT_MODE
) -> PROCESS_STATUS:
    print(f"Playlist detected: {url}")
    videos = youtube.get_playlist_video_urls(url)
    print(f"Got {len(videos)} videos.")
    if mode == CONTENT_MODE.AUDIO:
        download_dir = path.join(config.STREAM_DOWNLOADS, "audio_library")
    elif mode == CONTENT_MODE.VIDEO:
        download_dir = path.join(config.STREAM_DOWNLOADS, "video_library")
    download_dir = youtube.get_playlist_download_directory(download_dir, url)
    download_dir = config.create_directory_if_not_exists(download_dir)
    storage_manager = StorageManager(download_dir)
    for i, vid in enumerate(videos):
        print(f"Processing: {i+1}/{len(videos)} ...")
        if stop_workers.is_set():
            print("Stop workers flag is set. Exiting...")
            return PROCESS_STATUS.CANCELLED
        if storage_manager.already_downloaded(vid):
            print(f"Video already exists. Will skip download: {vid}")
            continue
        if mode == CONTENT_MODE.AUDIO:
            download_audio(downloader, download_dir, storage_manager, vid)
        elif mode == CONTENT_MODE.VIDEO:
            download_video(downloader, download_dir, storage_manager, url)
    return PROCESS_STATUS.SUCCESS


def process_youtube_video(
    url: str, downloader: youtube.YoutubeDownloader, mode: CONTENT_MODE
) -> PROCESS_STATUS:
    print(f"Video detected: {url}")
    if mode == CONTENT_MODE.AUDIO:
        download_dir = path.join(config.STREAM_DOWNLOADS, "audio_library")
        download_dir = path.join(download_dir, "random_audio")
        download_dir = config.create_directory_if_not_exists(download_dir)
        storage_manager = StorageManager(download_dir)
        download_audio(downloader, download_dir, storage_manager, url)
    elif mode == CONTENT_MODE.VIDEO:
        download_dir = path.join(config.STREAM_DOWNLOADS, "video_library")
        download_dir = path.join(download_dir, "random_videos")
        download_dir = config.create_directory_if_not_exists(download_dir)
        storage_manager = StorageManager(download_dir)
        download_video(downloader, download_dir, storage_manager, url)
    return PROCESS_STATUS.SUCCESS


def process_url(url: str, mode: CONTENT_MODE) -> PROCESS_STATUS:
    if "twitch.tv" in url:
        return process_twitch_url(url, mode)
    elif "youtube.com" in url:
        return process_youtube_url(url, mode)
    else:
        print("Invalid platform specified.")
        return PROCESS_STATUS.FAILED


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
        split_length_criteria = 60 * 180  # 180 minutes
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


def download_video(
    downloader: youtube.YoutubeDownloader,
    download_dir: str,
    storage_manager: StorageManager,
    url: str,
):
    try:
        print(f"Downloading {url} ...")
        audio_file = downloader.download_video(url, download_dir)
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
        split_length_criteria = 60 * 180  # 180 minutes
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
    num_worker_threads: int,
    q: queue.Queue,
    file_queue: FileQueue.OSFileQueue,
    process_function: Callable,
    content_mode: CONTENT_MODE,
) -> List[threading.Thread]:
    threads = []
    for _ in range(num_worker_threads):
        t = threading.Thread(
            target=process_function, args=(q, file_queue, content_mode)
        )
        t.setDaemon(True)
        t.start()
        threads.append(t)
    return threads


def preprocess_url(url: str) -> str:
    if "watch?v" in url and "&list=" in url:
        url = url.split("&list=")[0]
    return url


def process_queue(
    q: queue.Queue, file_queue: FileQueue.OSFileQueue, mode: CONTENT_MODE
):
    while True:
        try:
            url = q.get(block=True)
            if url == SENTINEL:
                break
            file_queue.remove_from_input(url)
            url = preprocess_url(url)
            file_queue.add_to_ongoing(url)
            status = process_url(url, mode)
            if status == PROCESS_STATUS.SUCCESS:
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
        file_queue.format_input_file()
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
    audio_file_queue = FileQueue.OSFileQueue(config.STREAM_DOWNLOADS, "audio")
    video_file_queue = FileQueue.OSFileQueue(config.STREAM_DOWNLOADS, "video")
    audio_q = queue.Queue()
    video_q = queue.Queue()

    for url in set(args.urls):
        audio_file_queue.add_to_input(url)

    load_ongoing(audio_q, audio_file_queue)

    audio_threads = start_worker_threads(
        args.num_worker_threads,
        audio_q,
        audio_file_queue,
        process_queue,
        CONTENT_MODE.AUDIO,
    )

    video_threads = start_worker_threads(
        args.num_worker_threads,
        video_q,
        video_file_queue,
        process_queue,
        CONTENT_MODE.VIDEO,
    )

    user_input_thread = threading.Thread(target=handle_user_input, args=(audio_q,))
    user_input_thread.setDaemon(True)
    user_input_thread.start()

    audio_file_input_thread = threading.Thread(
        target=handle_file_input, args=(audio_q, audio_file_queue)
    )
    audio_file_input_thread.setDaemon(True)
    audio_file_input_thread.start()

    video_file_input_thread = threading.Thread(
        target=handle_file_input, args=(video_q, video_file_queue)
    )
    video_file_input_thread.setDaemon(True)
    video_file_input_thread.start()

    try:
        user_input_thread.join()
        audio_file_input_thread.join()
        video_file_input_thread.join()
    except KeyboardInterrupt:
        # Exiting program
        pass

    # Add sentinel values to the queue to signal worker threads to exit
    for _ in range(args.num_worker_threads):
        video_q.put(SENTINEL)
        audio_q.put(SENTINEL)

    # Wait for all threads to finish
    for t in audio_threads:
        t.join()
    for t in video_threads:
        t.join()


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"Program finished in {end_time - start_time:.2f} seconds.")
