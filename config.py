import os.path as path
import sys
import os

ROOT_DIR = path.dirname(__file__)
STREAM_DOWNLOADS = path.join(ROOT_DIR, "stream_downloads")
LOG_DIR = path.abspath(path.join(ROOT_DIR, "logs"))


def create_directory_if_not_exists(directory_path: str):
    """
    Creates a directory if it does not exist.
    :param directory_path: The path of the directory to create.
    :return: None
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    return directory_path


create_directory_if_not_exists(STREAM_DOWNLOADS)
