from __future__ import annotations
import json
from typing import List, Dict, Any
from .llm import ollama_generate, coerce_json_response


def build_actions_decisions_topics_prompt(chunks: List[str]) -> str:
    joined = "\n\n".join(chunks)
    return (
        "SYSTEM: You are an expert meeting analyst. Use only the provided transcript. Do not invent facts.\n"
        "TASKS:\n"
        "1) Extract Decisions (explicitly stated conclusions/approvals).\n"
        "2) Extract Action Items (tasks with owners/due if present).\n"
        "3) Identify 5–12 concise Topic Tags (lowercase, 1–3 words each).\n"
        "TIMESTAMPS: If transcript shows markers like [12.3-18.9], use the start time as numeric seconds for 'timestamp'.\n"
        "OUTPUT: STRICT JSON only with fields: {\n"
        "  decisions: [{ text: string, owner?: string|null, timestamp?: number|null }],\n"
        "  action_items: [{ text: string, owner?: string|null, due_date?: string|null, timestamp?: number|null }],\n"
        "  key_topics: string[]\n"
        f"}}\n\nTRANSCRIPT:\n{joined}\n\nJSON:"
    )


def extract_actions_decisions_topics(chunks: List[str]) -> Dict[str, Any]:
    prompt = build_actions_decisions_topics_prompt(chunks)
    resp = ollama_generate(prompt, json_response=True)
    data = coerce_json_response(resp)
    # Normalize minimal structure
    out: Dict[str, Any] = {
        "decisions": data.get("decisions") or [],
        "action_items": data.get("action_items") or [],
        "key_topics": data.get("key_topics") or [],
    }
    return out

