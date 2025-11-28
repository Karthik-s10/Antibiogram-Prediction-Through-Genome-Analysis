"""
Job Manager for Background Training Tasks
Manages job lifecycle, status tracking, and progress updates.
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime
import threading
import logging

logger = logging.getLogger(__name__)


class JobManager:
    """
    Manages background training jobs.
    
    Provides thread-safe job tracking with status updates and progress monitoring.
    """
    
    def __init__(self):
        """Initialize the job manager."""
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def create_job(self, job_type: str, metadata: Optional[Dict] = None) -> str:
        """
        Create a new job.
        
        Args:
            job_type: Type of job (e.g., 'xgboost', 'transformer', 'parallel')
            metadata: Optional metadata for the job
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        with self._lock:
            self.jobs[job_id] = {
                "id": job_id,
                "type": job_type,
                "status": "pending",
                "progress": 0.0,
                "message": "Job created",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
                "result": None,
                "error": None
            }
        
        logger.info(f"Created job {job_id} of type {job_type}")
        return job_id
    
    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Update job status and progress.
        
        Args:
            job_id: Job identifier
            status: New status ('pending', 'running', 'completed', 'failed')
            progress: Progress value (0.0 to 1.0)
            message: Status message
            result: Job result data
            error: Error message if failed
        """
        with self._lock:
            if job_id not in self.jobs:
                logger.warning(f"Attempted to update non-existent job {job_id}")
                return
            
            job = self.jobs[job_id]
            
            if status is not None:
                job["status"] = status
            
            if progress is not None:
                job["progress"] = min(1.0, max(0.0, progress))
            
            if message is not None:
                job["message"] = message
            
            if result is not None:
                job["result"] = result
            
            if error is not None:
                job["error"] = error
            
            job["updated_at"] = datetime.utcnow().isoformat()
        
        logger.debug(f"Updated job {job_id}: status={status}, progress={progress}")
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job information.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job data or None if not found
        """
        with self._lock:
            return self.jobs.get(job_id, None)
    
    def list_jobs(self, job_type: Optional[str] = None) -> list:
        """
        List all jobs, optionally filtered by type.
        
        Args:
            job_type: Optional job type filter
            
        Returns:
            List of job data
        """
        with self._lock:
            jobs = list(self.jobs.values())
            
            if job_type:
                jobs = [j for j in jobs if j["type"] == job_type]
            
            # Sort by creation time (newest first)
            jobs.sort(key=lambda x: x["created_at"], reverse=True)
            
            return jobs
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                logger.info(f"Deleted job {job_id}")
                return True
            return False
    
    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed/failed jobs.
        
        Args:
            max_age_hours: Maximum age in hours for completed/failed jobs
            
        Returns:
            Number of jobs deleted
        """
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        deleted_count = 0
        
        with self._lock:
            jobs_to_delete = []
            
            for job_id, job in self.jobs.items():
                if job["status"] in ["completed", "failed"]:
                    updated_at = datetime.fromisoformat(job["updated_at"])
                    if updated_at < cutoff_time:
                        jobs_to_delete.append(job_id)
            
            for job_id in jobs_to_delete:
                del self.jobs[job_id]
                deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old jobs")
        
        return deleted_count
