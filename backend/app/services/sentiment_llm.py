from __future__ import annotations
import json
from typing import List, Dict, Any
from .llm import ollama_generate, coerce_json_response


def build_sentiment_prompt(chunks: List[str]) -> str:
    return (
        "SYSTEM: You are an expert meeting sentiment analyst. Use only the transcript; avoid speculation.\n"
        "TASK: Provide overall sentiment and highlight contentious/positive moments. Also produce a short 'vibe' string (1–2 sentences) that captures the emotional tone.\n"
        "HIGHLIGHTS: 3–7 items. For each, include a short text snippet, a polarity label, and optional reason.\n"
        "TIMESTAMPS: If markers like [12.3-18.9] appear, convert start time to seconds; else null.\n"
        "OUTPUT: STRICT JSON only: {\n"
        "  label: 'positive'|'neutral'|'negative'|'mixed',\n"
        "  score: number,  // -1..1\n"
        "  vibe: string,   // 1–2 sentences, descriptive tone summary\n"
        "  rationale: string, // 2–4 sentences; why you chose this label\n"
        "  highlights: [{ timestamp?: number|null, text: string, polarity: 'positive'|'negative'|'contentious', reason?: string }]\n"
        "}.\n\nTRANSCRIPT:\n"
        + "\n\n".join(chunks)
        + "\n\nJSON:"
    )


def sentiment_overview_from_chunks(chunks: List[str]) -> Dict[str, Any]:
    prompt = build_sentiment_prompt(chunks)
    resp = ollama_generate(prompt, json_response=True)
    try:
        data = coerce_json_response(resp)
        # Ensure required fields present
        if not data.get("vibe"):
            data["vibe"] = data.get("rationale") or data.get("label") or "neutral"
        return data
    except Exception:
        return {"label": "neutral", "score": 0.0, "vibe": "neutral, matter-of-fact discussion", "rationale": "fallback", "highlights": []}
