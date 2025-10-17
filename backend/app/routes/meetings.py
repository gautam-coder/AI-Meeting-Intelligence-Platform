from __future__ import annotations
from fastapi import APIRouter, Depends, UploadFile, File as FastAPIFile, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
import shutil
import os
from ..database import get_db
from ..schemas import MeetingCreate, MeetingOut, MeetingDetailOut, JobOut
from ..models import Meeting, File
from ..services import jobs as jobsvc
from ..services.pipeline import process_meeting
from ..services.storage import save_upload
from ..config import settings
from ..utils.id import new_id


router = APIRouter(prefix="/api/meetings", tags=["meetings"])


# Support both with and without trailing slash to avoid 307 redirects
@router.post("/", response_model=MeetingOut)
@router.post("", response_model=MeetingOut)
def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db)):
    m = Meeting(id=new_id("mtg"), title=payload.title, status="created")
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.get("/", response_model=list[MeetingOut])
@router.get("", response_model=list[MeetingOut])
def list_meetings(db: Session = Depends(get_db)):
    rows = db.scalars(select(Meeting).order_by(Meeting.created_at.desc())).all()
    return rows


@router.get("/{meeting_id}", response_model=MeetingDetailOut)
def get_meeting(meeting_id: str, db: Session = Depends(get_db)):
    m = db.get(Meeting, meeting_id)
    if not m:
        raise HTTPException(status_code=404, detail="Not found")
    return m


@router.post("/{meeting_id}/upload", response_model=MeetingOut)
def upload_file(meeting_id: str, upload: UploadFile = FastAPIFile(...), auto: bool = Query(True), background: BackgroundTasks = None, db: Session = Depends(get_db)):
    m = db.get(Meeting, meeting_id)
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    # Validate extension
    ext = (os.path.splitext(upload.filename or "")[1] or "").lstrip(".").lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")
    # Write to a secure temp file, then move to uploads dir
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        shutil.copyfileobj(upload.file, tmp)
        tmp_path = tmp.name
    path, size = save_upload(tmp_path, upload.filename or "upload")
    if size > settings.max_upload_mb * 1024 * 1024:
        os.remove(path)
        raise HTTPException(status_code=400, detail="File too large")
    f = File(id=new_id("file"), meeting_id=m.id, path=path, original_name=upload.filename or os.path.basename(path), size_bytes=size, mime_type=upload.content_type or None, kind="source")
    db.add(f)
    m.status = "uploaded"
    db.commit()
    db.refresh(m)
    # Automatically start processing if requested
    if auto:
        job = jobsvc.create_job(db, kind="process", meeting_id=meeting_id)

        def _run(job_id: str):
            j = jobsvc.get_job(db, job_id)
            if not j:
                return
            try:
                jobsvc.start_job(db, j)

                def progress_cb(pct: int, msg: str | None = None):
                    jobsvc.update_progress(db, j, pct, msg)

                progress_cb(1, "queued")
                process_meeting(db, meeting_id, progress_cb=progress_cb)
                jobsvc.finish_job(db, j)
            except Exception as e:
                jobsvc.fail_job(db, j, str(e))
                mm = db.get(Meeting, meeting_id)
                if mm:
                    mm.status = "error"
                    mm.error = str(e)
                    db.commit()

        background.add_task(_run, job.id)
    return m


@router.post("/{meeting_id}/process", response_model=JobOut)
def start_processing(meeting_id: str, background: BackgroundTasks, force: bool = Query(False), db: Session = Depends(get_db)):
    m = db.get(Meeting, meeting_id)
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    job = jobsvc.create_job(db, kind="process", meeting_id=meeting_id)

    def _run(job_id: str):
        j = jobsvc.get_job(db, job_id)
        if not j:
            return
        try:
            jobsvc.start_job(db, j)
            def progress_cb(pct: int, msg: str | None = None):
                jobsvc.update_progress(db, j, pct, msg)

            progress_cb(1, "queued")
            process_meeting(db, meeting_id, progress_cb=progress_cb)
            jobsvc.finish_job(db, j)
        except Exception as e:
            jobsvc.fail_job(db, j, str(e))
            m = db.get(Meeting, meeting_id)
            if m:
                m.status = "error"
                m.error = str(e)
                db.commit()

    background.add_task(_run, job.id)
    return job


@router.post("/reprocess_all")
def reprocess_all(background: BackgroundTasks, db: Session = Depends(get_db)):
    meetings = db.scalars(select(Meeting).order_by(Meeting.created_at.desc())).all()
    job_ids: list[str] = []
    for mtg in meetings:
        job = jobsvc.create_job(db, kind="process", meeting_id=mtg.id)
        job_ids.append(job.id)

        def _run(job_id: str, mid: str):
            j = jobsvc.get_job(db, job_id)
            if not j:
                return
            try:
                jobsvc.start_job(db, j)
                process_meeting(db, mid)
                jobsvc.finish_job(db, j)
            except Exception as e:
                jobsvc.fail_job(db, j, str(e))
                mm = db.get(Meeting, mid)
                if mm:
                    mm.status = "error"
                    mm.error = str(e)
                    db.commit()

        background.add_task(_run, job.id, mtg.id)
    return {"count": len(job_ids), "jobs": job_ids}
