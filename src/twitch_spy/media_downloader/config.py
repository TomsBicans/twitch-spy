import os.path as path
import sys
import os
MODULE_DIR = path.dirname(__file__)
SOURCE_DIR = path.dirname(MODULE_DIR)

sys.path.extend([SOURCE_DIR])


def create_directory_if_not_exists(directory_path: str):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
