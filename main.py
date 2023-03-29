import src.video_downloader.twitch as twitch
import src.video_downloader.youtube as youtube
from src.video_downloader.storage_manager import StorageManager
from src.twitch_api import api_client
from concurrent.futures import ThreadPoolExecutor
from typing import Set
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


def process_queue(q: queue.Queue):
    while True:
        try:
            url = q.get(block=True)
            if url == SENTINEL:
                break
            process_url(url)
            q.task_done()
        except Exception as e:
            traceback.print_exc()


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
        res = downloader.download_audio(url, download_dir)
        print(res)
        with storage_manager.lock:
            storage_manager.mark_successful_download(url)
    except Exception as e:
        with storage_manager.lock:
            storage_manager.troublesome_download(url)
        traceback.print_exc()


def main():
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
    args = parser.parse_args()

    urls: Set[str] = set(args.urls)
    q = queue.Queue()
    num_worker_threads = args.num_worker_threads
    threads = []

    total_songs, total_duration = utils.count_songs_and_duration(
        config.STREAM_DOWNLOADS
    )
    print(f"Total songs: {total_songs}")
    print(f"Total duration: {utils.format_duration(total_duration)}")

    for url in urls:
        q.put(url)

    for _ in range(num_worker_threads):
        t = threading.Thread(target=process_queue, args=(q,))
        t.setDaemon(True)
        t.start()
        threads.append(t)

    while True:
        try:
            url = input("Enter URL: ")
            q.put(url)
        except KeyboardInterrupt:
            print("Exiting program...")
            stop_workers.set()
            break

    # Add sentinel values to the queue to signal worker threads to exit
    for _ in range(num_worker_threads):
        q.put(SENTINEL)

    # Wait for all threads to finish
    for t in threads:
        t.join()


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"Program finished in {end_time - start_time:.2f} seconds.")
