from src.media_downloader.atomizer import Atom
from src.media_downloader.job_manager import JobStats
from src.socket_instance import socketio
from collections import defaultdict
from enum import Enum


class Events(Enum):
    JOB_CREATED = "job_created"
    JOB_UPDATE = "job_update"
    JOB_RENDER = "job_render"
    STATISTICS_UPDATE = "statistics_update"
    ATOM_UPDATE_STATUS = "atom_update_status"


class EventDispatcher:
    def __init__(self):
        self.listeners = defaultdict(list)

    def register_listener(self, event_name: str, listener):
        self.listeners[event_name].append(listener)

    def unregister_listener(self, event_name: str, listener):
        self.listeners[event_name].remove(listener)

    def dispatch_event(self, event_name: str, *args):
        for listener in self.listeners[event_name]:
            listener(event_name, *args)


def atom_status_listener(event_name: str, atom: Atom):
    socketio.emit(  # ATOM MODEL LOCATION SOCKET
        Events.ATOM_UPDATE_STATUS.value,
        {
            "event": event_name,
            "id": str(atom.id),
            "url": atom.url,
            "url_valid": atom.url_valid,
            "platform": atom.platform.value,
            "single_item": atom.single_item,
            "content_type": atom.content_type.value,
            "content_name": str(atom.content_title),
            "download_dir": atom.download_dir,
            "media_file_os_path": atom.media_file_os_path,
            "thumbnail_image_in_base64": atom.thumbnail_image_in_base64,
            "status": atom.status.value,
        },
    )


def statistics_listener(event_name: str, stats: JobStats):
    socketio.emit(event_name, stats.get_stats())
