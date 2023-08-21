from enum import Enum
import threading

SENTINEL = "STOP_WORKER"
stop_workers = threading.Event()


class PROCESS_STATUS(Enum):
    QUEUED = "queued"
    STARTED = "started"
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
