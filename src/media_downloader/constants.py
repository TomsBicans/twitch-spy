from enum import Enum
import threading

SENTINEL = "STOP_WORKER"
stop_workers = threading.Event()


class PROCESS_STATUS(Enum):
    SUCCESS = 1
    CANCELLED = 2
    FAILED = 3
    INVALID = 4


class CONTENT_MODE(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    STREAM = "stream"


class PLATFORM(Enum):
    YOUTUBE = "youtube"
    TWITCH = "twitch"
    UNDEFINED = None
