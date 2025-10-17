AI Meeting Intelligence Platform: Post-Meeting Analysis

What’s inside
- backend/ (FastAPI + SQLite + ChromaDB + Ollama + whisper.cpp integration)
- frontend/ (React + Tailwind + Vite)
- docs/ (API and architecture)
  - docs/tech-writeup/README.md (Technical write‑up: architecture, pipeline, challenges)

Quickstart
1) Backend
   - cd backend
   - python3 -m venv .venv && source .venv/bin/activate
   - pip install -r requirements.txt
   - cp .env.example .env
   - Edit .env with paths to whisper.cpp binary and model
   - Ensure Ollama is running; pull models: `ollama pull llama3` and `ollama pull nomic-embed-text`
   - uvicorn app.main:app --reload

2) Frontend
   - cd frontend
   - npm install
   - npm run dev

3) Use
   - Open http://localhost:5173
   - Create meeting, upload audio/video, start processing
   - View summary, topics, sentiments, transcript, and search highlights

Notes
- Transcription engine is selectable:
  - whisper.cpp: compile or auto-build via Setup; configure `WHISPER_BIN`/`WHISPER_MODEL`
  - faster-whisper: set `TRANSCRIPTION_ENGINE=faster_whisper`; optional diarization via pyannote (requires `HF_TOKEN`)
- ChromaDB persists under backend/data/chroma
- SQLite DB at backend/data/app.db

Deliverables
- Working codebase with API, docs, and setup instructions
- See docs/tech-writeup/api.md and docs/tech-writeup/architecture.md
- Brief technical write‑up: docs/tech-writeup/README.md
