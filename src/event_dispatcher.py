from src.media_downloader.atomizer import Atom
from src.socket_instance import socketio


class EventDispatcher:
    def __init__(self):
        self.listeners = []

    def register_listener(self, listener):
        self.listeners.append(listener)

    def unregister_listener(self, listener):
        self.listeners.remove(listener)

    def dispatch_event(self, event_name: str, atom: Atom):
        for listener in self.listeners:
            listener(event_name, atom)


def atom_status_listener(event_name: str, atom: Atom):
    # print(f"Received event: {event_name}")
    # print(f"Atom: {atom}")
    socketio.emit(
        "atom_update_status",
        {
            "event": event_name,
            "id": str(atom.id),
            "content_name": str(atom.content_name),
            "content_type": atom.content_type.value,
            "url": atom.url,
            "status": atom.status.value,
        },
    )
