from __future__ import annotations
import json
import os
import subprocess
import shutil
import tempfile
from typing import List, Optional
from sqlalchemy.orm import Session
from ..config import settings
from ..models import TranscriptSegment, Meeting
from ..utils.id import new_id
from ..utils.logging import logger
from .bootstrap import ensure_whisper_ready
from .transcription_fw import transcribe_file_faster_whisper
from .diarization import apply_diarization


def _resolve_whisper_bin() -> str:
    # Prefer configured path, else try PATH candidates
    p = settings.whisper_binary_path
    # Use explicitly configured path if it exists
    if p and os.path.exists(p) and os.access(p, os.X_OK):
        return p
    # Else, try known whisper.cpp binary names only
    for name in ("whisper.cpp", "whisper-cpp", "main"):
        found = shutil.which(name)
        if found and os.access(found, os.X_OK):
            return found
    raise FileNotFoundError(f"whisper binary not found. Set WHISPER_BIN or ensure it is in PATH")


def run_whisper_cpp(input_path: str, out_prefix: str) -> None:
    bin_path = _resolve_whisper_bin()
    args = [
        bin_path,
        "-m", settings.whisper_model_path,
        "-f", input_path,
        "-of", out_prefix,
        "-oj",  # json
        "-pp",   # print progress
        "-nt",   # no timestamps in text
        "-t", str(settings.whisper_threads),
    ]
    if settings.whisper_language:
        args += ["-l", settings.whisper_language]
    if settings.whisper_gpu_layers and settings.whisper_gpu_layers > 0:
        args += ["-ngl", str(settings.whisper_gpu_layers)]
    if settings.whisper_diarize:
        args += ["-tdrz"]

    logger.info(f"Running whisper.cpp: {' '.join(args)}")
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"whisper.cpp failed: {proc.stderr[:1000]}")


def parse_whisper_json(json_path: str) -> List[dict]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # whisper.cpp json: { 'language', 'duration', 'transcription': [ { 'text', 'timestamp': { 'from', 'to' }, 'speaker' } ] }
    trans = data.get("transcription") or []
    segments = []
    for i, seg in enumerate(trans):
        ts = seg.get("timestamp") or {}
        start = float(ts.get("from", 0))
        end = float(ts.get("to", max(start, start + 0.5)))
        speaker = seg.get("speaker")
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        segments.append({
            "start": start,
            "end": end,
            "speaker": speaker,
            "text": text,
        })
    return segments


def store_segments(db: Session, meeting: Meeting, language: Optional[str], segments: List[dict]) -> List[TranscriptSegment]:
    created: List[TranscriptSegment] = []
    for seg in segments:
        s = TranscriptSegment(
            id=new_id("seg"),
            meeting_id=meeting.id,
            start=seg["start"],
            end=seg["end"],
            speaker=seg.get("speaker"),
            text=seg["text"],
            language=language,
        )
        db.add(s)
        created.append(s)
    db.commit()
    return created


def transcribe_file_whisper_cpp(db: Session, meeting: Meeting, input_path: str) -> List[TranscriptSegment]:
    # Prepare output json path in a temp dir
    with tempfile.TemporaryDirectory() as td:
        ok, detail = ensure_whisper_ready()
        if not ok:
            raise RuntimeError(f"whisper not ready: {detail}")
        out_prefix = os.path.join(td, "out")
        run_whisper_cpp(input_path, out_prefix)
        # Load json and extract
        out_json = f"{out_prefix}.json"
        with open(out_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        language = data.get("language")
        raw_segments = parse_whisper_json(out_json)
        # Try to apply diarization/normalize speaker labels if needed
        try:
            apply_diarization(input_path, raw_segments)
        except Exception:
            pass
    return store_segments(db, meeting, language, raw_segments)


def transcribe_file(db: Session, meeting: Meeting, input_path: str) -> List[TranscriptSegment]:
    engine = (settings.transcription_engine or "whisper_cpp").lower()
    if engine == "faster_whisper":
        return transcribe_file_faster_whisper(db, meeting, input_path)
    return transcribe_file_whisper_cpp(db, meeting, input_path)
