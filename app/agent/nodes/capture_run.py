"""Log in, open the project + agent, run it, and screen-record the run.

This mirrors the manual process: marketplace login -> project -> agent -> run.
Credentials come from app.config (env vars) — never hardcode them.
"""

from pathlib import Path

import structlog
from playwright.sync_api import sync_playwright

from app import config
from app.agent.state import VideoState
from app.clients import hub_client

log = structlog.get_logger()


def capture_run(state: VideoState) -> dict:
    log.info("capture_run.start", agent_id=state.get("agent_id"))
    raw_dir = Path(config.OUTPUT_DIR) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir=str(raw_dir),
            record_video_size={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        hub_client.login(page)

        # Navigate to the agent workspace.
        # URL format confirmed from README: /workspace?agent=<id>&project=<id>
        page.goto(
            f"{config.HUB_BASE_URL}{hub_client.WORKSPACE_PATH}"
            f"?agent={state['agent_id']}&project={state['project_id']}"
        )

        transcript = hub_client.run_agent_and_collect_events(
            page, state["agent_id"]
        )

        # Context must close before browser — this finalises the video file on disk.
        context.close()
        browser.close()

    video_path = _latest_video_in(raw_dir)
    log.info("capture_run.done", agent_id=state.get("agent_id"), video=video_path)
    return {
        "raw_video_path": video_path,
        "run_transcript": transcript,
        "status": "captured",
    }


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
