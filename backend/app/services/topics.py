from __future__ import annotations
import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from ..models import TopicTag, Meeting
from ..utils.id import new_id
from .llm import build_topics_prompt, ollama_generate, coerce_json_response


def _normalize_topics_payload(data: Any) -> List[Any]:
    # Accept array, or dict with a list under known keys, or values of dict
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("topics", "tags", "labels", "items"):
            v = data.get(k)
            if isinstance(v, list):
                return v
        # fallback: use dict values
        return list(data.values())
    return []


def infer_topics(db: Session, meeting: Meeting, chunks: List[str]) -> List[TopicTag]:
    prompt = build_topics_prompt(chunks)
    resp = ollama_generate(prompt, json_response=True)
    try:
        parsed = coerce_json_response(resp)
    except Exception:
        parsed = []
    arr = _normalize_topics_payload(parsed)
    out: List[TopicTag] = []
    for t in arr[:10]:
        label = (t.get("label") if isinstance(t, dict) else str(t)).strip()
        if not label:
            continue
        try:
            conf = float(t.get("confidence", 0.7)) if isinstance(t, dict) else 0.7
        except Exception:
            conf = 0.7
        tag = TopicTag(id=new_id("topic"), meeting_id=meeting.id, label=label, confidence=conf)
        db.add(tag)
        out.append(tag)
    db.commit()
    return out
