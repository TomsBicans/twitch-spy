import os

import pytest
import twitch_spy.media_downloader.youtube as youtube


PLAYLIST_URL = "https://www.youtube.com/playlist?list=playlist-id"


def test_download_thumbnail_uses_yt_dlp(monkeypatch, tmp_path):
    calls = {}
    video_url = "https://www.youtube.com/watch?v=video"
    cache_name = youtube.thumbnail_cache_name("Video Title", video_url)
    expected_path = tmp_path / "thumbnails" / f"{cache_name}.jpg"

    class FakeYoutubeDL:
        def __init__(self, options):
            calls["options"] = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def extract_info(self, url, download):
            calls["extract_info"] = (url, download)
            expected_path.write_bytes(b"jpeg-data")
            return {"thumbnails": [{"filepath": str(expected_path)}]}

    monkeypatch.setattr(youtube.yt_dlp, "YoutubeDL", FakeYoutubeDL)

    result = youtube.YoutubeDownloader.download_thumbnail(
        video_url, "Video Title", str(tmp_path)
    )

    assert result == str(expected_path)
    assert calls["extract_info"] == (
        video_url,
        True,
    )
    assert calls["options"]["skip_download"] is True
    assert calls["options"]["writethumbnail"] is True
    assert calls["options"]["outtmpl"]["thumbnail"].endswith(
        os.path.join("thumbnails", f"{cache_name}.%(ext)s")
    )
    assert calls["options"]["postprocessors"] == [
        {
            "key": "FFmpegThumbnailsConvertor",
            "format": "jpg",
            "when": "before_dl",
        }
    ]


def test_download_thumbnail_reuses_existing_file(monkeypatch, tmp_path):
    video_url = "https://www.youtube.com/watch?v=video"
    cache_name = youtube.thumbnail_cache_name("Video Title", video_url)
    thumbnail_path = tmp_path / "thumbnails" / f"{cache_name}.jpg"
    thumbnail_path.parent.mkdir()
    thumbnail_path.write_bytes(b"jpeg-data")

    def fail_if_called(options):
        pytest.fail("yt-dlp should not run when the thumbnail already exists")

    monkeypatch.setattr(youtube.yt_dlp, "YoutubeDL", fail_if_called)

    result = youtube.YoutubeDownloader.download_thumbnail(
        video_url, "Video Title", str(tmp_path)
    )

    assert result == str(thumbnail_path)


def test_thumbnail_cache_name_distinguishes_videos_with_same_title():
    first = youtube.thumbnail_cache_name(
        "Same Title", "https://www.youtube.com/watch?v=first"
    )
    second = youtube.thumbnail_cache_name(
        "Same Title", "https://www.youtube.com/watch?v=second"
    )

    assert first != second
    assert first.startswith("Same_Title__")
    assert second.startswith("Same_Title__")


def test_download_thumbnail_returns_none_when_unavailable(monkeypatch, tmp_path):
    class FakeYoutubeDL:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def extract_info(self, url, download):
            return {"thumbnails": []}

    monkeypatch.setattr(youtube.yt_dlp, "YoutubeDL", FakeYoutubeDL)

    result = youtube.YoutubeDownloader.download_thumbnail(
        "https://www.youtube.com/watch?v=video", "Video Title", str(tmp_path)
    )

    assert result is None


def test_add_preview_picture_embeds_downloaded_thumbnail(monkeypatch, tmp_path):
    thumbnail_path = tmp_path / "thumbnail.jpg"
    thumbnail_path.write_bytes(b"jpeg-data")
    saved_audio = {}

    class FakeAudio(dict):
        def save(self):
            saved_audio["saved"] = True

    audio = FakeAudio()
    monkeypatch.setattr(youtube, "ID3", lambda audio_path: audio)
    monkeypatch.setattr(youtube, "APIC", lambda **kwargs: kwargs)

    result = youtube.YoutubeDownloader.add_preview_picture_to_audio_file(
        str(thumbnail_path), str(tmp_path / "audio.mp3")
    )

    assert result == str(thumbnail_path)
    assert audio["APIC"]["mime"] == "image/jpeg"
    assert audio["APIC"]["data"] == b"jpeg-data"
    assert saved_audio["saved"] is True


def test_youtube_playlist_videos(monkeypatch):
    calls = {}

    class FakeYoutubeDL:
        def __init__(self, options):
            calls["options"] = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def extract_info(self, url, download):
            calls["extract_info"] = (url, download)
            return {
                "entries": [
                    {"id": "video-1", "title": "First video"},
                    None,
                    {"id": "video-2", "title": "Second video"},
                ]
            }

    monkeypatch.setattr(youtube.yt_dlp, "YoutubeDL", FakeYoutubeDL)

    videos = youtube.get_playlist_video_urls(PLAYLIST_URL)

    assert [(video.title, video.url) for video in videos] == [
        ("First video", "https://www.youtube.com/watch?v=video-1"),
        ("Second video", "https://www.youtube.com/watch?v=video-2"),
    ]
    assert calls["extract_info"] == (PLAYLIST_URL, False)
    assert calls["options"]["extract_flat"] is True


def test_youtube_playlist_title(monkeypatch):
    calls = {}

    class FakeYoutubeDL:
        def __init__(self, options):
            calls["options"] = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def extract_info(self, url, download):
            calls["extract_info"] = (url, download)
            return {"title": "Playlist title"}

    monkeypatch.setattr(youtube.yt_dlp, "YoutubeDL", FakeYoutubeDL)

    title = youtube.get_playlist_name(PLAYLIST_URL)

    assert title == "Playlist title"
    assert calls["extract_info"] == (PLAYLIST_URL, False)
    assert calls["options"]["skip_download"] is True


def test_get_video_title_uses_metadata_only_extraction(monkeypatch):
    calls = {}

    class FakeYoutubeDL:
        def __init__(self, options):
            calls["options"] = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def extract_info(self, url, download):
            calls["extract_info"] = (url, download)
            return {"title": "Video title"}

    monkeypatch.setattr(youtube.yt_dlp, "YoutubeDL", FakeYoutubeDL)

    assert youtube.get_video_title("https://www.youtube.com/watch?v=video") == (
        "Video title"
    )
    assert calls["extract_info"] == (
        "https://www.youtube.com/watch?v=video",
        False,
    )
    assert calls["options"]["skip_download"] is True
