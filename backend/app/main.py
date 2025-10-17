from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import Base, engine, SessionLocal
from .routes import meetings, search, files, jobs, setup
from sqlalchemy import select
from .models import Meeting, Summary
from .services.pipeline import process_meeting
import threading


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Post-meeting analysis platform: transcription, summaries, search.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meetings.router)
app.include_router(search.router)
app.include_router(files.router)
app.include_router(jobs.router)
app.include_router(setup.router)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}


def _backfill_missing_insights():
    db = SessionLocal()
    try:
        rows = db.scalars(select(Meeting)).all()
        for m in rows:
            has_summary = db.query(Summary).filter(Summary.meeting_id == m.id).first() is not None
            if not has_summary:
                try:
                    process_meeting(db, m.id)
                except Exception:
                    # best-effort; continue other meetings
                    pass
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    # Non-blocking backfill so existing meetings get insights dynamically
    t = threading.Thread(target=_backfill_missing_insights, daemon=True)
    t.start()
