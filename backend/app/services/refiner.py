from __future__ import annotations
import json
from typing import List, Dict, Any
from .llm import ollama_generate, coerce_json_response


def build_refine_prompt(chunks: List[str], actions: List[Dict[str, Any]], decisions: List[Dict[str, Any]]) -> str:
    joined = "\n\n".join(chunks)
    payload = json.dumps({
        "action_items": actions,
        "decisions": decisions,
    })
    return (
        "SYSTEM: You are an expert PM/editor refining meeting outputs.\n"
        "INPUTS: (1) The meeting transcript chunks, (2) the initial lists of action items and decisions.\n"
        "GOAL: Improve quality, remove redundant or vague entries, and ensure entries are specific, atomic, and useful.\n"
        "RULES:\n"
        "- Decisions must be explicit approvals/choices/commitments taken; avoid generic observations.\n"
        "- Action items must be actionable tasks in imperative form; include owner if stated; include due_date if present.\n"
        "- Keep or infer timestamp (seconds) when a bracketed [start-end] appears near the statement; use the START as 'timestamp'.\n"
        "- Keep items concise (max ~20 words).\n"
        "- Remove duplicates and items that simply restate the summary.\n"
        "- If owner is unclear but a specific speaker said it, use that speaker label (e.g., 'Speaker A').\n"
        "- Cap lists to at most 12 items each.\n"
        "OUTPUT: STRICT JSON only: { decisions: {text, owner?, timestamp?}[], action_items: {text, owner?, due_date?, timestamp?}[] }\n\n"
        f"TRANSCRIPT CHUNKS:\n{joined}\n\n"
        f"INITIAL LISTS (JSON):\n{payload}\n\nJSON:"
    )


def refine_actions_and_decisions(chunks: List[str], actions: List[Dict[str, Any]], decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    prompt = build_refine_prompt(chunks, actions, decisions)
    resp = ollama_generate(prompt, json_response=True, temperature=0.1)
    data = coerce_json_response(resp)
    return {
        "action_items": data.get("action_items") or [],
        "decisions": data.get("decisions") or [],
    }

