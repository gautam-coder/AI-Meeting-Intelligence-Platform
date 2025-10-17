from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    duration_seconds = Column(Integer, default=0)
    language = Column(String, nullable=True)
    status = Column(String, default="pending", index=True)
    error = Column(Text, nullable=True)

    files = relationship("File", back_populates="meeting", cascade="all, delete-orphan")
    segments = relationship("TranscriptSegment", back_populates="meeting", cascade="all, delete-orphan")
    summary = relationship("Summary", uselist=False, back_populates="meeting", cascade="all, delete-orphan")
    sentiments = relationship("Sentiment", back_populates="meeting", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="meeting", cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")
    topics = relationship("TopicTag", back_populates="meeting", cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"
    id = Column(String, primary_key=True)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False, index=True)
    path = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    kind = Column(String, default="source")  # source/transcript/artifact

    meeting = relationship("Meeting", back_populates="files")


class TranscriptSegment(Base):
    __tablename__ = "segments"
    id = Column(String, primary_key=True)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False, index=True)
    start = Column(Float, nullable=False)
    end = Column(Float, nullable=False)
    speaker = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    language = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)

    meeting = relationship("Meeting", back_populates="segments")


class Summary(Base):
    __tablename__ = "summaries"
    id = Column(String, primary_key=True)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    key_topics = Column(Text, nullable=True)  # JSON
    decisions = Column(Text, nullable=True)   # JSON
    action_items = Column(Text, nullable=True)  # JSON
    risks = Column(Text, nullable=True)
    sentiment_overview = Column(Text, nullable=True)

    meeting = relationship("Meeting", back_populates="summary")


class Decision(Base):
    __tablename__ = "decisions"
    id = Column(String, primary_key=True)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    owner = Column(String, nullable=True)
    timestamp = Column(Float, nullable=True)

    meeting = relationship("Meeting", back_populates="decisions")


class ActionItem(Base):
    __tablename__ = "action_items"
    id = Column(String, primary_key=True)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    owner = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String, default="open")
    timestamp = Column(Float, nullable=True)

    meeting = relationship("Meeting", back_populates="action_items")


class TopicTag(Base):
    __tablename__ = "topics"
    id = Column(String, primary_key=True)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False, index=True)
    label = Column(String, index=True)
    confidence = Column(Float, nullable=True)

    meeting = relationship("Meeting", back_populates="topics")


class Sentiment(Base):
    __tablename__ = "sentiments"
    id = Column(String, primary_key=True)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False, index=True)
    start = Column(Float, nullable=False)
    end = Column(Float, nullable=False)
    score = Column(Float, nullable=False)  # -1..1
    label = Column(String, nullable=False)  # negative/neutral/positive

    meeting = relationship("Meeting", back_populates="sentiments")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=True, index=True)
    kind = Column(String, nullable=False)  # ingest/transcribe/summarize/index
    status = Column(String, default="queued")  # queued/running/succeeded/failed
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)


class JobEvent(Base):
    __tablename__ = "job_events"
    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    progress = Column(Integer, nullable=True)  # 0..100
    message = Column(String, nullable=True)
