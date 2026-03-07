from enum import Enum
import threading

SENTINEL = "STOP_WORKER"
stop_workers = threading.Event()
lock = threading.Lock()


class PROCESS_STATUS(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    FAILED = "failed"
    INVALID = "invalid"


class CONTENT_MODE(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    STREAM = "stream"


class PLATFORM(Enum):
    YOUTUBE = "youtube"
    TWITCH = "twitch"
    UNDEFINED = None
