from __future__ import annotations
from typing import Any, Dict, List, Optional
import json
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import subprocess
import orjson
import json as stdjson
from ..config import settings
from ..utils.logging import logger
import math


def _json_dumps(obj: Any) -> str:
    return orjson.dumps(obj).decode()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def ollama_generate(prompt: str, model: Optional[str] = None, json_response: bool = False, temperature: float = 0.2) -> str:
    model = model or settings.ollama_summarize_model
    url = f"{settings.ollama_base_url}/api/generate"
    headers = {"Content-Type": "application/json"}
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if json_response:
        body["format"] = "json"
    with httpx.Client(timeout=settings.ollama_timeout_seconds) as client:
        try:
            r = client.post(url, content=_json_dumps(body), headers=headers)
            r.raise_for_status()
            data = r.json()
            return data.get("response", "")
        except httpx.HTTPStatusError as e:
            # If model not found locally, try to pull then retry once
            try:
                if e.response is not None and e.response.text and "model" in e.response.text.lower():
                    subprocess.run(["ollama", "pull", model], check=False)
                    r2 = client.post(url, content=_json_dumps(body), headers=headers)
                    r2.raise_for_status()
                    data2 = r2.json()
                    return data2.get("response", "")
            except Exception:
                pass
            raise


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def ollama_embed(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    model = model or settings.ollama_embedding_model
    url = f"{settings.ollama_base_url}/api/embeddings"
    headers = {"Content-Type": "application/json"}
    with httpx.Client(timeout=settings.ollama_timeout_seconds) as client:
        embs: List[List[float]] = []
        for t in texts:
            body = {"model": model, "prompt": t}
            try:
                r = client.post(url, content=_json_dumps(body), headers=headers)
                r.raise_for_status()
                data = r.json()
                vec = data.get("embedding")
                if not vec:
                    raise ValueError("empty embedding")
                embs.append(vec)
            except Exception as e:
                logger.warning(f"Embedding fallback in use: {e}")
                embs.append(_simple_embed(t))
        return embs


def _simple_embed(text: str, dims: int = 256) -> List[float]:
    buckets = [0.0] * dims
    for tok in (text or "").lower().split():
        h = abs(hash(tok))
        idx = h % dims
        buckets[idx] += 1.0
    norm = math.sqrt(sum(x * x for x in buckets)) or 1.0
    return [x / norm for x in buckets]


def _strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("```", 1)[-1]
    if s.endswith("```"):
        s = s.rsplit("```", 1)[0]
    return s.strip()


def coerce_json_response(resp: str) -> Any:
    """Attempt to robustly parse LLM JSON responses that may include prose or code fences."""
    if not resp:
        return {}
    s = _strip_code_fences(resp)
    # Fast path
    try:
        return json.loads(s)
    except Exception:
        pass
    # Extract first top-level JSON object/array
    first_obj = s.find("{")
    first_arr = s.find("[")
    idx = min([i for i in [first_obj, first_arr] if i != -1], default=-1)
    if idx == -1:
        raise ValueError("No JSON object/array found in response")
    # Scan to matching bracket
    open_ch = s[idx]
    close_ch = "}" if open_ch == "{" else "]"
    depth = 0
    end = idx
    for i, ch in enumerate(s[idx:], start=idx):
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    fragment = s[idx:end]
    return json.loads(fragment)


def coerce_json_response(text: str) -> Any:
    """Attempt to coerce LLM output into JSON.
    - Strips code fences
    - Extracts the first JSON object/array substring
    - Tries std json parsing
    Returns parsed object or raises ValueError.
    """
    s = (text or "").strip()
    # strip common markdown fences
    if s.startswith("```"):
        s = s.strip('`')
        # remove leading format hints like json\n
        if s.lower().startswith("json"):  # e.g., json\n{...}
            s = s[4:].lstrip("\n\r ")
    # find first JSON object/array
    start_obj = s.find('{')
    start_arr = s.find('[')
    start = min([p for p in [start_obj, start_arr] if p >= 0], default=-1)
    if start > 0:
        s = s[start:]
    # try to cut trailing junk after the matching last brace/bracket
    last_obj = s.rfind('}')
    last_arr = s.rfind(']')
    last = max(last_obj, last_arr)
    if last >= 0:
        s = s[: last + 1]
    # parse
    return stdjson.loads(s)


def build_summary_prompt(transcript_chunks: List[str]) -> str:
    system = "SYSTEM: You are an AI meeting analyst. Use only the transcript. Do not fabricate details."
    schema_hint = (
        "OUTPUT: STRICT JSON with fields: summary (string), key_topics (string[]), "
        "decisions ({text:string, owner?:string|null, timestamp?:number|null}[]), action_items ({text:string, owner?:string|null, due_date?:string|null, timestamp?:number|null}[]), "
        "risks (string[]), sentiment_overview ({label:'positive'|'neutral'|'negative', score:-1..1, rationale:string})."
    )
    guidance = (
        "SUMMARY FORMAT: Provide a well-structured Markdown report (not a one-liner) with sections: \n"
        "  # Meeting Summary\n  ## Executive Summary (5-10 bullets)\n  ## Detailed Notes (3-6 short paragraphs)\n  ## Timeline Highlights (bullet list with mm:ss timestamps if available).\n"
        "Do NOT include Decisions, Action Items, Key Topics, or Risks in the 'summary' text — those are separate arrays.\n"
        "LENGTH: Aim for 300-800 words; include only facts present in the transcript.\n"
        "TIMESTAMPS: If transcript shows [12.3-18.9], use 12.3 as seconds. If unknown, set timestamp to null."
    )
    joined = "\n\n".join(transcript_chunks)
    return f"{system}\n{schema_hint}\n{guidance}\n\nTRANSCRIPT:\n{joined}\n\nJSON:"


def build_topics_prompt(transcript_chunks: List[str]) -> str:
    return (
        "Identify 3-8 concise, high-signal topic tags for this meeting. Rank by prominence. "
        "Return STRICT JSON as an array of {label:string, confidence:number 0..1}.\nTRANSCRIPT:\n"
        + "\n\n".join(transcript_chunks)
        + "\n\nJSON:"
    )


def build_sentiment_prompt(transcript_chunks: List[str]) -> str:
    return (
        "Assess overall sentiment and tone (e.g., positive, neutral, negative) considering collaboration, stress, alignment, and conflict.\n"
        "Return STRICT JSON: { label:'positive'|'neutral'|'negative', score:-1..1, rationale:string }.\nTRANSCRIPT:\n"
        + "\n\n".join(transcript_chunks)
        + "\n\nJSON:"
    )
