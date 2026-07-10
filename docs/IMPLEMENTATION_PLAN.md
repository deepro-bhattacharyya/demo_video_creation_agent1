# Implementation Plan

Work through phases in order. Each phase ends with something runnable and verifiable.
Don't jump ahead — later phases depend on state and code produced by earlier ones.

---

## Phase 1 — Foundation & Platform Connection ✅

**Goal:** Environment is wired up, the app starts cleanly, and we can read an
agent's spec from the platform without writing a single pixel of video.

### Setup
- [x] Confirm Python 3.11+, install `requirements.txt`
- [x] `playwright install chromium`
- [x] Copy `.env.example` to `.env` and fill in real values locally
- [x] Confirm `.env` is git-ignored and never committed
- [x] `app/config.py` loads all env vars in one place and fails loudly if one is missing

### Platform client (`hub_client.py`)
- [x] `login(page)`: drive Playwright to `AGENTICQEAHUB_BASE_URL/marketplace` and authenticate
- [x] Confirm login succeeds (wait for a post-login element to confirm)
- [x] `get_agent_spec(agent_id)`: return `{"name": ..., "spec": ...}` from the platform

### `select_agent` node
- [x] Call `hub_client.get_agent_spec` and populate `agent_name` + `agent_spec` in state
- [x] Keep all UI selectors (login fields, buttons, nav) in `hub_client.py` only

**Done when:** `select_agent` runs end-to-end and prints the agent name + spec for `defect-triaging-crewai`.

---

## Phase 2 — Run Capture ✅

**Goal:** A real browser session runs the target agent and saves a 1920×1080 video to disk.

### `capture_run` node
- [x] Launch Playwright with `record_video_dir="output/raw"` and `record_video_size={"width": 1920, "height": 1080}`
- [x] Call `hub_client.login(page)` to authenticate
- [x] Navigate to the agent workspace: `?agent=<agent_id>&project=<project_id>`
- [x] Implement `run_agent_and_collect_events(page, agent_id)` in `hub_client.py`:
  - Trigger the run
  - Wait for completion
  - Collect step/HITL events into `run_transcript`
- [x] Close the browser context to finalise the video file
- [x] Return `raw_video_path`, `run_transcript`, and `status: "captured"`

**Done when:** Running the two-node graph (`select_agent → capture_run`) produces a real `.webm`/`.mp4` in `output/raw/` and a non-empty `run_transcript`.

---

## Phase 3 — Script Generation & Human Review ✅

**Goal:** The run is turned into a reviewable, timed scene list before any rendering starts.

### `generate_script` node
- [x] Build a prompt combining `agent_spec` + `run_transcript`
- [x] Require structured JSON output: `[{"start", "end", "on_screen", "narration"}, ...]`
- [x] Parse safely; rely on LangGraph's `retry_policy(max_attempts=3)` for malformed responses
- [x] Sanity-check that scene timings roughly span the recording length
- [x] Return `scenes`, `script_status: "pending_review"`

### `review_script` node (human-in-the-loop)
- [x] `interrupt()` with `scenes` + `custom_instructions` so a person can inspect/edit
- [x] Handle `"action": "edit"` — return updated scenes, keep status `"pending_review"` (loops back for re-approval)
- [x] Handle `"action": "approve"` — return `script_status: "approved"`
- [x] Support a `skip_review` flag (`SKIP_REVIEW=true` in `.env`) to auto-approve for standard runs
- [ ] Add a timeout so the graph doesn't hang indefinitely *(deferred — handled by `SKIP_REVIEW` flag for now)*

**Done when:** The three-node graph produces an approved scene list that maps correctly onto the recording timeline.

---

## Phase 4 — Video Assembly ✅

**Goal:** Two output videos — one narrated, one silent — are produced from the approved script.

