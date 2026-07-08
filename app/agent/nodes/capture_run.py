"""Log in, open the project + agent, run it, and screen-record the run.

This mirrors the manual process: marketplace login -> project -> agent -> run.
Credentials come from app.config (env vars) — never hardcode them.
"""

from app.agent.state import VideoState


def capture_run(state: VideoState) -> dict:
    # TODO (Milestone 2):
    #   - launch Playwright, record_video_dir -> output/raw, size 1920x1080
    #   - hub_client.login(page)
    #   - navigate to workspace for state["agent_id"] / state["project_id"]
    #   - trigger the run, wait for completion, collect step events
    #   - close context to finalize the video file
    raise NotImplementedError
    # return {"raw_video_path": ..., "run_transcript": [...], "status": "captured"}
