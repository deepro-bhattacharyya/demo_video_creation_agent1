"""Turn the approved narration lines into a single voice-over track (TTS)."""

from app.agent.state import VideoState


def synthesize_audio(state: VideoState) -> dict:
    # TODO (Milestone 5): TTS each scene's narration, concatenate to one track.
    raise NotImplementedError
    # return {"narration_audio_path": ..., "status": "audio_ready"}
