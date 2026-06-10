import os
import tempfile
import twitch_spy.media_downloader.storage_manager as storage_manager
from twitch_spy.media_downloader.storage_manager import (
    StorageManager,
    normalize_string,
)
from twitch_spy.media_downloader.youtube import thumbnail_cache_name


def test_init():
    with tempfile.TemporaryDirectory() as tempdir:
        instance = StorageManager(tempdir)
        assert instance.download_dir == tempdir
        assert os.path.exists(os.path.join(tempdir, "storage"))
        assert os.path.exists(os.path.join(tempdir, "storage", "local_storage.txt"))
        assert os.path.exists(os.path.join(tempdir, "storage", "failed_downloads.txt"))
        assert os.path.exists(os.path.join(tempdir, "storage", "failed_split.txt"))


def test_instances_are_independent():
    with tempfile.TemporaryDirectory() as tempdir:
        instance1 = StorageManager(tempdir)
        instance2 = StorageManager(tempdir)
        assert instance1 is not instance2
        assert instance1.download_dir == instance2.download_dir


def test_instances_have_independent_locks():
    with tempfile.TemporaryDirectory() as tempdir:
        instance1 = StorageManager(tempdir)
        instance2 = StorageManager(tempdir)
        assert instance1.lock is not instance2.lock


def test_already_downloaded():
    with tempfile.TemporaryDirectory() as tempdir:
        instance = StorageManager(tempdir)
        assert not instance.already_downloaded("http://example.com/file1")


def test_mark_successful_download():
    with tempfile.TemporaryDirectory() as tempdir:
        instance = StorageManager(tempdir)
        instance.mark_successful_download("http://example.com/file1")
        assert instance.already_downloaded("http://example.com/file1")


def test_entry_round_trip_preserves_commas(tmp_path):
    instance = StorageManager(str(tmp_path))
    title = "JACKBOYS, Travis Scott - OUT WEST (Audio) ft. Young Thug"

    instance.add_entry(instance.storage_file, "https://example.com/video", title)

    assert instance.read_entries(instance.storage_file) == [
        ("https://example.com/video", title, None, None)
    ]


def test_read_entries_recovers_legacy_title_with_comma(tmp_path):
    instance = StorageManager(str(tmp_path))
    title = "JACKBOYS, Travis Scott - OUT WEST (Audio) ft. Young Thug"
    with open(instance.storage_file, "w", encoding="utf-8") as storage_file:
        storage_file.write(
            "https://example.com/video,JACKBOYS, Travis Scott - OUT WEST "
            "(Audio) ft. Young Thug,None,None\n"
        )

    assert instance.read_entries(instance.storage_file) == [
        ("https://example.com/video", title, None, None)
    ]


def test_troublesome_download():
    with tempfile.TemporaryDirectory() as tempdir:
        instance = StorageManager(tempdir)
        instance.troublesome_download("http://example.com/file1")
        assert instance.read_entries(instance.failed_downloads) == [
            ("http://example.com/file1", None, None, None)
        ]


def test_troublesome_split():
    with tempfile.TemporaryDirectory() as tempdir:
        instance = StorageManager(tempdir)
        instance.troublesome_split("http://example.com/file1")
        assert instance.read_entries(instance.failed_split) == [
            ("http://example.com/file1", None, None, None)
        ]


def test_find_thumbnail_path_uses_identity_key(tmp_path):
    instance = StorageManager(str(tmp_path))
    url = "https://www.youtube.com/watch?v=video"
    thumbnail_path = (
        tmp_path
        / "thumbnails"
        / f"{thumbnail_cache_name('Video Title', url)}.jpg"
    )
    thumbnail_path.write_bytes(b"new-thumbnail")

    assert instance._find_thumbnail_path("Video Title", url, None) == str(
        thumbnail_path
    )


def test_find_thumbnail_path_falls_back_to_legacy_name(tmp_path):
    instance = StorageManager(str(tmp_path))
    thumbnail_path = tmp_path / "thumbnails" / "Video_Title.jpg"
    thumbnail_path.write_bytes(b"legacy-thumbnail")

    assert instance._find_thumbnail_path(
        "Video Title", "https://www.youtube.com/watch?v=video", None
    ) == str(thumbnail_path)


def test_normalize_string_matches_full_width_punctuation():
    assert normalize_string("WHAT TO DO?") == normalize_string("WHAT TO DO？")


def test_find_mp3file_matches_full_width_punctuation(monkeypatch, tmp_path):
    audio_path = tmp_path / "JACKBOYS, Travis Scott - WHAT TO DO？ (Audio).mp3"
    audio_path.write_bytes(b"audio")
    monkeypatch.setattr(storage_manager, "AUDIO_LIBRARY", str(tmp_path))

    result = storage_manager.find_mp3file_with_title(
        "JACKBOYS, Travis Scott - WHAT TO DO? (Audio)"
    )

    assert result == str(audio_path)
