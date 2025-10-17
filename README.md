# 🧠 AI Meeting Intelligence Platform
### Transform Meeting Recordings into Actionable Insights

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green?logo=fastapi)
![React](https://img.shields.io/badge/React-Frontend-blue?logo=react)
![Ollama](https://img.shields.io/badge/Ollama-LLM-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)


## 📖 Overview

**AI Meeting Intelligence Platform** is a full‑stack system that converts meeting recordings into structured, searchable, and insightful summaries.  
It combines **automatic transcription**, **semantic analysis**, **sentiment detection**, and **AI summarization** to give teams an instant overview of discussions, decisions, and action items.

Built with **FastAPI**, **React**, and **Ollama**, it integrates **whisper.cpp** (or **faster‑whisper**) for transcription and **ChromaDB** for vector‑based semantic search — providing an efficient, privacy‑preserving, and self‑contained solution for meeting intelligence.



## ✨ Key Features

- **Accurate Transcription** (whisper.cpp / faster‑whisper)
- **Topic Extraction & Summaries** (LLM via Ollama)
- **Sentiment Insights** per segment
- **Semantic Search** over transcripts (ChromaDB)
- **Action Items & Decisions** extraction
- **Fully Local / Offline‑friendly** (no external data sharing)
- **Simple Web UI** for upload, processing, and review



## 🏗️ Architecture Overview

```
Frontend (React + Tailwind + Vite)
         │
         ▼
Backend (FastAPI + SQLite + ChromaDB)
         │
         ├── Transcription (whisper.cpp / faster-whisper)
         ├── Embeddings (Ollama)
         ├── Semantic Indexing (Chroma)
         └── LLM Summarization + Sentiment + Topics
```



## 📁 Project Structure

| Directory | Description |
|---|---|
| **backend/** | FastAPI backend with SQLite DB, ChromaDB, whisper.cpp, and Ollama integrations. |
| **frontend/** | React + Tailwind + Vite interface for uploading meetings and visualizing insights. |
| **docs/** | Architecture and API documentation. |
| **docs/tech-writeup/** | Technical write‑ups: architecture, pipeline, and challenges (README.md, api.md, architecture.md). |



## 🚀 Quickstart

### 1️⃣ Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

- Update `.env` with:
  - `WHISPER_BIN` → path to whisper.cpp binary  
  - `WHISPER_MODEL` → path to your model file
- Start **Ollama** and pull required models:
  ```bash
  ollama pull llama3
  ollama pull nomic-embed-text
  ```
- Run the backend:
  ```bash
  uvicorn app.main:app --reload
  ```

### 2️⃣ Frontend Setup

```bash
cd frontend
npm install
npm run dev
```
Open: **http://localhost:5173**

### 3️⃣ Use the Platform

1. Create a meeting and upload audio/video.  
2. Click **Process** to run transcription → embeddings → indexing → LLM insights.  
3. Explore: **summary**, **topics**, **sentiments**, **transcript**, and **search highlights**.



## ⚙️ Configuration Details

### 🎙️ Transcription Engines

| Engine | Description | Setup |
|---|---|---|
| **whisper.cpp** | Local, fast transcription with low resource usage. | Configure `WHISPER_BIN` and `WHISPER_MODEL` in `.env`. |
| **faster‑whisper** | Python engine; supports optional diarization. | Set `TRANSCRIPTION_ENGINE=faster_whisper`; diarization via pyannote requires `HF_TOKEN`. |

### 💾 Storage Layout

- **ChromaDB**: `backend/data/chroma`  
- **SQLite**: `backend/data/app.db`  
- **Uploads**: `backend/data/uploads`



## 📚 Documentation

- `docs/tech-writeup/README.md` — Technical overview (architecture, pipeline, challenges)  
- `docs/tech-writeup/api.md` — API endpoints and usage  
- `docs/tech-writeup/architecture.md` — System design details & diagrams



## 🧩 Deliverables

- ✅ Working backend & frontend codebase
- ✅ API, docs, and setup instructions
- ✅ Post‑meeting pipeline (transcription → insights → search)




## 🪪 License

Released under the **MIT License**. See `LICENSE` for details.

