import base64
from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from flask import Flask
from flask.testing import FlaskClient

from twitch_spy.media_downloader.atomizer import Atom
from twitch_spy.media_downloader.constants import CONTENT_MODE, PROCESS_STATUS
from twitch_spy.routes import home_routes
from twitch_spy.socket_instance import socketio
from twitch_spy.util import MagicStrings


@pytest.fixture
def library_client() -> Iterator[FlaskClient]:
    jobs = [
        Atom(
            f"https://youtube.com/watch?v={index}",
            CONTENT_MODE.AUDIO,
            "music",
            content_title=f"Track {index}",
            thumbnail_image_in_base64=base64.b64encode(b"artwork").decode(),
        )
        for index in range(1622)
    ]
    for job in jobs:
        job.status = PROCESS_STATUS.FINISHED
    by_id = {job.id: job for job in jobs}
    app = Flask(__name__)
    app.register_blueprint(home_routes.home_routes)
    app.config[MagicStrings.APP] = SimpleNamespace(
        library_status=lambda: {"state": "complete", "processed": 1622, "error": None},
        job_manager=SimpleNamespace(
            get_all_jobs=lambda: jobs,
            get_job=by_id.get,
            stats=SimpleNamespace(get_stats=lambda: {"finished": len(jobs)}),
        ),
    )
    with app.test_client() as client:
        yield client


def test_library_serializes_only_one_small_page(
    library_client: FlaskClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    serialize = Mock(wraps=home_routes.atom_to_dict)
    monkeypatch.setattr(home_routes, "atom_to_dict", serialize)
    response = library_client.get("/library")
    page = response.json
    assert response.status_code == 200
    assert page["total"] == 1622
    assert page["next_offset"] == 48
    assert len(page["jobs"]) == serialize.call_count == 48
    assert len(response.data) < 40_000
    assert all("thumbnail_image_in_base64" not in job for job in page["jobs"])
    assert all(job["thumbnail_url"].endswith("/thumbnail") for job in page["jobs"])
    assert page["jobs"][0]["content_name"] == "Track 0"


def test_library_pages_cover_every_track_once(library_client: FlaskClient) -> None:
    ids: list[str] = []
    offset = 0
    while offset is not None:
        page = library_client.get(f"/library?offset={offset}").json
        ids.extend(job["id"] for job in page["jobs"])
        offset = page["next_offset"]
    assert len(ids) == len(set(ids)) == 1622
    assert library_client.get("/library?offset=1622").json == {
        "jobs": [], "total": 1622, "next_offset": None,
        "scan": {"state": "complete", "processed": 1622, "error": None},
    }


@pytest.mark.parametrize("offset", ["-1", "invalid", "1.5", ""])
def test_library_rejects_invalid_offset(library_client: FlaskClient, offset: str) -> None:
    assert library_client.get(f"/library?offset={offset}").status_code == 400


def test_empty_library(library_client: FlaskClient) -> None:
    library_client.application.config[MagicStrings.APP].job_manager.get_all_jobs = lambda: []
    assert library_client.get("/library").json == {
        "jobs": [], "total": 0, "next_offset": None,
        "scan": {"state": "complete", "processed": 1622, "error": None},
    }


def test_thumbnail_is_loaded_separately(library_client: FlaskClient) -> None:
    job = library_client.get("/library").json["jobs"][0]
    response = library_client.get(job["thumbnail_url"])
    assert response.data == b"artwork"
    assert response.mimetype == "image/jpeg"
    assert response.cache_control.max_age == 3600
    assert library_client.get(f"/jobs/{uuid4()}/thumbnail").status_code == 404
    assert library_client.get("/jobs/invalid/thumbnail").status_code == 404


def test_missing_artwork_has_no_thumbnail_url(library_client: FlaskClient) -> None:
    manager = library_client.application.config[MagicStrings.APP].job_manager
    job = manager.get_all_jobs()[0]
    job.thumbnail_image_in_base64 = None
    assert "thumbnail_url" not in library_client.get("/library").json["jobs"][0]
    assert library_client.get(f"/jobs/{job.id}/thumbnail").status_code == 404


def test_statistics_request_does_not_serialize_or_broadcast_library(
    library_client: FlaskClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    serialize = Mock(side_effect=AssertionError("Statistics must not serialize tracks"))
    monkeypatch.setattr(home_routes, "atom_to_dict", serialize)
    app = library_client.application
    socketio.init_app(app)
    requester = socketio.test_client(app)
    other = socketio.test_client(app)
    try:
        requester.emit("request_statistics")
        assert requester.get_received() == [
            {"name": "statistics_update", "args": [{"finished": 1622}], "namespace": "/"},
        ]
        assert other.get_received() == []
        serialize.assert_not_called()
    finally:
        requester.disconnect()
        other.disconnect()
