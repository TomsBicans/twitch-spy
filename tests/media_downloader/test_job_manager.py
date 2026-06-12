import threading
import time
from concurrent.futures import Future

import pytest

from twitch_spy.media_downloader.atomizer import Atom
from twitch_spy.media_downloader.constants import CONTENT_MODE
from twitch_spy.media_downloader.job_manager import JobManager


def make_atom(tmp_path, name="video"):
    return Atom(
        f"https://youtube.com/watch?v={name}",
        CONTENT_MODE.AUDIO,
        str(tmp_path),
    )


def test_shutdown_finishes_active_job_and_cancels_queued_job(monkeypatch, tmp_path):
    manager = JobManager(lambda *_args: None, max_workers=1)
    active_started = threading.Event()
    release_active = threading.Event()
    processed = []

    def process(job):
        processed.append(job.url)
        active_started.set()
        release_active.wait(timeout=2)
        return job

    monkeypatch.setattr(manager, "process_job", process)
    first = make_atom(tmp_path, "first")
    second = make_atom(tmp_path, "second")
    manager.add_job(first)
    assert active_started.wait(timeout=1)
    manager.add_job(second)

    shutdown_thread = threading.Thread(target=manager.shutdown)
    shutdown_thread.start()
    time.sleep(0.05)
    assert shutdown_thread.is_alive()
    release_active.set()
    shutdown_thread.join(timeout=2)

    assert not shutdown_thread.is_alive()
    assert processed == [first.url]
    assert not manager.has_active_jobs()
    with pytest.raises(RuntimeError, match="shutting down"):
        manager.add_job(make_atom(tmp_path, "third"))
    manager.shutdown()


def test_future_completion_and_active_check_are_synchronized(tmp_path):
    manager = JobManager(lambda *_args: None, max_workers=1)
    manager.shutdown()
    future = Future()
    job = make_atom(tmp_path)
    future.set_result(job)
    entered_done = threading.Event()
    release_done = threading.Event()

    def controlled_done():
        entered_done.set()
        release_done.wait(timeout=2)
        return False

    future.done = controlled_done
    with manager.futures_lock:
        manager.futures.add(future)

    active_thread = threading.Thread(target=manager.has_active_jobs)
    completion_thread = threading.Thread(target=manager.job_done, args=(future,))
    active_thread.start()
    assert entered_done.wait(timeout=1)
    completion_thread.start()
    time.sleep(0.05)
    assert completion_thread.is_alive()
    release_done.set()
    active_thread.join(timeout=2)
    completion_thread.join(timeout=2)

    assert not active_thread.is_alive()
    assert not completion_thread.is_alive()
    assert future not in manager.futures
