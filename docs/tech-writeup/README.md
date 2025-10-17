# Technical Write‑Up

This document summarizes key architecture decisions, the end‑to‑end AI pipeline, and notable challenges with their solutions for the AI Meeting Intelligence Platform.

## Architecture Decisions

- Frontend: React + Vite + Tailwind
  - Reason: Fast dev cycle, simple SSR‑free app, Tailwind for consistent design system.
  - Pages: Dashboard, Upload, Meeting Detail. Shared UI primitives in `frontend/src/components/ui.tsx`.

- Backend: FastAPI + SQLAlchemy (SQLite)
  - Reason: Lightweight, typed Python APIs, easy async/background jobs via FastAPI BackgroundTasks.
  - Layout: `backend/app` modules by concern (routes, services, models, utils).
  - Persistence: SQLite for structured entities (Meetings, Files, Segments, Summary, Topics, Decisions, Action Items, Sentiments, Jobs).

- Search: ChromaDB + Ollama Embeddings
  - Reason: Local vector DB with persistent storage; models run via Ollama (no external dependency).
  - Fallback: Deterministic local embedding used if Ollama embeddings are unavailable to keep search functional.

- Transcription Engines
  - Default: `faster-whisper` (high accuracy, good CPU performance; optional GPU when available).
  - Optional: `whisper.cpp` with auto‑setup helpers (download/build), tunable diarization flags.
  - Diarization: Optional pyannote; heuristic speaker labeling used when diarization is not available.

- LLM Runtime: Ollama
  - Reason: Local LLMs for privacy and offline operation.
  - Models: `llama3.2` for summary/extraction/sentiment; `nomic-embed-text` (or similar) for embeddings.
  - Robust JSON: A custom parser tolerates code fences/extra text and extracts strict JSON payloads.

- Background Jobs & Resilience
  - Jobs table tracks status and progress milestones; UI polls `/api/jobs/{id}` for progress + elapsed.
  - Startup backfill reprocesses historical meetings missing insights.
  - Auto‑process on upload for a smooth flow.

## AI Pipeline Implementation (End‑to‑End)

1) Ingestion
   - Endpoint: `POST /api/meetings/{id}/upload` saves media under `backend/data/uploads` and enqueues processing (auto by default).
   - Files: `app/routes/meetings.py`, `app/services/storage.py`.

2) Transcription (+ optional diarization)
   - Engine: `faster-whisper` by default; `whisper.cpp` optional.
   - Diarization: pyannote (if enabled) or heuristic speaker labeling with readable labels (Speaker A/B/…).
   - Output: Segments with `start`, `end`, `speaker`, `text`; stored in DB.
   - Files: `services/transcription.py`, `services/transcription_fw.py`, `services/fallback.py`.

3) Chunking for LLM
   - Transcript is chunked with timestamped, speaker‑prefixed lines, respecting token limits.
   - File: `services/pipeline.py::chunk_transcript`.

4) Summarization (LLM Map‑Reduce)
   - Per‑chunk extraction (bullets/notes), then merge pass produces a cohesive report:
     - `summary` (narrative markdown), `key_topics`, `decisions`, `action_items`, `risks`.
   - File: `services/summarizer.py`.

5) Extraction Pass (LLM) for Actions / Decisions / Topics
   - Dedicated prompt to separate actionable tasks and explicit decisions, plus focused topic tags.
   - Refinement pass (LLM) improves specificity, dedupes, and carries owners/timestamps.
   - Files: `services/extractors.py`, `services/refiner.py`.

6) Sentiment (LLM) with Vibe + Highlights
   - LLM returns `{ label, score, vibe, rationale, highlights[] }` with timestamped contentious/positive moments.
   - If LLM response is missing critical fields, a fallback computes aggregate + derived highlights.
   - Files: `services/sentiment_llm.py`, `services/sentiment.py`.

7) Persistence & Indexing
   - Summary (one per meeting) is upserted with all JSON subfields; decisions and action items are also stored in normalized tables for future filtering/analytics.
   - ChromaDB indexes per‑segment text for semantic search; metadata carries meeting/segment/time.
   - Files: `services/pipeline.py`, `services/embeddings.py`.

8) Frontend UX
   - Dashboard: global search, recent meetings.
   - Meeting Detail: LLM summary, topic chips, sentiment vibe + highlights, decision/action lists with owners and timestamps, full transcript.
   - Upload: guided create/upload/process with live progress + elapsed.
   - Files: `frontend/src/pages/*`, `frontend/src/components/ui.tsx`.

## Challenges and Solutions

- Long Context & Token Limits
  - Challenge: Meetings can be long; naive prompts fail.
  - Solution: Chunked map‑reduce summarization; targeted extraction passes (decisions/actions/topics); controlled chunk size.

- JSON Robustness from LLMs
  - Challenge: Models sometimes wrap JSON in prose/code fences or return partial structures.
  - Solution: `coerce_json_response` extracts valid JSON from noisy responses; strict schemas in prompts; secondary normalization.

- Duplicate / Vague Items in Actions/Decisions
  - Challenge: Overlap with summary or repeated phrasing.
  - Solution: LLM refinement pass + programmatic merge/dedupe by normalized text; keep earliest timestamps; enforce concise/imperative phrasing.

- Speaker Identification
  - Challenge: Diarization may be unavailable or heavy.
  - Solution: Optional pyannote; otherwise a readable heuristic assigns A/B turns so transcripts remain navigable.

- Local‑Only Operation (No External Cloud)
  - Challenge: Offline environments; missing models.
  - Solution: Ollama and local embeddings; optional auto‑pull; fallback local embeddings to keep search alive.

- Operational UX
  - Challenge: Users need to know status for long jobs.
  - Solution: Background tasks with job progress milestones, frontend polling, and an improved progress UI.

- Backfill / Dynamic Reprocessing
  - Challenge: Existing meetings need new insights as the system evolves.
  - Solution: Startup backfill worker; `/api/meetings/reprocess_all` bulk refresh.

