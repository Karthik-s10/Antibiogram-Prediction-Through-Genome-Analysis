"""
Job management system for tracking training job status and progress.
Provides in-memory storage for job state (can be upgraded to Redis for production).
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Training job status states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TrainingJob:
    """Training job data structure."""
    job_id: str
    job_type: str  # 'xgboost' or 'transformer'
    status: JobStatus = JobStatus.PENDING
    progress: int = 0  # 0-100
    current_step: str = "Initializing..."
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class JobManager:
    """
    Manages training jobs and their lifecycle.
    Uses singleton pattern to maintain state across requests.
    """
    _instance = None
    _jobs: Dict[str, TrainingJob] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JobManager, cls).__new__(cls)
            cls._instance._jobs = {}
        return cls._instance
    
    def create_job(self, job_id: str, job_type: str, metadata: Dict[str, Any]) -> TrainingJob:
        """Create a new training job."""
        job = TrainingJob(
            job_id=job_id,
            job_type=job_type,
            metadata=metadata
        )
        self._jobs[job_id] = job
        logger.info(f"Created job {job_id} of type {job_type}")
        return job
    
    def get_job(self, job_id: str) -> Optional[TrainingJob]:
        """Retrieve a job by ID."""
        return self._jobs.get(job_id)
    
    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        current_step: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Update job status and progress."""
        job = self._jobs.get(job_id)
        if not job:
            logger.warning(f"Attempted to update non-existent job {job_id}")
            return
        
        if status:
            job.status = status
            if status == JobStatus.COMPLETED:
                job.completed_at = datetime.now()
                job.progress = 100
        
        if progress is not None:
            job.progress = min(100, max(0, progress))
        
        if current_step:
            job.current_step = current_step
        
        if metrics:
            job.metrics.update(metrics)
        
        if error:
            job.error = error
            job.status = JobStatus.FAILED
        
        job.updated_at = datetime.now()
        
        logger.debug(f"Updated job {job_id}: status={job.status.value}, progress={job.progress}%")
    
    def list_jobs(self) -> Dict[str, TrainingJob]:
        """List all jobs."""
        return self._jobs.copy()
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        job = self._jobs.get(job_id)
        if not job or job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            return False
        
        job.status = JobStatus.CANCELLED
        job.updated_at = datetime.now()
        logger.info(f"Cancelled job {job_id}")
        return True
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job from the manager."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.info(f"Deleted job {job_id}")
            return True
        return False

