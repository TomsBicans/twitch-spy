from typing import Dict, List, Optional, Union, Any, Callable
from collections import OrderedDict

from concurrent.futures import Future

from src.media_downloader.atomizer import Atom
import src.media_downloader.constants as const
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID
import time
import random


class JobManager:
    def __init__(
        self, job_update_callback: Callable, max_workers: Optional[int] = None
    ):
        self.jobs: Dict[UUID, Atom] = OrderedDict()
        self.job_update_callback = job_update_callback
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=max_workers)

    def add_job(self, job: Atom) -> None:
        self.jobs[job.id] = job
        future: Future = self.executor.submit(self.process_job, job)
        future.add_done_callback(self.job_done)

    def get_job(self, job_id: UUID) -> Optional[Atom]:
        return self.jobs.get(job_id)

    def get_all_jobs(self) -> List[Atom]:
        return list(self.jobs.values())

    def process_job(self, job: Atom) -> Atom:
        # Implement the logic to process each job
        # For example, downloading a video or audio
        # ...
        # Once done, you can update the status or any other attributes of the job
        job.update_status(const.PROCESS_STATUS.PROCESSING)
        self.job_update_callback(job)

        job_time = int(random.random() * 10)
        time.sleep(job_time)
        job.update_status(const.PROCESS_STATUS.FINISHED)
        return job

    def job_done(self, future: Future) -> None:
        # This is called once a job is done. You can do any cleanup or post-processing here.
        # If the job raises an exception, you can capture it here.
        exception: Union[BaseException, None] = future.exception()
        result = future.result()
        self.job_update_callback(result)
        if exception:
            # Handle the exception, e.g., update the job status to failed
            pass
