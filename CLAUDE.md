# CLAUDE.md — Project Context for Claude Code

> Read this first. It is the source of truth for how to build this project.
> The full design rationale lives in `README.md`; this file is the working brief.

## What we are building

A service called **DemoVideoBot** that automatically produces two demo videos
for any agent on the AgenticQEAHub platform:

1. a **narrated** walkthrough (voice-over), and
2. a shorter **silent** cut (on-screen captions, no voice).

It works by logging into the platform, running the target agent, screen-recording
the run, writing a narration script from the run, then assembling both videos.
A React web UI lets users kick off the pipeline, review and edit the script,
and download the finished files.

AgenticQEAHub is an **external** system. We connect to it over the network. Its
code is NOT part of this repo — do not try to import or vendor it.

## Pipeline (build in this order)

1. `select_agent`    — fetch the target agent's metadata + spec doc
2. `capture_run`     — log in, open project + agent, run it, record video
3. `generate_script` — LLM (Gemini) writes a timed scene list from the run
4. `review_script`   — pause for a human to approve/edit before rendering
5. `synthesize_audio` — TTS voice-over from the approved script
6. `assemble_full`   — merge recording + voice-over → narrated video
7. `assemble_silent` — condensed cut with captions → silent video
8. `finalize`        — validate both files, clean up intermediates, write to `output/`

## Tech stack

- Python 3.11+
- LangGraph for orchestration (each pipeline stage is a node)
- Playwright for browser login + screen recording
- Google Gemini for the narration script and TTS voice-over (via `google-genai`, single API key)
- FFmpeg for video/audio assembly
- FastAPI — REST API backend (non-blocking pipeline via background threads)
- React + Vite — web UI for submitting jobs, reviewing scripts, and viewing results

## Hard rules

- **NEVER hardcode secrets.** Credentials and API keys come only from
  environment variables (see `.env.example`). Never write real values into
  code, tests, commits, or docs.
- **NEVER commit `.env`.** It is already in `.gitignore`. Keep it that way.
- Each pipeline node is a plain function: takes the state dict, returns a dict
  of updates. Keep nodes small and independently testable.
- Selectors for the platform UI (button IDs, field names) live in ONE place
  (`app/clients/hub_client.py`) so a UI change is a one-file fix.
- Prefer clear, boring code over clever code. This will be maintained by people
  who are new to the stack.

## Current status

- All 5 pipeline phases are implemented and 41 unit tests pass.
- The UI is built and the React build is served by FastAPI in production.
- **Inputs are display names**: users type "Project Name" (e.g. `Dev test project`) and "Agent Name" (e.g. `Defect Triage (CrewAI)`). Navigation goes login → projects listing → click project → click agent.
- UI selectors in `hub_client.py` are marked `# TODO: confirm` — they must be verified against the real AgenticQEAHub platform before a live end-to-end run.
- Per-agent HITL responses live in `agents/` — `agents/defect_triage_crewai.py` exists; add one file per new agent and register it in `agents/__init__.py`.
- Using a **personal Gemini API key** for now (prototype). Keep the key access in one place (`app/config.py`) so swapping it later is trivial.

## How to run

**Backend**
```bash
cd backend
pip install -r requirements.txt
python -m playwright install chromium
cp ../.env.example ../.env      # then fill in real values locally (never commit)
uvicorn app.api.routes:app --reload
```

**Frontend** (separate terminal)
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

## Definition of done for v1

Running the pipeline against one agent produces two playable files in `output/`:
a narrated 1920×1080 video with an audio track, and a shorter silent one with
captions. See the metrics table in `README.md` section 5.

## Where to look

- `README.md` — full approved design + rationale (do not contradict it)
- `docs/IMPLEMENTATION_PLAN.md` — the ordered task list (all 5 phases done)
- `docs/INSTALL.md` — step-by-step setup, run instructions, and how to add a new agent
- `backend/app/agent/state.py` — the shared state object every node reads/writes
- `backend/app/clients/hub_client.py` — all platform UI selectors live here
- `backend/agents/` — per-agent HITL prompt configs; one file per agent
- `frontend/src/` — React components and API client