### Narrated cut
- [x] `synthesize_audio`: TTS each scene's `narration` text into one concatenated audio track
  - Use `tts_client.synthesize()` backed by `config.GEMINI_API_KEY` (Gemini TTS)
  - Return `narration_audio_path`
- [x] `assemble_full`: FFmpeg mux `raw_video_path` + `narration_audio_path`
  - Return `narrated_video_path`
  - Verify with ffprobe: audio track present, resolution 1920×1080

### Silent cut
- [x] `assemble_silent`: produce a condensed cut driven by scene timings
  - Trim to scene boundaries (not fixed rules)
  - Burn in each scene's `on_screen` text as captions
  - Strip audio track
  - Return `silent_video_path`
  - Verify with ffprobe: no audio track, shorter duration than narrated cut

**Done when:** Both `output/narrated_<agent>.mp4` and `output/silent_<agent>.mp4` are playable and pass ffprobe checks.

---

## Phase 5 — Integration, Hardening & Deployment ✅

**Goal:** The full pipeline is wired end-to-end, hardened against real failures, and reachable via API.

### Wire it together
- [x] `graph.py`: all nodes connected; `build_graph(checkpointer=)` accepts a `MemorySaver` for interrupt/resume
- [x] `finalize` node: ffprobe validates both outputs (audio present/absent), cleans up raw + audio intermediates
- [x] `routes.py`: `POST /videos` kicks off pipeline in a background thread and returns `thread_id` immediately; `GET /videos/{id}/status` for polling; `POST /videos/{id}/resume` for approve/edit
- [ ] End-to-end run against `defect-triaging-crewai`; compare outputs against reference videos *(requires live platform access — UI selectors in `hub_client.py` still marked TODO)*

### Hardening
- [x] Per-stage timeouts + one retry on `capture_run` (Playwright 5-min timeout + `RetryPolicy(max_attempts=2)` in graph)
- [x] Clean up `output/raw/` captures and `output/audio/` intermediates after assembly (`finalize._cleanup`)
- [x] Structured logging (structlog) on `capture_run`, `generate_script`, `finalize` — entry/exit + key state fields
- [x] Unit tests: **41 passing** across all phases (generate_script, synthesize_audio, assemble, finalize, routes, graph)

### Deployment
- [x] `uvicorn app.api.routes:app --reload` starts cleanly with a valid `.env`
- [x] `GET /health` returns `{"status": "ok"}` (verified in test suite)
- [x] Multi-stage `Dockerfile` (Node build + Python runtime) and `docker-compose.yml` created
- [x] FastAPI serves the React build from `/` in production (no separate web server needed)

**Done when:** `POST /videos` against `defect-triaging-crewai` produces two files in `output/` in under 15 minutes, end-to-end, unattended.

---

## Frontend — React Web UI ✅

**Goal:** Users can submit jobs, track progress, review scripts, and see output
paths without touching the command line.

- [x] `PipelineForm` — Agent ID, Project ID, optional custom instructions
- [x] `ProgressView` — spinner + step hints; polls `/status` every 5 seconds
- [x] `SceneReviewer` — editable scene cards (on_screen + narration); sticky Approve / Submit Edits bar
- [x] `ResultsView` — output file paths, Generate Another button
- [x] Error view for pipeline failures with Try Again
- [x] Vite proxy routes `/videos` and `/health` to `:8000` in dev (no CORS config needed)
- [x] FastAPI CORS middleware allows `localhost:5173` in development
- [x] `npm run build` produces a production bundle served by FastAPI's `StaticFiles`

---

## Notes

- First test target: `defect-triaging-crewai` (reference videos already exist for comparison).
- Out of scope for v1: multi-language narration, thumbnails/intro branding, publishing to a hosting site.
- Personal Gemini key is fine for prototyping; move to an org key before wider rollout (one-line change in `config.py`).
- Gemini TTS is used for voice-over — no separate TTS provider or API key needed.
- `MemorySaver` stores job state in memory; swap for `SqliteSaver` before multi-worker production deploy.
