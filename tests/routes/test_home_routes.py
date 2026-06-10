from twitch_spy.routes import home_routes


def test_stream_audio_returns_404_when_file_is_missing(monkeypatch):
    monkeypatch.setattr(home_routes.sm, "find_mp3file_with_title", lambda title: None)

    response = home_routes.stream_audio("missing")

    assert response == ("File not found", 404)
