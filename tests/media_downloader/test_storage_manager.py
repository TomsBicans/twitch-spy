import os
import tempfile
from twitch_spy.media_downloader.storage_manager import (
    StorageManager,
)


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
