from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from ..models import Job, JobEvent
from ..utils.id import new_id


def create_job(db: Session, kind: str, meeting_id: str | None = None) -> Job:
    job = Job(id=new_id("job"), kind=kind, status="queued", meeting_id=meeting_id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def start_job(db: Session, job: Job):
    job.status = "running"
    job.started_at = datetime.utcnow()
    job.error = None
    db.commit()


def finish_job(db: Session, job: Job):
    job.status = "succeeded"
    job.finished_at = datetime.utcnow()
    db.commit()


def fail_job(db: Session, job: Job, error: str):
    job.status = "failed"
    job.finished_at = datetime.utcnow()
    job.error = error[:4000]
    db.commit()


def get_job(db: Session, job_id: str) -> Job | None:
    return db.scalar(select(Job).where(Job.id == job_id))


def add_event(db: Session, job: Job, progress: int | None = None, message: str | None = None) -> JobEvent:
    ev = JobEvent(id=new_id("je"), job_id=job.id, progress=progress, message=message)
    db.add(ev)
    db.commit()
    return ev


def update_progress(db: Session, job: Job, progress: int, message: str | None = None):
    add_event(db, job, progress=progress, message=message)


def latest_event(db: Session, job_id: str) -> JobEvent | None:
    stmt = select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.created_at.desc())
    return db.scalars(stmt).first()
