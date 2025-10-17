from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone
from ..database import get_db
from ..models import Job, JobEvent
from ..schemas import JobOut


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _elapsed_seconds(job: Job) -> float:
    if job.started_at and job.finished_at:
        return (job.finished_at - job.started_at).total_seconds()
    if job.started_at:
        return (datetime.now(timezone.utc).replace(tzinfo=None) - job.started_at).total_seconds()
    return 0.0


@router.get("/{job_id}")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    # latest event
    ev = db.scalars(select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.created_at.desc())).first()
    progress = ev.progress if ev and ev.progress is not None else (100 if job.status == "succeeded" else 0)
    message = ev.message if ev and ev.message else job.status
    return {
        "id": job.id,
        "meeting_id": job.meeting_id,
        "kind": job.kind,
        "status": job.status,
        "error": job.error,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "progress": progress,
        "message": message,
        "elapsed_seconds": _elapsed_seconds(job),
    }


@router.get("/meeting/{meeting_id}")
def list_meeting_jobs(meeting_id: str, db: Session = Depends(get_db)):
    rows = db.scalars(select(Job).where(Job.meeting_id == meeting_id).order_by(Job.created_at.desc())).all()
    return [
        {"id": j.id, "kind": j.kind, "status": j.status, "created_at": j.created_at, "started_at": j.started_at, "finished_at": j.finished_at}
        for j in rows
    ]

