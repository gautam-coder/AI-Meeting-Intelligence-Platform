from __future__ import annotations
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models import Meeting, File, TranscriptSegment, Summary, Decision, ActionItem
from ..utils.id import new_id
from ..utils.logging import logger
from .transcription import transcribe_file
from .embeddings import get_collection
from .llm import build_summary_prompt, ollama_generate
from .topics import infer_topics
from .extractors import extract_actions_decisions_topics
from .sentiment import segments_to_sentiment, aggregate_sentiment, fallback_sentiment_summary
from .sentiment_llm import sentiment_overview_from_chunks
from .summarizer import summarize_chunks
from .fallback import simple_summary, simple_topics, extract_action_items_and_decisions, assign_speakers_if_missing
import json
from rapidfuzz import fuzz
import json as _json
import re
from .refiner import refine_actions_and_decisions


def chunk_transcript(segments: List[TranscriptSegment], max_chars: int = 4000) -> List[str]:
    chunks: List[str] = []
    cur = ""
    for s in segments:
        piece = f"[{s.start:.1f}-{s.end:.1f}] {s.speaker or 'Speaker'}: {s.text}\n"
        if len(cur) + len(piece) > max_chars and cur:
            chunks.append(cur)
            cur = piece
        else:
            cur += piece
    if cur:
        chunks.append(cur)
    return chunks


def index_segments(meeting: Meeting, segments: List[TranscriptSegment]):
    coll = get_collection()
    ids = [seg.id for seg in segments]
    docs = [seg.text for seg in segments]
    metadatas = [{
        "meeting_id": meeting.id,
        "segment_id": seg.id,
        "start": seg.start,
        "end": seg.end,
        "speaker": seg.speaker or "",
        "title": meeting.title,
    } for seg in segments]
    coll.add(ids=ids, documents=docs, metadatas=metadatas)


def _norm_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _clean_struct_list(items):
    # items: list[dict|str]; keep dicts, normalize text, dedupe, filter too short/generic
    seen = set()
    out = []
    verbs = re.compile(r"\b(will|shall|need to|let's|please|assign|follow up|prepare|schedule|create|send|update|review|fix|investigate|implement|migrate|deploy|draft|plan|analyze|align|finalize)\b", re.I)
    for it in items or []:
        if isinstance(it, str):
            txt = _norm_text(it)
            obj = {"text": txt}
        else:
            txt = _norm_text(it.get("text", ""))
            obj = dict(it)
            obj["text"] = txt
        if not txt or len(txt.split()) < 4:
            continue
        # require a plausible action/decision verb
        if not verbs.search(txt):
            continue
        key = txt.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(obj)
        if len(out) >= 12:
            break
    return out


def _unique_topics(arr):
    seen = set()
    out = []
    for t in arr or []:
        label = t if isinstance(t, str) else t.get("label")
        if not label:
            continue
        key = str(label).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(label if isinstance(t, str) else {"label": label, "confidence": t.get("confidence")})
        if len(out) >= 10:
            break
    return out

