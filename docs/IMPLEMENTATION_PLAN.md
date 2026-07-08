# Implementation Plan

Work through phases in order. Each phase ends with something runnable and verifiable.
Don't jump ahead — later phases depend on state and code produced by earlier ones.

---

## Phase 1 — Foundation & Platform Connection

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

## Phase 2 — Run Capture

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

## Phase 3 — Script Generation & Human Review

**Goal:** The run is turned into a reviewable, timed scene list before any rendering starts.

### `generate_script` node
- [ ] Build a prompt combining `agent_spec` + `run_transcript`
- [ ] Require structured JSON output: `[{"start", "end", "on_screen", "narration"}, ...]`
- [ ] Parse safely; rely on LangGraph's `retry_policy(max_attempts=3)` for malformed responses
- [ ] Sanity-check that scene timings roughly span the recording length
- [ ] Return `scenes`, `script_status: "pending_review"`

### `review_script` node (human-in-the-loop)
- [ ] `interrupt()` with `scenes` + `custom_instructions` so a person can inspect/edit
- [ ] Handle `"action": "edit"` — return updated scenes, keep status `"pending_review"` (loops back for re-approval)
- [ ] Handle `"action": "approve"` — return `script_status: "approved"`
- [ ] Support a `skip_review` flag (env var or request field) to auto-approve for standard runs
- [ ] Add a timeout so the graph doesn't hang indefinitely

**Done when:** The three-node graph produces an approved scene list that maps correctly onto the recording timeline.

---

## Phase 4 — Video Assembly

**Goal:** Two output videos — one narrated, one silent — are produced from the approved script.

### Narrated cut
- [ ] `synthesize_audio`: TTS each scene's `narration` text into one concatenated audio track
  - Use `tts_client.synthesize()` backed by `config.GEMINI_API_KEY` (Gemini TTS)
  - Return `narration_audio_path`
- [ ] `assemble_full`: FFmpeg mux `raw_video_path` + `narration_audio_path`
  - Return `narrated_video_path`
  - Verify with ffprobe: audio track present, resolution 1920×1080

### Silent cut
- [ ] `assemble_silent`: produce a condensed cut driven by scene timings
  - Trim to scene boundaries (not fixed rules)
  - Burn in each scene's `on_screen` text as captions
  - Strip audio track
  - Return `silent_video_path`
  - Verify with ffprobe: no audio track, shorter duration than narrated cut

**Done when:** Both `output/narrated_<agent>.mp4` and `output/silent_<agent>.mp4` are playable and pass ffprobe checks.

---

## Phase 5 — Integration, Hardening & Deployment

**Goal:** The full pipeline is wired end-to-end, hardened against real failures, and reachable via API.

### Wire it together
- [ ] `graph.py`: confirm all nodes are connected per the pipeline order in CLAUDE.md
- [ ] `finalize` node: ffprobe both outputs (resolution, duration, audio presence), move to `OUTPUT_DIR`
- [ ] `routes.py` `POST /videos`: invoke the graph with `{agent_id, project_id, custom_instructions}`, handle the `review_script` interrupt cleanly
- [ ] End-to-end run against `defect-triaging-crewai`; compare outputs against reference videos

### Hardening
- [ ] Per-stage timeouts + one retry on `capture_run`
- [ ] Clean up `output/raw/` captures after assembly to save disk
- [ ] Structured logging (structlog) per stage — log stage entry/exit and key state fields
- [ ] Unit tests with hub + TTS mocked (see `tests/`): at minimum cover `select_agent`, `generate_script`, `finalize`

### Deployment check
- [ ] `uvicorn app.api.routes:app --reload` starts cleanly with a valid `.env`
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] Dockerfile builds and `docker compose up` launches the service

**Done when:** `POST /videos` against `defect-triaging-crewai` produces two files in `output/` in under 15 minutes, end-to-end, unattended.

---

## Notes

- First test target: `defect-triaging-crewai` (reference videos already exist for comparison).
- Out of scope for v1: multi-language narration, thumbnails/intro branding, publishing to a hosting site.
- Personal Gemini key is fine for prototyping; move to an org key before wider rollout (change is one line in `config.py`).
- Gemini TTS is used for voice-over — no separate TTS provider or API key needed.
