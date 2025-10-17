from __future__ import annotations
import json
from typing import List, Dict, Any
from .llm import ollama_generate, coerce_json_response


# def build_chunk_prompt(chunk: str) -> str:
#     return (
#         "SYSTEM: You are an expert meeting analyst. Extract only what is explicitly present. Do not invent names, dates, or facts.\n"
#         "TASK: Given this transcript chunk, produce: (a) 3-7 concise summary bullets, (b) decisions, (c) action items with owners/due if stated, (d) topic tags.\n"
#         "TIMESTAMPS: If the chunk shows markers like [12.3-18.9], use the start time as a string in 'timestamp_hint'. If unknown, use null.\n"
#         "OUTPUT: STRICT JSON. No extra text. Schema: {\n"
#         "  summary_bullets: string[],\n"
#         "  decisions: { text: string, owner?: string|null, timestamp_hint?: string|null }[],\n"
#         "  action_items: { text: string, owner?: string|null, due_date?: string|null, timestamp_hint?: string|null }[],\n"
#         "  topics: string[]\n"
#         "}\n\nTRANSCRIPT CHUNK:\n"
#         f"{chunk}\n\nJSON:"
#     )

def build_chunk_prompt(chunk: str) -> str:
    return (
        "SYSTEM: You are an expert meeting analyst. Extract only what is explicitly present in the transcript; do not invent names, dates, or facts.\n"
        "GOAL: Parse this meeting segment into structured JSON suitable for post-meeting intelligence and vector indexing.\n\n"
        "TASK:\n"
        "1. Summarize the chunk into 3–7 concise factual bullets.\n"
        "2. Identify explicit decisions or conclusions (with owner/timestamp if mentioned).\n"
        "3. Extract action items (with owner/due date if mentioned).\n"
        "4. Detect overall sentiment of the conversation in this chunk (Positive, Neutral, Negative, or Mixed).\n"
        "5. Capture any explicit speaker mentions (e.g., 'Alice', 'Project Lead'). If none, return null.\n"
        "6. Generate 3–6 topic tags relevant for later search (e.g., 'budget planning', 'product launch').\n"
        "7. Use the start timestamp if visible like [12.3-18.9] as 'timestamp_hint'; else null.\n\n"
        "OUTPUT: STRICT JSON only. No prose or commentary.\n"
        "Schema:\n"
        "{\n"
        "  summary_bullets: string[],\n"
        "  decisions: [{ text: string, owner?: string|null, timestamp_hint?: string|null }],\n"
        "  action_items: [{ text: string, owner?: string|null, due_date?: string|null, timestamp_hint?: string|null }],\n"
        "  sentiment: string,  // one of ['Positive','Neutral','Negative','Mixed']\n"
        "  speakers: string[]|null,\n"
        "  topics: string[]\n"
        "}\n\n"
        f"TRANSCRIPT CHUNK:\n{chunk}\n\nJSON:"
    )

# def build_merge_prompt(parts_json: List[str]) -> str:
#     joined = "\n".join(parts_json)
#     return (
#         "SYSTEM: You are a senior meeting analyst. Use only the provided chunk JSONs (no speculation).\n"
#         "TASK: Merge per-chunk notes into a single, comprehensive report: deduplicate near-identical items, preserve meaning, and keep owners/dates if present.\n"
#         "SUMMARY REQUIREMENTS: Produce a well-structured Markdown report (not a one-liner) with sections: \n"
#         "  # Meeting Summary\n  ## Executive Summary (5-10 bullets)\n  ## Detailed Notes (3-6 short paragraphs)\n  ## Timeline Highlights (bullet list with mm:ss timestamps if available)\n  ## Decisions\n  ## Action Items\n  ## Key Topics\n  ## Risks (if any)\n"
#         "LENGTH: Aim for 300-800 words; include only facts present in the chunks.\n"
#         "TOPICS: Provide 3-8 key topics ranked by prominence.\n"
#         "DECISIONS/ACTIONS: Merge duplicates; keep the earliest timestamp if multiple. Convert any timestamp_hint to numeric seconds if present, else null.\n"
#         "RISKS: Extract notable risks or blockers if present; else an empty list.\n"
#         "OUTPUT: STRICT JSON only with fields: {\n"
#         "  summary: string,\n"
#         "  key_topics: string[],\n"
#         "  decisions: { text: string, owner?: string|null, timestamp?: number|null }[],\n"
#         "  action_items: { text: string, owner?: string|null, due_date?: string|null, timestamp?: number|null }[],\n"
#         "  risks: string[],\n"
#         "  highlights?: { timestamp?: number|null, text: string }[]\n"
#         f"}}\n\nCHUNK JSONS (one per line):\n{joined}\n\nJSON:"
#     )
def build_merge_prompt(parts_json: List[str]) -> str:
    joined = "\n".join(parts_json)
    return (
        "SYSTEM: You are a senior AI meeting analyst synthesizing multiple chunk analyses into a unified meeting report.\n"
        "CONSTRAINTS:\n"
        "- Use only facts present in the input JSONs.\n"
        "- Deduplicate similar items; retain earliest timestamps and any explicit owners/dates.\n"
        "- Merge sentiments into an overall meeting sentiment (Positive/Neutral/Negative/Mixed).\n\n"
        "TASK: Produce a structured JSON report. The 'summary' must be narrative-only Markdown (no duplicate lists).\n\n"
        "OUTPUT REQUIREMENTS:\n"
        "  summary: Markdown with sections ONLY:\n"
        "    # Meeting Summary\n"
        "    ## Executive Summary (5–10 bullets)\n"
        "    ## Detailed Notes (3–6 short paragraphs)\n"
        "    ## Timeline Highlights (bullet list with timestamps if available)\n"
        "  Do NOT include Decisions, Action Items, Key Topics, or Risks inside 'summary'.\n\n"
        "OUTPUT: STRICT JSON only.\n"
        "Schema:\n"
        "{\n"
        "  summary: string,\n"
        "  overall_sentiment: string,  // one of ['Positive','Neutral','Negative','Mixed']\n"
        "  key_topics: string[],\n"
        "  decisions: [{ text: string, owner?: string|null, timestamp?: number|null }],\n"
        "  action_items: [{ text: string, owner?: string|null, due_date?: string|null, timestamp?: number|null }],\n"
        "  risks: string[],\n"
        "  highlights?: [{ timestamp?: number|null, text: string }]\n"
        f"}}\n\nCHUNK JSONS (one per line):\n{joined}\n\nJSON:"
    )


