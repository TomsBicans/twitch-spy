from typing import Dict, List, Optional, Union, Any, Callable
from collections import OrderedDict, defaultdict

from concurrent.futures import Future

from src.system_logger import logger
from src.media_downloader.atomizer import Atom
from src.media_downloader.platform_handlers import Atomizer
import src.media_downloader.constants as const
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID
import time
import random


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

        job_time = int(random.random() * 10)
        time.sleep(job_time)
        return job


class JobManager:
    def __init__(
        self, job_update_callback: Callable, max_workers: Optional[int] = None
    ):
        self.jobs: Dict[UUID, Atom] = OrderedDict()
        self.stats = JobStats()
        self.job_update_callback = job_update_callback
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=max_workers)

    def add_job(self, job: Atom) -> None:
        self.jobs[job.id] = job
        self.send_update(job)
        future: Future = self.executor.submit(self.process_job, job)
        future.add_done_callback(self.job_done)

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

    def job_done(self, future: Future) -> None:
        # This is called once a job is done. You can do any cleanup or post-processing here.
        # If the job raises an exception, you can capture it here.
        exception: Union[BaseException, None] = future.exception()

        job: Atom = future.result()

        if exception:
            # Handle the exception, e.g., update the job status to failed
            job.update_status(const.PROCESS_STATUS.FAILED)
            self.send_update(job)
            logger.debug(f"Processing failed for job {job}")
            return
        job.update_status(const.PROCESS_STATUS.FINISHED)
        self.send_update(job)
        logger.debug(f"Processing finished for job {job}")
