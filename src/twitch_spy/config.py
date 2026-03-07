import os.path as path
import os

STREAM_DOWNLOADS: str = None
LOG_DIR: str = None
AUDIO_LIBRARY: str = None


def create_directory_if_not_exists(directory_path: str):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    return directory_path


def init(output_dir: str):
    global STREAM_DOWNLOADS, LOG_DIR, AUDIO_LIBRARY
    output_dir = path.abspath(output_dir)
    STREAM_DOWNLOADS = path.join(output_dir, "stream_downloads")
    LOG_DIR = path.join(output_dir, "logs")
    AUDIO_LIBRARY = path.join(STREAM_DOWNLOADS, "audio_library")
    create_directory_if_not_exists(STREAM_DOWNLOADS)
    create_directory_if_not_exists(LOG_DIR)
    create_directory_if_not_exists(AUDIO_LIBRARY)
