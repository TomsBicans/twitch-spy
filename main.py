import src.video_downloader.twitch as twitch
import src.video_downloader.youtube as youtube
from src.video_downloader.storage_manager import StorageManager
from src.twitch_api import api_client
from concurrent.futures import ThreadPoolExecutor
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
        downloader = twitch.TwitchDownloader()
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
                try:
                    print(f"Downloading {vid} ...")
                    res = downloader.download_audio(vid, download_dir)
                    print(res)
                    with storage_manager.lock:
                        storage_manager.mark_successful_download(vid)
                except Exception as e:
                    traceback.print_exc()
        elif youtube.is_youtube_video(url):
            print(f"Video detected: {url}")
            try:
                print(f"Downloading {url} ...")
                res = downloader.download_audio(url, config.STREAM_DOWNLOADS)
                print(res)
            except Exception as e:
                traceback.print_exc()
                raise e
    else:
        print("Invalid platform specified.")
        exit()


def main():
    parser = argparse.ArgumentParser(
        description="Download and convert videos from different platforms"
    )
    parser.add_argument("urls", nargs="*", help="URLs of the videos to download")
    args = parser.parse_args()

    q = queue.Queue()
    num_worker_threads = 4
    threads = []

    for url in args.urls:
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
