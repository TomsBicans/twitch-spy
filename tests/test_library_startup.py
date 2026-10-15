from collections.abc import Iterator
from pathlib import Path
import threading
from unittest.mock import Mock

import pytest

from twitch_spy.app import Application
from twitch_spy.media_downloader.atomizer import Atom
from twitch_spy.media_downloader.constants import CONTENT_MODE, PROCESS_STATUS
from twitch_spy.media_downloader.storage_manager import LibraryManager, StorageManager


def saved_track(index: int, directory: Path) -> Atom:
    atom = Atom(f"https://youtube.com/watch?v={index}", CONTENT_MODE.AUDIO, str(directory))
    atom.update_status(PROCESS_STATUS.FINISHED)
    return atom


def test_server_can_respond_while_library_is_blocked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    entered = threading.Event()
    release = threading.Event()

    def scan(self: LibraryManager, stop_event: threading.Event) -> Iterator[Atom]:
        entered.set()
        assert release.wait(3)
        yield saved_track(1, tmp_path)

    monkeypatch.setattr(LibraryManager, "iter_atoms", scan)
    application = Application(frontend_dir=tmp_path)
    assert not entered.is_set()
    application.start_library_loading()
    thread = application.library_thread
    try:
        assert entered.wait(1)
        application.start_library_loading()
        assert application.library_thread is thread
        client = application.app.test_client()
        assert client.get("/health").status_code == 200
        page = client.get("/library").json
        assert page["jobs"] == []
        assert page["scan"]["state"] == "loading"
    finally:
        release.set()
        thread.join(3)
        application.job_manager.shutdown()
    assert not thread.is_alive()
    assert application.library_status() == {"state": "complete", "processed": 1, "error": None}
    assert len(client.get("/library").json["jobs"]) == 1


def test_library_batches_survive_failure_without_per_track_broadcasts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    def scan(self: LibraryManager, stop_event: threading.Event) -> Iterator[Atom]:
        for index in range(48):
            yield saved_track(index, tmp_path)
        raise OSError("Unreadable library")

    monkeypatch.setattr(LibraryManager, "iter_atoms", scan)
    application = Application(frontend_dir=tmp_path)
    callback = Mock()
    application.job_manager.job_update_callback = callback
    application.start_library_loading()
    application.library_thread.join(3)
    try:
        assert application.library_status()["state"] == "failed"
        assert application.library_status()["error"]
        assert len(application.job_manager.get_all_jobs()) == 48
        assert application.job_manager.stats.get_stats() == {"finished": 48}
        callback.assert_not_called()
    finally:
        application.job_manager.shutdown()


def test_library_cancels_between_tracks_and_preserves_live_jobs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    application = Application(frontend_dir=tmp_path)
    live = saved_track(0, tmp_path)
    application.job_manager.add_job_to_archive(live)

    def scan(stop_event: threading.Event) -> Iterator[Atom]:
        yield saved_track(0, tmp_path)
        stop_event.set()
        yield saved_track(1, tmp_path)

    monkeypatch.setattr(application.audio_library, "iter_atoms", scan)
    application.start_library_loading()
    application.library_thread.join(3)
    try:
        assert application.library_status()["state"] == "cancelled"
        assert application.job_manager.get_all_jobs() == [live]
    finally:
        application.job_manager.shutdown()


def test_library_indexes_folders_once_and_reads_artwork_only_on_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    storage = StorageManager(str(tmp_path))
    for index in range(100):
        title = f"Track {index}"
        storage.add_entry(storage.storage_file, f"https://youtube.com/watch?v={index}", title)
        (tmp_path / f"{title}.mp3").write_bytes(b"audio")
        (tmp_path / "thumbnails" / f"{title}.jpg").write_bytes(b"artwork")
    index_files = Mock(wraps=StorageManager._index_files)
    monkeypatch.setattr(StorageManager, "_index_files", staticmethod(index_files))
    monkeypatch.setattr(StorageManager, "read_img_base64", Mock(side_effect=AssertionError("Eager artwork read")))
    atoms = list(LibraryManager(str(tmp_path)).iter_atoms())
    assert len(atoms) == 100
    assert index_files.call_count == 2
    assert all(atom.media_file_os_path and atom.thumbnail_file_os_path for atom in atoms)
    assert all(atom.thumbnail_image_in_base64 is None for atom in atoms)
    application = Application(frontend_dir=tmp_path)
    application.job_manager.restore_jobs(atoms)
    try:
        client = application.app.test_client()
        job = client.get("/library").json["jobs"][0]
        assert client.get(job["thumbnail_url"]).data == b"artwork"
        Path(atoms[0].thumbnail_file_os_path).unlink()
        assert client.get(job["thumbnail_url"]).status_code == 404
    finally:
        application.job_manager.shutdown()
