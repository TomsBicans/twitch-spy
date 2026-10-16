import logging
from pathlib import Path
from urllib.parse import quote

import pytest
from flask import Flask

from twitch_spy.routes import home_routes


def test_stream_audio_returns_404_when_file_is_missing(monkeypatch):
    monkeypatch.setattr(home_routes.sm, "find_mp3file_with_title", lambda title: None)

    response = home_routes.stream_audio("missing")

    assert response == ("File not found", 404)


@pytest.mark.parametrize("available", [True, False])
def test_audio_title_with_slashes_does_not_reach_frontend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    available: bool,
) -> None:
    title = "K/DA - POP/STARS (ft. Madison Beer)"
    audio_path = tmp_path / "song.mp3"
    audio_bytes = b"test audio content"
    audio_path.write_bytes(audio_bytes)
    requested_titles: list[str] = []

    def find_audio(requested_title: str) -> str | None:
        requested_titles.append(requested_title)
        return str(audio_path) if available else None

    monkeypatch.setattr(home_routes.sm, "find_mp3file_with_title", find_audio)
    app = Flask(__name__)
    app.register_blueprint(home_routes.home_routes)

    @app.get("/<path:frontend_path>")
    def frontend(frontend_path: str) -> str:
        pytest.fail(f"Audio request reached frontend: {frontend_path}")

    with caplog.at_level(logging.WARNING, logger="ApplicationLogger"):
        response = app.test_client().get(f"/audio/{quote(title, safe='')}")

    assert requested_titles == [title]
    if available:
        assert response.status_code == 200
        assert response.mimetype == "audio/mpeg"
        assert response.data == audio_bytes
    else:
        assert response.status_code == 404
        assert response.data == b"File not found"
        assert title in caplog.text
    response.close()
