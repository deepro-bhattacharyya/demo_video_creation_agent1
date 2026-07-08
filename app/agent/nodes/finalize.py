"""Validate both outputs and place them in the final output directory."""

from app.agent.state import VideoState


def finalize(state: VideoState) -> dict:
    # TODO (Milestone 7): ffprobe checks (resolution, audio present/absent,
    # durations), move finals into OUTPUT_DIR.
    raise NotImplementedError
    # return {"status": "done"}