def _upsert_summary(db: Session, meeting: Meeting, summary_text: str, key_topics, decisions, action_items, risks, sentiment_overview) -> Summary:
    # key_topics/decisions/action_items/risks/sentiment_overview are JSON-serializable
    import json as _json
    existing = db.query(Summary).filter(Summary.meeting_id == meeting.id).first()
    if existing:
        existing.summary = summary_text
        existing.key_topics = _json.dumps(key_topics) if not isinstance(key_topics, str) else key_topics
        existing.decisions = _json.dumps(decisions) if not isinstance(decisions, str) else decisions
        existing.action_items = _json.dumps(action_items) if not isinstance(action_items, str) else action_items
        existing.risks = _json.dumps(risks) if not isinstance(risks, str) else risks
        existing.sentiment_overview = _json.dumps(sentiment_overview) if not isinstance(sentiment_overview, str) else sentiment_overview
        db.commit()
        db.refresh(existing)
        return existing
    s = Summary(
        id=new_id("sum"), meeting_id=meeting.id,
        summary=summary_text,
        key_topics=_json.dumps(key_topics) if not isinstance(key_topics, str) else key_topics,
        decisions=_json.dumps(decisions) if not isinstance(decisions, str) else decisions,
        action_items=_json.dumps(action_items) if not isinstance(action_items, str) else action_items,
        risks=_json.dumps(risks) if not isinstance(risks, str) else risks,
        sentiment_overview=_json.dumps(sentiment_overview) if not isinstance(sentiment_overview, str) else sentiment_overview,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

def generate_summary(db: Session, meeting: Meeting, segments: List[TranscriptSegment]) -> Summary:
    chunks = chunk_transcript(segments)
    # Use up to first N chunks to keep within LLM token limits
    prompt = build_summary_prompt(chunks[:8])
    resp = ollama_generate(prompt, json_response=True)
    try:
        data = json.loads(resp)
    except Exception:
        data = {"summary": resp[:4000]}
    # Heuristic fallbacks when LLM omits fields
    from .fallback import simple_summary as _fs, simple_topics as _ft, extract_action_items_and_decisions as _fx
    text_summary = (data.get("summary") or "").strip()
    if not text_summary:
        text_summary = _fs(segments)
    topics_val = data.get("key_topics")
    if not topics_val:
        topics_val = _ft(segments)
    acts_llm = data.get("action_items") or []
    decs_llm = data.get("decisions") or []
    if not acts_llm or not decs_llm:
        acts_f, decs_f = _fx(segments)
        if not acts_llm:
            acts_llm = acts_f
        if not decs_llm:
            decs_llm = decs_f
    sent_over = data.get("sentiment_overview") or aggregate_sentiment(db, meeting)

    summary = _upsert_summary(
        db,
        meeting,
        text_summary,
        topics_val,
        decs_llm,
        acts_llm,
        data.get("risks") or [],
        sent_over,
    )
    # Optional: explode decisions/action_items into their tables if structured
    try:
        for d in data.get("decisions", []) or []:
            dec = Decision(id=new_id("dec"), meeting_id=meeting.id, text=d.get("text", ""), owner=d.get("owner"), timestamp=d.get("timestamp"))
            db.add(dec)
        for a in data.get("action_items", []) or []:
            ai = ActionItem(id=new_id("act"), meeting_id=meeting.id, text=a.get("text", ""), owner=a.get("owner"), timestamp=a.get("timestamp"))
            db.add(ai)
        db.commit()
    except Exception:
        pass
    return summary


def process_meeting(db: Session, meeting_id: str, progress_cb=None):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise ValueError("Meeting not found")
    logger.info(f"Processing meeting {meeting.id}")
    if progress_cb:
        try:
            progress_cb(5, "starting")
        except Exception:
            pass
    # Transcribe each source file
    files = db.scalars(select(File).where(File.meeting_id == meeting.id, File.kind == "source")).all()
    all_segments: List[TranscriptSegment] = []
    for i, f in enumerate(files):
        segs = transcribe_file(db, meeting, f.path)
        all_segments.extend(segs)
        if progress_cb:
            try:
                # Transcription progress rough estimate
                pct = 10 + int(30 * (i + 1) / max(1, len(files)))
                progress_cb(min(40, pct), "transcribed")
            except Exception:
                pass
    if not all_segments:
        raise ValueError("No segments produced; input may be silent or unsupported")
    # Normalize/assign speaker labels if missing
    assign_speakers_if_missing(all_segments)
    db.commit()
    # Basic duration
    meeting.duration_seconds = int(max((s.end for s in all_segments), default=0))
    # Index for search
    index_segments(meeting, all_segments)
    if progress_cb:
        try:
            progress_cb(55, "indexed")
        except Exception:
            pass
    # Sentiment
    segments_to_sentiment(db, meeting, all_segments)
    provisional_sent = aggregate_sentiment(db, meeting)
    if progress_cb:
        try:
            progress_cb(65, "sentiment analyzed")
        except Exception:
            pass
    # LLM-based Summary + Topics + Sentiment
    chunks = chunk_transcript(all_segments, 3000)[:10]
    try:
        merged = summarize_chunks(chunks)
        # Separate LLM pass for actions/decisions/topics
        adt = extract_actions_decisions_topics(chunks)
        acts_llm = list(adt.get("action_items") or merged.get("action_items") or [])
        decs_llm = list(adt.get("decisions") or merged.get("decisions") or [])
        topics_llm = list(adt.get("key_topics") or merged.get("key_topics") or [])

        # Clean and dedupe
        acts_llm = _merge_duplicates(_clean_struct_list(acts_llm))
        decs_llm = _merge_duplicates(_clean_struct_list(decs_llm))
        # Refinement pass with transcript context
        try:
            refined = refine_actions_and_decisions(chunks, acts_llm, decs_llm)
            acts_llm = _merge_duplicates(_clean_struct_list(refined.get("action_items") or acts_llm))
            decs_llm = _merge_duplicates(_clean_struct_list(refined.get("decisions") or decs_llm))
        except Exception:
            pass
        topics_llm = _unique_topics(topics_llm)

        # Write Summary
        summary = _upsert_summary(
            db,
            meeting,
            merged.get("summary", ""),
            topics_llm,
            decs_llm,
            acts_llm,
            merged.get("risks") or [],
            provisional_sent,
        )
        # Persist decisions/action items rows as well
        try:
            for d in decs_llm:
                db.add(Decision(id=new_id("dec"), meeting_id=meeting.id, text=d.get("text",""), owner=d.get("owner"), timestamp=d.get("timestamp") or d.get("timestamp_hint")))
            for a in acts_llm:
                db.add(ActionItem(id=new_id("act"), meeting_id=meeting.id, text=a.get("text",""), owner=a.get("owner"), timestamp=a.get("timestamp") or a.get("timestamp_hint")))
            db.commit()
        except Exception:
            pass
        # Persist topics into tags
        from ..models import TopicTag
        for label in topics_llm[:10]:
            lab = label if isinstance(label, str) else (label.get("label") if isinstance(label, dict) else str(label))
            if not lab:
                continue
            tag = TopicTag(id=new_id("topic"), meeting_id=meeting.id, label=str(lab), confidence=0.9)
            db.add(tag)
        db.commit()
    except Exception as e:
        logger.warning(f"LLM summary/topics failed: {e}; falling back")
        # Fall back to prior flow
        # Keep previous minimal fallback but avoid heuristic expansions where possible
        try:
            generate_summary(db, meeting, all_segments)
        except Exception:
            pass
    if progress_cb:
        try:
            progress_cb(75, "summary + topics done")
        except Exception:
            pass
    # LLM Sentiment overview
    try:
        sent = sentiment_overview_from_chunks(chunks)
        # ensure label/score present; else use aggregate fallback with highlights
        if not sent or not sent.get("label"):
            sent = fallback_sentiment_summary(db, meeting, all_segments)
        # Ensure highlights exist: if missing or empty, derive a fallback set
        if not isinstance(sent.get("highlights"), list) or len(sent.get("highlights") or []) == 0:
            fb = fallback_sentiment_summary(db, meeting, all_segments)
            sent["highlights"] = fb.get("highlights", [])
    except Exception as e:
        logger.warning(f"LLM sentiment failed: {e}; using aggregate")
        sent = fallback_sentiment_summary(db, meeting, all_segments)
    # Attach sentiment overview to latest summary
    try:
        latest = db.query(Summary).filter(Summary.meeting_id == meeting.id).first()
        if latest:
            latest.sentiment_overview = json.dumps(sent)
            db.commit()
    except Exception:
        pass
    if progress_cb:
        try:
            progress_cb(95, "sentiment done")
        except Exception:
            pass
    # Status
    meeting.status = "ready"
    meeting.error = None
    db.commit()
    if progress_cb:
        try:
            progress_cb(100, "completed")
        except Exception:
            pass
def _unique_topics(items):
    out = []
    seen = set()
    for v in items or []:
        lab = v if isinstance(v, str) else (v.get("label") if isinstance(v, dict) else str(v))
        if not lab:
            continue
        k = lab.strip().lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(lab)
    return out[:10]


def _clean_struct_list(items):
    out = []
    for it in items or []:
        if isinstance(it, dict):
            txt = (it.get("text") or "").strip()
            if not txt:
                continue
            out.append({k: it.get(k) for k in ["text", "owner", "due_date", "timestamp", "timestamp_hint"] if k in it})
        elif isinstance(it, str):
            if it.strip():
                out.append({"text": it.strip()})
    return out[:20]


def _norm_text(s: str) -> str:
    return " ".join((s or "").lower().split())


def _merge_duplicates(items):
    by_key = {}
    for it in items:
        key = _norm_text(it.get("text", ""))
        if not key:
            continue
        cur = by_key.get(key)
        ts = it.get("timestamp") or it.get("timestamp_hint")
        if cur is None:
            by_key[key] = it
        else:
            # prefer earliest timestamp and keep owner if missing
            cur_ts = cur.get("timestamp") or cur.get("timestamp_hint")
            if ts is not None and (cur_ts is None or ts < cur_ts):
                cur["timestamp"] = ts
            if not cur.get("owner") and it.get("owner"):
                cur["owner"] = it.get("owner")
    return list(by_key.values())


def _upsert_summary(db: Session, meeting: Meeting, summary: str, key_topics, decisions, action_items, risks, sentiment_overview) -> Summary:
    # single summary per meeting
    s = db.query(Summary).filter(Summary.meeting_id == meeting.id).first()
    if s:
        s.summary = summary
        s.key_topics = _json.dumps(key_topics) if not isinstance(key_topics, str) else key_topics
        s.decisions = _json.dumps(decisions) if not isinstance(decisions, str) else decisions
        s.action_items = _json.dumps(action_items) if not isinstance(action_items, str) else action_items
        s.risks = _json.dumps(risks) if not isinstance(risks, str) else risks
        s.sentiment_overview = _json.dumps(sentiment_overview) if not isinstance(sentiment_overview, str) else sentiment_overview
        db.commit()
        db.refresh(s)
        return s
    s = Summary(
        id=new_id("sum"),
        meeting_id=meeting.id,
        summary=summary,
        key_topics=_json.dumps(key_topics) if not isinstance(key_topics, str) else key_topics,
        decisions=_json.dumps(decisions) if not isinstance(decisions, str) else decisions,
        action_items=_json.dumps(action_items) if not isinstance(action_items, str) else action_items,
        risks=_json.dumps(risks) if not isinstance(risks, str) else risks,
        sentiment_overview=_json.dumps(sentiment_overview) if not isinstance(sentiment_overview, str) else sentiment_overview,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s
