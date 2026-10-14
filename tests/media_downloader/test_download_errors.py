import logging
from pathlib import Path

import pytest

from twitch_spy.event_dispatcher import atom_to_dict
from twitch_spy.media_downloader.atomizer import Atom
from twitch_spy.media_downloader.constants import CONTENT_MODE, PROCESS_STATUS
from twitch_spy.media_downloader.platform_handlers import YouTubeHandler
from twitch_spy.media_downloader.storage_manager import StorageManager


def test_failure_survives_reload_and_success_clears_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    atom = Atom("https://youtube.com/watch?v=test", CONTENT_MODE.AUDIO, str(tmp_path))
    handler = YouTubeHandler()

    def fail(job: Atom) -> None:
        raise RuntimeError("Download rejected\nTry again later")

    monkeypatch.setattr(handler, "select_content_handler", lambda job: fail)
    with caplog.at_level(logging.ERROR, logger="ApplicationLogger"):
        handler.process(atom)

    assert atom.status == PROCESS_STATUS.FAILED
    assert atom.error_message == "RuntimeError: Download rejected\nTry again later"
    assert any(record.exc_info for record in caplog.records)
    reloaded = StorageManager(str(tmp_path)).generate_atoms()[0]
    assert reloaded.error_message == atom.error_message
    assert atom_to_dict("job_update", reloaded)["error_message"] == atom.error_message

    def succeed(job: Atom) -> None:
        job.content_title = "Recovered track"

    monkeypatch.setattr(handler, "select_content_handler", lambda job: succeed)
    handler.process(atom)
    storage = StorageManager(str(tmp_path))
    assert atom.error_message is None
    assert storage.read_download_error(atom.url) is None
    assert storage.read_entries(storage.failed_downloads) == []
    assert storage.generate_atoms()[0].status == PROCESS_STATUS.FINISHED


def test_legacy_failure_and_latest_error(tmp_path: Path) -> None:
    storage = StorageManager(str(tmp_path))
    url = "https://youtube.com/watch?v=test"
    storage.troublesome_download(url)
    assert storage.generate_atoms()[0].error_message is None
    storage.troublesome_download(url, error_message="First failure")
    storage.troublesome_download(url, error_message="Second failure")
    assert storage.generate_atoms()[0].error_message == "Second failure"
    assert len(storage.read_entries(storage.failed_downloads)) == 1
