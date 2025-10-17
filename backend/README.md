Backend (FastAPI) for AI Meeting Intelligence Platform

Prereqs
- Python 3.11+
- Ollama running locally (default: http://localhost:11434)
- whisper.cpp built locally; set path in `app/config.py`
- SQLite (bundled with Python)
 - Optional: pyannote.audio for high-accuracy multi-speaker diarization (requires HF_TOKEN)

Quickstart
1) Create and activate venv
   - python3 -m venv .venv && source .venv/bin/activate
2) Install deps
   - pip install -r requirements.txt
3) Configure environment
   - Copy `.env.example` to `.env` and adjust paths
   - To enable accurate multi-speaker diarization, set `DIARIZATION_ENABLED=1` and provide a valid `HF_TOKEN` (Hugging Face access token)
4) Start API
   - uvicorn app.main:app --reload

Notes
- Uploads and artifacts are stored under `backend/data`
- ChromaDB persistence directory lives at `backend/data/chroma`
- For long jobs, processing runs as background tasks recorded in DB

Multi-Speaker Diarization (Recommended)
- Set `DIARIZATION_ENABLED=1` in `.env` and provide `HF_TOKEN` to use `pyannote/speaker-diarization-3.1`.
- This significantly improves speaker attribution beyond whisper.cpp's tinydiarize.
- Without pyannote, the system falls back to heuristics and any labels provided by the transcriber, then normalizes to `Speaker A/B/C...`.
