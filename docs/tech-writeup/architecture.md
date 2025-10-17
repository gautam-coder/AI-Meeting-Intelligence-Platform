Architecture & AI Pipeline

Overview
- Frontend: React + Tailwind, Vite dev server
- Backend: FastAPI, SQLAlchemy (SQLite), BackgroundTasks
- AI: whisper.cpp (transcription + diarization), Ollama (LLM + embeddings), ChromaDB (vector search)

Data Flow
- Upload audio/video -> `/api/meetings/{id}/upload` stores file under `backend/data/uploads`
- `/process` job:
  1) Transcription (engine selectable):
     - whisper.cpp CLI -> JSON parsed into `segments`
     - faster-whisper (Python) -> segments via CTranslate2; optional pyannote diarization
  2) Index segments in Chroma with Ollama embeddings
  3) Sentiment (heuristic placeholder per segment)
  4) Topics (LLM)
  5) Summary (LLM JSON with topics, decisions, action items)
  6) Store derived insights in SQLite

Storage
- SQLite DB: `backend/data/app.db`
- Uploads: `backend/data/uploads`
- Chroma: `backend/data/chroma`

LLM/Embedding Models
- Summarization: `OLLAMA_SUMMARY_MODEL` (e.g., `llama3`)
- Embeddings: `OLLAMA_EMBED_MODEL` (e.g., `nomic-embed-text`)

Edge Cases & Handling
- Large uploads: `max_upload_mb` limit, streamed to temp then moved; deduplicate filenames
- Unsupported types: extension allowlist
- Corrupted media: whisper.cpp error surfaces to job and meeting status `error`
- No speech / silence: if no segments -> fail early with clear error
- Long meetings: transcript chunking for LLM; index all segments regardless
- Diarization quality: optional tinydiarize (whisper.cpp) or pyannote (requires HF token); store `speaker` if present; UI degrades gracefully
- Multilingual / code-switching: `whisper_language` None to auto-detect; store language per segment
- LLM JSON robustness: strict JSON mode; fallback to plain text summary if parsing fails
- Embedding availability: uses Ollama local embeddings to avoid network; retries with backoff
- Chroma errors: idempotent `get_or_create_collection`; add in batches
- Timeouts: httpx timeout for Ollama; tenacity retries
- Concurrency: background tasks per processing job; DB transactions per step
- Idempotency: re-running process appends duplicate embeddings; future improvement: upserts by `meeting_id`
- Privacy: no network calls beyond local Ollama and local file system; caution with `/api/files/download`

Local Dev Setup
- Install whisper.cpp and download model (`ggml-base.en.bin` or better) OR set `TRANSCRIPTION_ENGINE=faster_whisper` and prepare models via setup endpoints
- Install and run Ollama, pull models: `ollama pull llama3`, `ollama pull nomic-embed-text`
- Start FastAPI: `uvicorn app.main:app --reload`
- Start frontend: `npm run dev` in `frontend`

Future Enhancements
- Improve sentiment with LLM per chunk and smoothing
- Speaker diarization with better models; speaker naming via heuristics
- Job queue with a proper worker (e.g., RQ/Celery) and progress events via websockets
- Authentication and fine-grained access control
- Export to PDF/Markdown, shareable public links
