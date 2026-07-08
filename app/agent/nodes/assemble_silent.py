"""FFmpeg: build a shorter, silent cut with burned-in captions."""

from app.agent.state import VideoState


def assemble_silent(state: VideoState) -> dict:
    # TODO (Milestone 6): trim per scene timings, burn in narration as captions,
    # no audio track.
    raise NotImplementedError
    # return {"silent_video_path": ..., "status": "silent_assembled"}
