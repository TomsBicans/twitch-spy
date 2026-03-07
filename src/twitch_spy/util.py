import math
import os
from enum import Enum


class OS:
    @staticmethod
    def read_file(file: str):
        """Read file and return content as string."""
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            return content

    @staticmethod
    def create_dir(dir: str):
        """Create the directory if it does not exist."""
        if not os.path.exists(dir):
            os.mkdir(dir)
            return dir
        else:
            return dir


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class MagicStrings(Enum):
    APP = "my_app"


def mini_print(data: list, threshold: int = None):
    """Omit data in middle of list if list size is above threshold."""
    print(len(data), threshold)
    if len(data) > threshold:
        res = []
        res.extend(data[0 : math.floor(threshold / 2)])
        res.append(f"{len(data) - threshold} items ommited.".upper())
        res.extend(data[-(math.floor(threshold / 2) + 1) :])
        return res
    else:
        return data
