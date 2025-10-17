from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class FileOut(BaseModel):
    id: str
    original_name: str
    size_bytes: int
    mime_type: Optional[str]
    kind: str

    class Config:
        from_attributes = True


class SegmentOut(BaseModel):
    id: str
    start: float
    end: float
    speaker: Optional[str]
    text: str
    confidence: Optional[float]

    class Config:
        from_attributes = True


class SummaryOut(BaseModel):
    id: str
    summary: str
    key_topics: Optional[str]
    decisions: Optional[str]
    action_items: Optional[str]
    risks: Optional[str]
    sentiment_overview: Optional[str]

    class Config:
        from_attributes = True


class DecisionOut(BaseModel):
    id: str
    text: str
    owner: Optional[str]
    timestamp: Optional[float]

    class Config:
        from_attributes = True


class ActionItemOut(BaseModel):
    id: str
    text: str
    owner: Optional[str]
    due_date: Optional[datetime]
    status: str
    timestamp: Optional[float]

    class Config:
        from_attributes = True


class TopicTagOut(BaseModel):
    id: str
    label: str
    confidence: Optional[float]

    class Config:
        from_attributes = True


class SentimentOut(BaseModel):
    id: str
    start: float
    end: float
    score: float
    label: str

    class Config:
        from_attributes = True


class MeetingCreate(BaseModel):
    title: str = Field(min_length=1)


class MeetingOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    duration_seconds: int
    language: Optional[str]
    status: str
    error: Optional[str] = None
    files: List[FileOut] = []

    class Config:
        from_attributes = True


class MeetingDetailOut(MeetingOut):
    segments: List[SegmentOut] = []
    summary: Optional[SummaryOut]
    decisions: List[DecisionOut] = []
    action_items: List[ActionItemOut] = []
    topics: List[TopicTagOut] = []
    sentiments: List[SentimentOut] = []


class SearchQuery(BaseModel):
    query: str
    top_k: int = 10


class SearchHit(BaseModel):
    meeting_id: str
    segment_id: str
    score: float
    start: float
    end: float
    text: str
    title: str


class JobOut(BaseModel):
    id: str
    meeting_id: Optional[str]
    kind: str
    status: str
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True


class JobStatusOut(JobOut):
    progress: int
    message: Optional[str]
    elapsed_seconds: float
