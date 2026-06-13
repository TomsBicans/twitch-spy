from typing import Dict, List, Optional, Union, Any, Callable
from collections import OrderedDict, defaultdict

from concurrent.futures import Future

from twitch_spy.system_logger import logger
from twitch_spy.media_downloader.atomizer import Atom
from twitch_spy.media_downloader.platform_handlers import Atomizer
import twitch_spy.media_downloader.constants as const
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID
import time
import random
import threading


class JobStats:
    def __init__(self) -> None:
        # A dictionary where each key is a status and the value is a set of job IDs having that status.
        self.jobs_by_status: Dict[str, set] = defaultdict(set)

    def update(self, job: Atom) -> None:
        """Update job ID's set based on its status."""
        # First, remove the job ID from all sets (to ensure it's not in any incorrect set)
        for status_set in self.jobs_by_status.values():
            status_set.discard(job.id)

        # Add the job ID to the set corresponding to its current status
        self.jobs_by_status[job.status.value].add(job.id)

    def get_stats(self) -> Dict[str, int]:
        """Retrieve the statistics."""
        return {status: len(job_ids) for status, job_ids in self.jobs_by_status.items()}


class JobProcessor:
    """Handles the logic to process each job."""

    @staticmethod
    def process(job: Atom) -> Atom:
        platform_handler = Atomizer.get_platform_handler(job)
        if platform_handler is None:
            job.update_status(const.PROCESS_STATUS.FAILED)
            return job
        job = platform_handler.process(job)
        return job


class JobManager:
    def __init__(
        self, job_update_callback: Callable, max_workers: Optional[int] = None
    ):
        self.jobs: Dict[UUID, Atom] = OrderedDict()
        self.stats = JobStats()
        self.job_update_callback = job_update_callback
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures: set[Future] = set()
        self.futures_lock = threading.Lock()
        self.shutting_down = False
        self.shutdown_complete = threading.Event()

    def add_job(self, job: Atom) -> None:
        self._submit_job(job, archive=True)

    def add_job_to_archive(self, job: Atom) -> None:
        self.jobs[job.id] = job
        self.send_update(job)

    def get_job(self, job_id: UUID) -> Optional[Atom]:
        return self.jobs.get(job_id)

    def get_all_jobs(self) -> List[Atom]:
        return list(self.jobs.values())

    def send_update(self, job: Atom):
        self.stats.update(job)
        self.job_update_callback(job, self.stats)

    def process_job(self, job: Atom) -> Atom:
        job.update_status(const.PROCESS_STATUS.PROCESSING)
        self.send_update(job)
        job = JobProcessor.process(job)  # Do the actual job processing here.
        return job

    def retry_job(self, job: Atom) -> None:
        job.update_status(const.PROCESS_STATUS.QUEUED)
        self.send_update(job)
        self._submit_job(job)

    def _submit_job(self, job: Atom, archive: bool = False) -> None:
        with self.futures_lock:
            if self.shutting_down:
                raise RuntimeError("Job manager is shutting down")
            if archive:
                self.add_job_to_archive(job)
            future: Future = self.executor.submit(self.process_job, job)
            self.futures.add(future)
        future.add_done_callback(self.job_done)

    def job_done(self, future: Future) -> None:
        with self.futures_lock:
            self.futures.discard(future)
        if future.cancelled():
            return
        exception: Union[BaseException, None] = future.exception()
        if exception:
            logger.error(f"Unexpected error during job processing: {exception}", exc_info=exception)
            return

        job: Atom = future.result()
        # If the platform handler explicitly marked the job as FAILED, respect it
        if job.status == const.PROCESS_STATUS.FAILED:
            self.send_update(job)
            logger.debug(f"Processing failed for job {job}")
            return
        # Otherwise, consider it finished successfully
        job.update_status(const.PROCESS_STATUS.FINISHED)
        self.send_update(job)
        logger.debug(f"Processing finished for job {job}")

    def has_active_jobs(self) -> bool:
        with self.futures_lock:
            return any(not future.done() for future in self.futures)

    def shutdown(self) -> None:
        with self.futures_lock:
            if self.shutting_down:
                already_shutting_down = True
            else:
                self.shutting_down = True
                already_shutting_down = False
        if already_shutting_down:
            self.shutdown_complete.wait()
            return
        try:
            self.executor.shutdown(wait=True, cancel_futures=True)
        finally:
            self.shutdown_complete.set()
