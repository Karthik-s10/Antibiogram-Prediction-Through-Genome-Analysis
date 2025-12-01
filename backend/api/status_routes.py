"""
Status API endpoints for monitoring training job progress.
Provides real-time status updates via polling.
"""
from fastapi import APIRouter, HTTPException
import logging

from jobs.job_manager import JobManager

router = APIRouter()
logger = logging.getLogger(__name__)
job_manager = JobManager()


@router.get("/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the current status of a training job.
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        Job status including progress, current step, and metrics
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return {
        "job_id": job_id,
        "status": job.status.value,
        "progress": job.progress,
        "current_step": job.current_step,
        "job_type": job.job_type,
        "metadata": job.metadata,
        "metrics": job.metrics,
        "error": job.error,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None
    }


@router.get("/")
async def list_all_jobs():
    """
    List all training jobs.
    
    Returns:
        List of all jobs with their current status
    """
    jobs = job_manager.list_jobs()

    # Sort jobs so that pinned jobs appear first, then by most recent
    sorted_jobs = sorted(
        jobs.items(),
        key=lambda item: (
            not getattr(item[1], "pinned", False),
            item[1].created_at
        )
    )

    return {
        "total": len(sorted_jobs),
        "jobs": [
            {
                "job_id": job_id,
                "status": job.status.value,
                "job_type": job.job_type,
                "progress": job.progress,
                "created_at": job.created_at.isoformat(),
                "pinned": getattr(job, "pinned", False),
                "metadata": job.metadata,
            }
            for job_id, job in sorted_jobs
        ]
    }


@router.delete("/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel a running training job.
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        Cancellation confirmation
    """
    success = job_manager.cancel_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found or already completed")
    
    return {
        "job_id": job_id,
        "status": "cancelled",
        "message": "Job cancelled successfully"
    }


@router.post("/{job_id}/pin")
async def pin_job(job_id: str):
    """Pin a training job."""
    success = job_manager.set_pin(job_id, True)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = job_manager.get_job(job_id)
    return {
        "job_id": job_id,
        "pinned": True,
        "status": job.status.value if job else None,
    }


@router.post("/{job_id}/unpin")
async def unpin_job(job_id: str):
    """Unpin a training job."""
    success = job_manager.set_pin(job_id, False)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = job_manager.get_job(job_id)
    return {
        "job_id": job_id,
        "pinned": False,
        "status": job.status.value if job else None,
    }


@router.delete("/")
async def clear_unpinned_jobs():
    """Delete all unpinned training jobs."""
    cleared = job_manager.clear_unpinned_jobs()
    
    return {
        "cleared": cleared,
        "message": f"Deleted {cleared} unpinned jobs"
    }

