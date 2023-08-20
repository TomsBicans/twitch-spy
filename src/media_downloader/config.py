import os.path as path
import sys
import os
MODULE_DIR = path.dirname(__file__)
SOURCE_DIR = path.dirname(MODULE_DIR)
DOWNLOADS_DIR = path.join(MODULE_DIR, "downloads")

sys.path.extend([SOURCE_DIR])


def create_directory_if_not_exists(directory_path: str):
    """
    Creates a directory if it does not exist.
    :param directory_path: The path of the directory to create.
    :return: None
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


create_directory_if_not_exists(DOWNLOADS_DIR)
