# API Documentation

Base URL: `http://localhost:8000`

OpenAPI/Swagger UI: `GET /docs`
ReDoc: `GET /redoc`
Health: `GET /healthz` → `{ "status": "ok" }`

## Meetings

### Create Meeting
- POST `/api/meetings`
- Body (JSON):
  - `title` string (required)
- 201/200 → Meeting

Example
```
curl -X POST http://localhost:8000/api/meetings \
  -H 'Content-Type: application/json' \
  -d '{"title":"Sprint Review – Oct 15"}'
```

Response (Meeting)
```
{
  "id": "mtg_...",
  "title": "Sprint Review – Oct 15",
  "created_at": "2025-10-16T19:40:27.123Z",
  "duration_seconds": 0,
  "language": null,
  "status": "created",
  "files": []
}
```

### List Meetings
- GET `/api/meetings`
- 200 → `[Meeting]`

### Get Meeting Detail
- GET `/api/meetings/{meeting_id}`
- 200 → Meeting with relationships (segments, summary, decisions, action_items, topics, sentiments)

### Upload Media
- POST `/api/meetings/{meeting_id}/upload`
- Query:
  - `auto` boolean (default true) — automatically start background processing
- Body: `multipart/form-data` with field `upload` (file)
- 200 → Meeting (status becomes `uploaded`)

Example
```
curl -X POST "http://localhost:8000/api/meetings/mtg_123/upload?auto=true" \
  -F upload=@/path/to/recording.mp4
```

### Start Processing (Background)
- POST `/api/meetings/{meeting_id}/process`
- 200 → Job

Example
```
curl -X POST http://localhost:8000/api/meetings/mtg_123/process
```

### Reprocess All Meetings (Background)
- POST `/api/meetings/reprocess_all`
- 200 → `{ count: number, jobs: string[] }`

## Jobs

### Get Job Status
- GET `/api/jobs/{job_id}`
- 200 →
```
{
  "id": "job_...",
  "meeting_id": "mtg_...",
  "kind": "process",
  "status": "queued|running|succeeded|failed",
  "error": null,
  "created_at": "...",
  "started_at": "...",
  "finished_at": "...",
  "progress": 0-100,
  "message": "string",
  "elapsed_seconds": number
}
```

### List Jobs for a Meeting
- GET `/api/jobs/meeting/{meeting_id}`
- 200 → minimal job objects (latest first)

## Search

### Semantic Search Across All Meetings
- POST `/api/search`
- Body (JSON):
  - `query` string
  - `top_k` number (default 10)
- 200 → `[SearchHit]`

Example
```
curl -X POST http://localhost:8000/api/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"timeline risks", "top_k": 8}'
```

Response (SearchHit)
```
{
  "meeting_id": "mtg_...",
  "segment_id": "seg_...",
  "score": 0.23,
  "start": 120.5,
  "end": 135.2,
  "text": "...segment text...",
  "title": "Sprint Review – Oct 15"
}
```

## Files (Dev/Testing Only)

### Download Local File (Caution)
- GET `/api/files/download?path=/absolute/or/workspace/path`
- 200 → file stream
- Note: Path access is not restricted; do not expose this endpoint in production.

## Schemas (Selected)

Meeting
- `id` string
- `title` string
- `created_at` datetime
- `duration_seconds` int
- `language` string|null
- `status` string
- `error` string|null
- `files` File[]
- Relations on detail: `segments`, `summary`, `decisions`, `action_items`, `topics`, `sentiments`

Summary
- `id` string
- `summary` string (LLM markdown narrative)
- `key_topics` JSON string (array)
- `decisions` JSON string (array of objects)
- `action_items` JSON string (array of objects)
- `risks` JSON string (array)
- `sentiment_overview` JSON string (object with `label`, `score`, `vibe`, `rationale`, `highlights[]`)

SearchHit
- `meeting_id` string
- `segment_id` string
- `score` number
- `start` number (seconds)
- `end` number (seconds)
- `text` string
- `title` string

Job
- `id` string
- `meeting_id` string|null
- `kind` string
- `status` string
- `error` string|null
- `created_at` datetime
- `started_at` datetime|null
- `finished_at` datetime|null
- `progress` int (0..100)
- `message` string|null
- `elapsed_seconds` number

## Status Codes
- 200 OK / 201 Created — success
- 400 Bad Request — invalid inputs (e.g., unsupported file type, size limit)
- 404 Not Found — missing meeting/file/job
- 500 Internal Server Error — unexpected failures

## Notes
- Upload size limit governed by `max_upload_mb` in backend settings.
- Supported media extensions: mp3, mp4, wav, m4a, aac, flac, webm, ogg.
- OpenAPI interactive docs at `/docs` reflect the latest server state.