def summarize_chunks(chunks: List[str]) -> Dict[str, Any]:
    parts: List[Dict[str, Any]] = []
    for ch in chunks:
        prompt = build_chunk_prompt(ch)
        resp = ollama_generate(prompt, json_response=True)
        print("Chunk summary response:", resp)
        try:
            data = coerce_json_response(resp)
            parts.append(data)
        except Exception:
            # fallback minimal
            parts.append({"summary_bullets": [ch[:200]], "decisions": [], "action_items": [], "topics": []})
    prompt_merge = build_merge_prompt([json.dumps(p) for p in parts])
    final_resp = ollama_generate(prompt_merge, json_response=True)
    try:
        out = coerce_json_response(final_resp)
    except Exception:
        # fallback merge
        bullets = []
        topics = []
        decs: List[Dict[str, Any]] = []
        acts: List[Dict[str, Any]] = []
        for p in parts:
            bullets.extend(p.get("summary_bullets", []) or [])
            topics.extend(p.get("topics", []) or [])
            decs.extend(p.get("decisions", []) or [])
            acts.extend(p.get("action_items", []) or [])
        out = {
            "summary": "\n".join(f"- {b}" for b in bullets[:10]),
            "key_topics": list(dict.fromkeys(topics))[:10],
            "decisions": decs[:10],
            "action_items": acts[:10],
            "risks": [],
        }
    # Ensure summary is comprehensive; if too short, synthesize a structured Markdown (narrative only)
    try:
        summary_text = (out.get("summary") or "").strip()
        if len(summary_text) < 400:  # minimum threshold for comprehensiveness
            topics = out.get("key_topics") or []
            decisions = out.get("decisions") or []
            actions = out.get("action_items") or []
            risks = out.get("risks") or []
            highlights = out.get("highlights") or []
            def _fmt_time(sec):
                try:
                    sec = int(sec or 0)
                    return f"{sec//60:02d}:{sec%60:02d}"
                except Exception:
                    return None
            lines = []
            lines.append("# Meeting Summary")
            # Executive Summary from topics/decisions/actions heuristics
            lines.append("## Executive Summary")
            es = []
            for t in topics[:6]:
                es.append(f"- Key topic: {t}")
            for d in decisions[:3]:
                if d.get("text"):
                    es.append(f"- Decision: {d['text']}")
            for a in actions[:3]:
                if a.get("text"):
                    es.append(f"- Action: {a['text']}")
            if not es:
                es.append("- Discussion covered multiple topics and follow-ups.")
            lines.extend(es[:10])
            # Detailed Notes (fallback from bullets we had per chunk)
            lines.append("\n## Detailed Notes")
            # Try to reconstruct from parts summary_bullets
            notes_added = 0
            for p in parts:
                for b in (p.get("summary_bullets") or [])[:2]:
                    lines.append(f"- {b}")
                    notes_added += 1
                    if notes_added >= 10:
                        break
                if notes_added >= 10:
                    break
            if notes_added == 0:
                lines.append("- See key items below.")
            # Timeline Highlights
            lines.append("\n## Timeline Highlights")
            if highlights:
                for h in highlights[:8]:
                    ts = _fmt_time(h.get("timestamp"))
                    if ts:
                        lines.append(f"- [{ts}] {h.get('text','')}")
                    else:
                        lines.append(f"- {h.get('text','')}")
            else:
                lines.append("- Key moments are reflected in decisions and actions.")
            # Do NOT include Decisions/Action Items/Key Topics/Risks in summary text
            out["summary"] = "\n".join(lines)
    except Exception:
        pass
    return out
