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

AgenticQEAHub is an **external** system. We connect to it over the network. Its
code is NOT part of this repo — do not try to import or vendor it.

## Pipeline (build in this order)

1. `select_agent`  — fetch the target agent's metadata + spec doc
2. `capture_run`   — log in, open project + agent, run it, record video
3. `generate_script` — LLM (Gemini) writes a timed scene list from the run
4. `review_script` — pause for a human to approve/edit before rendering
5. `synthesize_audio` — TTS voice-over from the approved script
6. `assemble_full` — merge recording + voice-over → narrated video
7. `assemble_silent` — condensed cut with captions → silent video
8. `finalize` — validate both files, write to `output/`

## Tech stack

- Python 3.11+
- LangGraph for orchestration (each pipeline stage is a node)
- Playwright for browser login + screen recording
- Google Gemini for the narration script and TTS voice-over (via `google-genai`, single API key)
- FFmpeg for video/audio assembly
- FastAPI to expose a "make a video for agent X" endpoint

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

## Current status / constraints

- Using a **personal Gemini API key** for now (prototype). Do not design
  anything that assumes an org key yet, but keep the key access in one place so
  swapping it later is trivial.
- No training data and none needed — this project does not train a model.
- No test fixtures yet. First real test target is the `defect-triaging-crewai`
  agent, for which reference videos already exist to compare against.

## How to run (once built)

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env      # then fill in real values locally (never commit)
uvicorn app.api.routes:app --reload
```

## Definition of done for v1

Running the pipeline against one agent produces two playable files in `output/`:
a narrated 1920x1080 video with an audio track, and a shorter silent one with
captions. See the metrics table in `README.md` section 5.

## Where to look

- `README.md` — full approved design + rationale (do not contradict it)
- `docs/IMPLEMENTATION_PLAN.md` — the ordered task list to work through (5 phases)
- `app/agent/state.py` — the shared state object every node reads/writes
