# API Reference

Base URL (development): `http://localhost:8000`

All request and response bodies are JSON. All endpoints except `GET /health` are
covered by the React frontend — this reference is for direct API access, testing,
or building integrations.

---

## Endpoints

### `POST /videos`

Start a new pipeline job in the background. Returns immediately with a `thread_id`.
Poll `GET /videos/{thread_id}/status` to track progress.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_type` | string | No | `"hub"` (default) or `"standalone"` |
| `agent_name` | string | Hub only | Display name of the agent, e.g. `"Defect Triage (CrewAI)"` |
| `project_name` | string | Hub only | Display name of the project, e.g. `"Dev test project"` |
| `agent_folder` | string | Standalone only | Absolute path to the local agent folder |
| `custom_instructions` | string | No | Free-text instructions for the narration script (tone, focus, naming) |

**Hub mode example**

```bash
curl -X POST http://localhost:8000/videos \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "hub",
    "agent_name": "Defect Triage (CrewAI)",
    "project_name": "Dev test project",
    "custom_instructions": "Focus on the Neo4j lookup step. Use formal tone."
  }'
```

**Standalone mode example**

```bash
curl -X POST http://localhost:8000/videos \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "standalone",
    "agent_folder": "C:/Projects/my-agent",
    "custom_instructions": "Keep narration under 2 minutes."
  }'
```

**Response `200 OK`**

```json
{
  "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "running"
}
```

**Error responses**

| Code | When |
|------|------|
| `422` | `source_type` is `"standalone"` but `agent_folder` is missing or empty |

---

### `GET /videos/{thread_id}/status`

Poll the current status of a pipeline job.

```bash
curl http://localhost:8000/videos/3fa85f64-5717-4562-b3fc-2c963f66afa6/status
```

**Response — running**

```json
{
  "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "running"
}
```

**Response — awaiting review** (pipeline paused, script is ready to review)

```json
{
  "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "awaiting_review",
  "scenes": [
    {
      "start": 0,
      "end": 12,
      "on_screen": "Agent receives defect ID",
      "narration": "The agent begins by accepting defect ID 80 as input and initiating the Neo4j lookup workflow."
    },
    {
      "start": 12,
      "end": 35,
      "on_screen": "Neo4j graph query runs",
      "narration": "A Cypher query is executed against the knowledge graph to retrieve related defects, owners, and historical resolution patterns."
    }
  ],
  "custom_instructions": "Focus on the Neo4j lookup step."
}
```

**Response — done**

```json
{
  "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "done",
  "narrated_video_path": "output/narrated_defect_triage__crewai_.mp4",
  "silent_video_path": "output/silent_defect_triage__crewai_.mp4"
}
```

**Response — error**

```json
{
  "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "error",
  "error": "Agent run did not complete within 600s. Check the platform for errors."
}
```

**Error responses**

| Code | When |
|------|------|
| `404` | `thread_id` not found |

---

### `POST /videos/{thread_id}/resume`

Resume a job that is paused at the script-review step.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | `"approve"` to use the script as-is, or `"edit"` to submit changes |
| `scenes` | array | Only when `action = "edit"` | Full updated scene array (same structure as returned by `/status`) |

**Approve without changes**

```bash
curl -X POST http://localhost:8000/videos/3fa85f64-.../resume \
  -H "Content-Type: application/json" \
  -d '{"action": "approve"}'
```

**Submit edited scenes**

```bash
curl -X POST http://localhost:8000/videos/3fa85f64-.../resume \
  -H "Content-Type: application/json" \
  -d '{
    "action": "edit",
    "scenes": [
      {
        "start": 0,
        "end": 12,
        "on_screen": "Agent receives defect ID",
        "narration": "The Defect Triaging agent accepts defect ID 80 and begins a structured Neo4j knowledge graph lookup."
      }
    ]
  }'
```

**Response `200 OK`**

```json
{
  "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "running"
}
```

**Error responses**

| Code | When |
|------|------|
| `404` | `thread_id` not found |
| `400` | Job is not in `awaiting_review` state |

---

### `GET /health`

Health check endpoint. Returns `200` if the server is running.

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok"}
```

---

## Scene object schema

Used in `GET /status` (response) and `POST /resume` (request when editing).

```json
{
  "start": 0,
  "end": 12,
  "on_screen": "Short caption (max 10 words)",
  "narration": "One to three sentences read aloud by the narrator."
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `start` | number | ≥ 0; first scene must be 0 |
| `end` | number | > `start` |
| `on_screen` | string | Max ~10 words (must be readable in under 3 seconds) |
| `narration` | string | 1–3 sentences; factual description of what the agent does |

Scenes must be in chronological order with no gaps and no overlaps.

---

## Polling recommended interval

Poll `GET /status` every **5 seconds** while `status == "running"`. The pipeline
typically takes 5–15 minutes end-to-end. Polling faster does not speed anything up.
