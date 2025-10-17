from __future__ import annotations
from typing import List, Dict
from sqlalchemy.orm import Session
from ..models import Sentiment, Meeting, TranscriptSegment
from ..utils.id import new_id
from ..utils.text import clamp


def label_from_score(score: float) -> str:
    if score <= -0.2:
        return "negative"
    if score >= 0.2:
        return "positive"
    return "neutral"


def segments_to_sentiment(db: Session, meeting: Meeting, segments: List[TranscriptSegment]) -> List[Sentiment]:
    # Simple heuristic placeholder: length-based neutral; real implementation could call an LLM per chunk
    out: List[Sentiment] = []
    for s in segments:
        length = len(s.text)
        # naive signal: more exclamation/question leads to polarity
        pol = (s.text.count("!") - s.text.count("?") * 0.5) / max(1, length)
        score = clamp(pol, -1.0, 1.0)
        sent = Sentiment(
            id=new_id("sent"), meeting_id=meeting.id,
            start=s.start, end=s.end, score=score, label=label_from_score(score)
        )
        db.add(sent)
        out.append(sent)
    db.commit()
    return out


def aggregate_sentiment(db: Session, meeting: Meeting) -> Dict:
    rows = db.query(Sentiment).filter(Sentiment.meeting_id == meeting.id).all()
    if not rows:
        return {"label": "neutral", "score": 0.0, "rationale": "no sentiment rows"}
    avg = sum(r.score for r in rows) / max(1, len(rows))
    label = label_from_score(avg)
    return {"label": label, "score": avg, "rationale": f"average over {len(rows)} segments"}


def _polarity_of_text(text: str) -> float:
    text = (text or "").lower()
    pos_markers = ["great", "awesome", "good", "excellent", "thanks", "glad", "happy", ":)"]
    neg_markers = ["issue", "problem", "concern", "bug", "delay", "risk", "blocker", ":(", "angry"]
    score = 0.0
    for w in pos_markers:
        if w in text:
            score += 0.5
    for w in neg_markers:
        if w in text:
            score -= 0.5
    score += 0.3 * text.count("!")
    score -= 0.2 * text.count("?")
    return clamp(score, -1.0, 1.0)


def fallback_highlights(segments: List[TranscriptSegment], max_items: int = 5) -> List[Dict]:
    # Rank segments by absolute polarity magnitude and length to pick salient moments
    scored = []
    for s in segments:
        pol = _polarity_of_text(s.text)
        mag = abs(pol) * 0.7 + min(1.0, len(s.text) / 200.0) * 0.3
        scored.append((mag, pol, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    out: List[Dict] = []
    for _, pol, s in scored[:max_items]:
        label = "positive" if pol > 0.2 else ("negative" if pol < -0.2 else "contentious")
        out.append({
            "timestamp": float(s.start),
            "text": s.text.strip()[:180],
            "polarity": label,
            "reason": None,
        })
    return out


def fallback_sentiment_summary(db: Session, meeting: Meeting, segments: List[TranscriptSegment]) -> Dict:
    agg = aggregate_sentiment(db, meeting)
    agg["highlights"] = fallback_highlights(segments, max_items=6)
    # Add a vibe string based on label and polarity distribution
    lab = agg.get("label", "neutral")
    pos = sum(1 for h in agg["highlights"] if h.get("polarity") == "positive")
    neg = sum(1 for h in agg["highlights"] if h.get("polarity") == "negative")
    if lab == "neutral" and pos and neg:
        vibe = "mixed: balanced positives and concerns"
    elif lab == "positive":
        vibe = "upbeat and collaborative"
    elif lab == "negative":
        vibe = "tense with notable concerns"
    else:
        vibe = "neutral, matter-of-fact"
    agg["vibe"] = vibe
    return agg
