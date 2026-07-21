"""Log in, run the agent, and screen-record the run.

Hub mode:        logs into AgenticQEAHub, navigates to the agent workspace,
                 runs it, and records with Playwright's built-in recorder.
Standalone mode: reads demo_config.yaml from the agent folder, launches the
                 agent locally, and records via FFmpeg (terminal agents) or
                 Playwright (web UI agents).

Credentials for the hub come from app.config (env vars) — never hardcode them.
"""

import re
from pathlib import Path

import structlog
from playwright.sync_api import sync_playwright

from app import config
from app.agent.state import VideoState
from app.clients import hub_client
from agents import get_agent_config

log = structlog.get_logger()


def capture_run(state: VideoState) -> dict:
    if state.get("source_type") == "standalone":
        return _capture_standalone(state)
    return _capture_hub(state)


# ---------------------------------------------------------------------------
# Standalone path
# ---------------------------------------------------------------------------

def _capture_standalone(state: VideoState) -> dict:
    from app.clients.standalone_client import load_demo_config, run_and_record

    agent_folder = state["agent_folder"]
    log.info("capture_run.standalone.start", folder=agent_folder)

    demo_config = load_demo_config(agent_folder)

    raw_dir = Path(config.OUTPUT_DIR) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    video_path, transcript = run_and_record(agent_folder, demo_config, str(raw_dir))

    log.info("capture_run.standalone.done", video=video_path)
    return {
        "raw_video_path": video_path,
        "run_transcript": transcript,
        "status": "captured",
        "completed_steps": state.get("completed_steps", []) + ["capture_run"],
    }


# ---------------------------------------------------------------------------
# Hub (platform) path
# ---------------------------------------------------------------------------

def _capture_hub(state: VideoState) -> dict:
    agent_name   = state["agent_name"]
    project_name = state["project_name"]
    log.info("capture_run.hub.start", agent=agent_name, project=project_name)

    # Load per-agent run config (form inputs, HITL responses, completion signals).
    agent_cfg        = get_agent_config(agent_name)
    run_inputs       = getattr(agent_cfg, "RUN_INPUTS",       []) if agent_cfg else []
    hitl_responses   = getattr(agent_cfg, "HITL_RESPONSES",   []) if agent_cfg else []
    completion_texts = getattr(agent_cfg, "COMPLETION_TEXTS", []) if agent_cfg else []

    raw_dir = Path(config.OUTPUT_DIR) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # headless=False + --start-maximized: browser fills the screen so everyone
        # can watch the run live. no_viewport=True lets Playwright use the actual
        # maximized window size instead of a fixed 1920×1080 box that overflows panels.
        browser = p.chromium.launch(
            headless=False,
            args=["--start-maximized"],
        )
        context = browser.new_context(
            record_video_dir=str(raw_dir),
            record_video_size={"width": 1920, "height": 1080},
            no_viewport=True,          # use full maximized window, not a fixed box
            ignore_https_errors=True,
        )
        page = context.new_page()

        hub_client.login(page)

        transcript = hub_client.run_agent_and_collect_events(
            page,
            project_name=project_name,
            agent_name=agent_name,
            run_inputs=run_inputs,
            hitl_responses=hitl_responses,
            completion_texts=completion_texts,
        )

        # Context must close before browser — this finalises the video file on disk.
        context.close()
        browser.close()

    video_path = _latest_video_in(raw_dir)
    log.info("capture_run.hub.done", agent=agent_name, video=video_path)
    return {
        "raw_video_path": video_path,
        "run_transcript": transcript,
        "status": "captured",
        "completed_steps": state.get("completed_steps", []) + ["capture_run"],
    }


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _latest_video_in(directory: Path) -> str:
    """Return the path of the most recently written video file in directory."""
    videos = sorted(
        list(directory.glob("*.webm")) + list(directory.glob("*.mp4")),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if not videos:
        raise RuntimeError(
            f"No video file found in {directory} after capture. "
            "Check that Playwright's record_video_dir is set correctly."
        )
    return str(videos[0])


def _slug(name: str) -> str:
    """Convert a display name to a filesystem-safe slug for output filenames."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")
