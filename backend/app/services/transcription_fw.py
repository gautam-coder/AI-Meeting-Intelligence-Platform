from __future__ import annotations
from typing import List, Optional
from sqlalchemy.orm import Session
from ..config import settings
from ..models import TranscriptSegment, Meeting
from ..utils.id import new_id
from ..utils.logging import logger
from .diarization import apply_diarization


def _load_fw():
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as e:
        raise RuntimeError("faster-whisper is not installed. Install it to use transcription_engine=faster_whisper") from e
    model_size = settings.faster_whisper_model
    compute = settings.faster_whisper_compute_type
    # device auto: CPU default; if CUDA available, faster-whisper will pick it up if compiled accordingly
    return WhisperModel(model_size, device="auto", compute_type=compute)




def transcribe_file_faster_whisper(db: Session, meeting: Meeting, input_path: str) -> List[TranscriptSegment]:
    # Ensure audio exists and model (separate from whisper.cpp model) not required to prefetch
    logger.info("Loading faster-whisper model: %s", settings.faster_whisper_model)
    model = _load_fw()
    # Transcribe; return segments with timestamps
    # We use vad_filter for cleaner segmentation.
    segments_iter, info = model.transcribe(
        input_path,
        task="transcribe",
        beam_size=5,
        vad_filter=True,
        word_timestamps=False,
        language=settings.whisper_language,
    )
    pieces: List[dict] = []
    for seg in segments_iter:
        text = (seg.text or "").strip()
        if not text:
            continue
        pieces.append({
            "start": float(seg.start),
            "end": float(seg.end),
            "text": text,
            "speaker": None,
            "confidence": None,
        })
    # Optional diarization and normalization
    try:
        apply_diarization(input_path, pieces)
    except Exception:
        pass

    # Store
    created: List[TranscriptSegment] = []
    for seg in pieces:
        s = TranscriptSegment(
            id=new_id("seg"),
            meeting_id=meeting.id,
            start=seg["start"],
            end=seg["end"],
            speaker=seg.get("speaker"),
            text=seg["text"],
            language=settings.whisper_language or None,
            confidence=seg.get("confidence"),
        )
        db.add(s)
        created.append(s)
    db.commit()
    return created
