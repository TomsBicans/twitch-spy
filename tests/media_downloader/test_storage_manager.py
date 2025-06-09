import pytest
import os
import threading
import tempfile
from src.media_downloader.storage_manager import (
    StorageManager,
    read_file,
)


def test_init():
    with tempfile.TemporaryDirectory() as tempdir:
        instance = StorageManager(tempdir)
        assert instance.download_dir == tempdir
        assert os.path.exists(os.path.join(tempdir, "storage"))
        assert os.path.exists(os.path.join(tempdir, "storage", "local_storage.txt"))
        assert os.path.exists(os.path.join(tempdir, "storage", "failed_downloads.txt"))
        assert os.path.exists(os.path.join(tempdir, "storage", "failed_split.txt"))


def test_multiton():
    with tempfile.TemporaryDirectory() as tempdir:
        instance1 = StorageManager(tempdir)
        instance2 = StorageManager(tempdir)
        print(StorageManager.describe_class())
        assert instance1 is instance2


def test_thread_safety():
    with tempfile.TemporaryDirectory() as tempdir:
        instance1 = StorageManager(tempdir)
        instance2 = None

        def set_instance():
            nonlocal instance2
            instance2 = StorageManager(tempdir)

        thread = threading.Thread(target=set_instance)
        thread.start()
        thread.join()
        assert instance1 is instance2


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
        assert (
            "http://example.com/file1"
            in read_file(instance.failed_downloads).splitlines()
        )


def test_troublesome_split():
    with tempfile.TemporaryDirectory() as tempdir:
        instance = StorageManager(tempdir)
        instance.troublesome_split("http://example.com/file1")
        assert (
            "http://example.com/file1" in read_file(instance.failed_split).splitlines()
        )
