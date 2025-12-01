"""
Job management system for tracking training job status and progress.
Provides in-memory storage for job state (can be upgraded to Redis for production).
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import json
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
    pinned: bool = False
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
    _history_path: Path = Path(__file__).resolve().parent / "job_history.json"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JobManager, cls).__new__(cls)
            cls._instance._jobs = {}
            cls._instance._load_history()
        return cls._instance
    
    def _serialize_job(self, job: TrainingJob) -> Dict[str, Any]:
        """Convert a TrainingJob to a JSON-serializable dict."""
        return {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "status": job.status.value,
            "progress": job.progress,
            "current_step": job.current_step,
            "metadata": job.metadata,
            "metrics": job.metrics,
            "error": job.error,
            "pinned": job.pinned,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

    def _deserialize_job(self, data: Dict[str, Any]) -> TrainingJob:
        """Create a TrainingJob from a serialized dict."""
        try:
            status = JobStatus(data.get("status", JobStatus.PENDING.value))
        except ValueError:
            status = JobStatus.PENDING

        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        updated_at = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else created_at
        completed_at = (
            datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        )

        return TrainingJob(
            job_id=data["job_id"],
            job_type=data.get("job_type", "unknown"),
            status=status,
            progress=int(data.get("progress", 0)),
            current_step=data.get("current_step", "Initializing..."),
            metadata=data.get("metadata", {}),
            metrics=data.get("metrics", {}),
            error=data.get("error"),
            pinned=bool(data.get("pinned", False)),
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
        )

    def _load_history(self) -> None:
        """Load job history from disk into memory."""
        try:
            if self._history_path.exists():
                with self._history_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                jobs = data.get("jobs", []) if isinstance(data, dict) else data
                for item in jobs:
                    try:
                        job = self._deserialize_job(item)
                        self._jobs[job.job_id] = job
                    except Exception as e:
                        logger.warning(f"Failed to deserialize job from history: {e}")
                logger.info(f"Loaded {len(self._jobs)} jobs from history")
        except Exception as e:
            logger.warning(f"Failed to load job history: {e}")

    def _save_history(self) -> None:
        """Persist all jobs to disk."""
        try:
            payload = {
                "jobs": [self._serialize_job(job) for job in self._jobs.values()]
            }
            with self._history_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save job history: {e}")
    
    def create_job(self, job_id: str, job_type: str, metadata: Dict[str, Any]) -> TrainingJob:
        """Create a new training job."""
        job = TrainingJob(
            job_id=job_id,
            job_type=job_type,
            metadata=metadata
        )
        self._jobs[job_id] = job
        logger.info(f"Created job {job_id} of type {job_type}")
        self._save_history()
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
        
        self._save_history()
        logger.debug(f"Updated job {job_id}: status={job.status.value}, progress={job.progress}%")
    
    def list_jobs(self) -> Dict[str, TrainingJob]:
        """List all jobs."""
        return self._jobs.copy()
    
    def set_pin(self, job_id: str, pinned: bool) -> bool:
        """Pin or unpin a job."""
        job = self._jobs.get(job_id)
        if not job:
            logger.warning(f"Attempted to set pin on non-existent job {job_id}")
            return False
        job.pinned = pinned
        job.updated_at = datetime.now()
        logger.info(f"{'Pinned' if pinned else 'Unpinned'} job {job_id}")
        return True
    
    def clear_unpinned_jobs(self) -> int:
        """Delete all jobs that are not pinned."""
        to_delete = [job_id for job_id, job in self._jobs.items() if not job.pinned]
        for job_id in to_delete:
            del self._jobs[job_id]
            logger.info(f"Deleted unpinned job {job_id}")
        self._save_history()
        return len(to_delete)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        job = self._jobs.get(job_id)
        if not job or job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            return False
        
        job.status = JobStatus.CANCELLED
        job.updated_at = datetime.now()
        logger.info(f"Cancelled job {job_id}")
        self._save_history()
        return True
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job from the manager."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.info(f"Deleted job {job_id}")
            self._save_history()
            return True
        return False

