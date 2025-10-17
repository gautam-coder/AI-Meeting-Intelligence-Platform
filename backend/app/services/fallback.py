from __future__ import annotations
from typing import List, Tuple
import re
from collections import Counter
from ..models import TranscriptSegment


_STOPWORDS = set(
    (
        "the a an and or but if then else when while to for of in on at by with from as is are was were be been being "
        "this that those these it its it's i you we they he she them us our your their do did done have has had not no yes ok okay so right well like get got make made take took want wanted need needed think thought know know's kinda sort sortof sort-of sort of "
        "uh um hmm uh-huh mm-hmm yeah yep nope nah okay ok alright all right gonna wanna kinda sorta really just one two three four five thing things stuff stuff's going gonna" 
    ).split()
)


def _norm_word(w: str) -> str:
    w = re.sub(r"[^a-z0-9]+", "", w.lower())
    return w


def segments_text(segments: List[TranscriptSegment], max_chars: int = 5000) -> str:
    out = []
    total = 0
    for s in segments:
        line = s.text.strip()
        if not line:
            continue
        total += len(line) + 1
        if total > max_chars:
            break
        out.append(line)
    return " \n".join(out)


def simple_summary(segments: List[TranscriptSegment], max_items: int = 8) -> str:
    # Pick the longest segments as proxy for salient content
    top = sorted([s for s in segments if s.text], key=lambda x: len(x.text), reverse=True)[:max_items]
    if not top:
        return "No meaningful speech detected."
    bullets = [f"- {s.text.strip()}" for s in top]
    return "\n".join(bullets)


def simple_topics(segments: List[TranscriptSegment], top_k: int = 6) -> List[str]:
    text = segments_text(segments, max_chars=12000)
    words = [_norm_word(w) for w in re.split(r"\s+", text)]
    words = [w for w in words if w and w not in _STOPWORDS and not w.isdigit()]
    counts = Counter(words)
    # Prefer longer, content-bearing words
    ranked = sorted(counts.items(), key=lambda kv: (kv[1], len(kv[0])), reverse=True)
    return [w for w, _ in ranked[:top_k]]


def extract_action_items_and_decisions(segments: List[TranscriptSegment]) -> Tuple[List[dict], List[dict]]:
    action_patterns = [
        r"\b(follow up|assign|due|deadline|next step|prepare|schedule|create|send|update|review|fix|investigate|implement|migrate|deploy|draft|plan|analyze|align|finalize)\b",
        r"\b(will|shall|need to|should|let's|please)\b",
    ]
    decision_patterns = [r"\bdecide(d|s|rs)?\b", r"\bagreed?\b", r"\bconclude(d|s)?\b", r"\bapproved?\b", r"\bchoose(s|n)?\b", r"\bwe will\b"]
    actions: List[dict] = []
    decisions: List[dict] = []
    seen_a = set()
    seen_d = set()
    for s in segments:
        txt = s.text.strip()
        # basic cleanliness
        txt = re.sub(r"\s+", " ", txt)
        if any(re.search(p, txt, re.IGNORECASE) for p in decision_patterns):
            key = txt.lower()
            if key not in seen_d and len(txt.split()) >= 4:
                decisions.append({"text": txt, "timestamp": float(s.start)})
                seen_d.add(key)
        if any(re.search(p, txt, re.IGNORECASE) for p in action_patterns):
            key = txt.lower()
            if key not in seen_a and len(txt.split()) >= 4:
                actions.append({"text": txt, "timestamp": float(s.start)})
                seen_a.add(key)
    return actions[:12], decisions[:12]


def assign_speakers_if_missing(segments: List[TranscriptSegment]) -> None:
    # If any segment has a speaker label, normalize to Speaker A/B/C.
    unique = []
    for s in segments:
        if s.speaker and s.speaker not in unique:
            unique.append(s.speaker)
    if unique:
        mapping = {spk: f"Speaker {chr(ord('A') + i)}" for i, spk in enumerate(unique[:26])}
        for s in segments:
            if s.speaker:
                s.speaker = mapping.get(s.speaker, s.speaker)
        return
    # Otherwise, alternate speakers using pauses and duration heuristics
    current_label = "Speaker A"
    last_end = None
    for i, s in enumerate(segments):
        if last_end is None:
            s.speaker = current_label
        else:
            gap = s.start - last_end
            duration = max(0.0, (s.end - s.start))
            should_switch = gap >= 0.8 or duration >= 6.0
            if should_switch:
                current_label = "Speaker B" if current_label == "Speaker A" else "Speaker A"
            s.speaker = current_label
        last_end = s.end
    # Ensure at least two speakers appear if there are many segments
    if len(segments) >= 4 and len({s.speaker for s in segments}) == 1:
        flip = False
        for s in segments:
            if flip:
                s.speaker = "Speaker B"
            flip = not flip
