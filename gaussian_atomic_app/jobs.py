from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
import time
import uuid


@dataclass
class JobState:
    job_id: str
    status: str = 'queued'
    message: str = ''
    current_step: str = ''
    progress_current: int = 0
    progress_total: int = 0
    logs: list[str] = field(default_factory=list)
    result: dict | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class JobStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, JobState] = {}

    def create(self) -> str:
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = JobState(job_id=job_id)
        return job_id

    def update(self, job_id: str, **changes) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in changes.items():
                setattr(job, key, value)
            job.updated_at = time.time()

    def append_log(self, job_id: str, message: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.logs.append(message)
            job.updated_at = time.time()

    def snapshot(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs[job_id]
            return {
                'job_id': job.job_id,
                'status': job.status,
                'message': job.message,
                'current_step': job.current_step,
                'progress_current': job.progress_current,
                'progress_total': job.progress_total,
                'logs': list(job.logs),
                'result': job.result,
                'created_at': job.created_at,
                'updated_at': job.updated_at,
            }


job_store = JobStore()
