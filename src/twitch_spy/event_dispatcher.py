from twitch_spy.media_downloader.atomizer import Atom
from twitch_spy.media_downloader.job_manager import JobStats
from twitch_spy.socket_instance import socketio
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


def atom_to_dict(event_name: str, atom: Atom, *, include_thumbnail: bool = True) -> dict:
    data = {
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
        "status": atom.status.value,
        "error_message": atom.error_message,
    }
    if include_thumbnail:
        data["thumbnail_image_in_base64"] = atom.thumbnail_image_in_base64
    if atom.thumbnail_file_os_path or (not include_thumbnail and atom.thumbnail_image_in_base64):
        data["thumbnail_url"] = f"/jobs/{atom.id}/thumbnail"
    return data


def atom_status_listener(event_name: str, atom: Atom):
    socketio.emit(Events.ATOM_UPDATE_STATUS.value, atom_to_dict(event_name, atom))


def statistics_listener(event_name: str, stats: JobStats):
    socketio.emit(event_name, stats.get_stats())
