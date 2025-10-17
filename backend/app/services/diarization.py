from __future__ import annotations
from typing import List, Optional, Dict
from ..config import settings


def _maybe_load_pyannote():
    if not settings.diarization_enabled:
        return None
    try:
        from pyannote.audio import Pipeline  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "pyannote.audio is not installed. Install it or disable DIARIZATION_ENABLED."
        ) from e
    token = settings.hf_token
    if not token:
        raise RuntimeError(
            "HF_TOKEN is required for pyannote models. Set it in backend/.env or disable DIARIZATION_ENABLED."
        )
    return Pipeline.from_pretrained(settings.pyannote_pipeline, use_auth_token=token)


def _assign_by_overlap(segments: List[dict], diarization) -> None:
    try:
        timeline = diarization.itertracks(yield_label=True)
    except Exception:
        return
    dia = []
    for turn, _, label in timeline:
        dia.append({"start": float(turn.start), "end": float(turn.end), "speaker": str(label)})
    for seg in segments:
        s0, s1 = float(seg.get("start", 0.0)), float(seg.get("end", 0.0))
        best_label: Optional[str] = None
        best_overlap = 0.0
        for d in dia:
            ov = max(0.0, min(s1, d["end"]) - max(s0, d["start"]))
            if ov > best_overlap:
                best_overlap = ov
                best_label = d["speaker"]
        if best_label:
            seg["speaker"] = best_label


def _normalize_labels_in_place(segments: List[dict]) -> None:
    seen: list[str] = []
    # Collect in order of first appearance
    for seg in segments:
        lab = seg.get("speaker")
        if lab and lab not in seen:
            seen.append(lab)
    mapping = {lab: f"Speaker {chr(ord('A') + i)}" for i, lab in enumerate(seen[:26])}
    for seg in segments:
        lab = seg.get("speaker")
        if lab in mapping:
            seg["speaker"] = mapping[lab]


def apply_diarization(input_path: str, segments: List[dict]) -> None:
    """
    Try to assign speaker labels to segments using pyannote if enabled.
    Falls back to normalizing any existing labels. Operates in-place.
    Each segment is a dict with keys: start, end, text, (optional) speaker.
    """
    # If we already have multiple distinct speaker labels, just normalize
    initial = [s.get("speaker") for s in segments if s.get("speaker")]
    if len(set(initial)) >= 2:
        _normalize_labels_in_place(segments)
        return

    pipeline = None
    try:
        pipeline = _maybe_load_pyannote()
    except Exception:
        pipeline = None

    if pipeline is not None:
        try:
            kwargs = {}
            if settings.diarization_num_speakers is not None:
                kwargs["num_speakers"] = settings.diarization_num_speakers
            if settings.diarization_min_speakers is not None:
                kwargs["min_speakers"] = settings.diarization_min_speakers
            if settings.diarization_max_speakers is not None:
                kwargs["max_speakers"] = settings.diarization_max_speakers
            try:
                diar = pipeline(input_path, **kwargs)
            except TypeError:
                # Fallback: try only num_speakers when supported
                basic = {}
                if "num_speakers" in kwargs:
                    basic["num_speakers"] = kwargs["num_speakers"]
                diar = pipeline(input_path, **basic)
            _assign_by_overlap(segments, diar)
        except Exception:
            pass

    # Normalize any labels we might now have
    _normalize_labels_in_place(segments)

    # Smoothing: prevent rapid flip-flops and micro-turns from creating spurious speakers
    _smooth_short_turns(segments, min_turn_sec=1.0)

    # Limit extremely fragmented speaker maps: keep top speakers by total duration
    _limit_minor_speakers(segments, max_speakers=6)


def _smooth_short_turns(segments: List[dict], min_turn_sec: float = 1.0) -> None:
    prev_speaker: Optional[str] = None
    prev2_speaker: Optional[str] = None
    for i, seg in enumerate(segments):
        spk = seg.get("speaker")
        dur = float(seg.get("end", 0.0)) - float(seg.get("start", 0.0))
        if prev_speaker and spk and spk != prev_speaker and dur <= min_turn_sec:
            # Flip-flop check: A, B(short), A -> turn B into A
            next_speaker = None
            if i + 1 < len(segments):
                next_speaker = segments[i + 1].get("speaker")
            if next_speaker == prev_speaker:
                seg["speaker"] = prev_speaker
                spk = prev_speaker
            else:
                # Otherwise smooth micro-turn to previous speaker
                seg["speaker"] = prev_speaker
                spk = prev_speaker
        prev2_speaker = prev_speaker
        prev_speaker = spk


def _limit_minor_speakers(segments: List[dict], max_speakers: int = 6) -> None:
    # Compute total speaking duration per speaker label
    totals: Dict[str, float] = {}
    for seg in segments:
        spk = seg.get("speaker")
        if not spk:
            continue
        dur = float(seg.get("end", 0.0)) - float(seg.get("start", 0.0))
        totals[spk] = totals.get(spk, 0.0) + max(0.0, dur)
    if not totals:
        return
    # Keep top-N speakers; others get merged to nearest previous speaker or "Speaker Others"
    keep = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:max_speakers]
    keep_set = {k for k, _ in keep}
    last_kept: Optional[str] = None
    for seg in segments:
        spk = seg.get("speaker")
        if not spk:
            # if unknown, inherit last kept if available
            if last_kept:
                seg["speaker"] = last_kept
            continue
        if spk in keep_set:
            last_kept = spk
        else:
            seg["speaker"] = last_kept or "Speaker Others"
