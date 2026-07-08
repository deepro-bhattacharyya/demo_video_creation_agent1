"""FFmpeg: merge the screen recording with the voice-over -> narrated video."""

from app.agent.state import VideoState


def assemble_full(state: VideoState) -> dict:
    # TODO (Milestone 5): mux raw_video_path + narration_audio_path.
    raise NotImplementedError
    # return {"narrated_video_path": ..., "status": "full_assembled"}
