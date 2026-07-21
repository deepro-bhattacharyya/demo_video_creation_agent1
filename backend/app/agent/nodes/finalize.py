"""Validate both outputs, log completion, and clean up intermediate files."""

import json
import shutil
import subprocess
from pathlib import Path

import structlog

from app import config
from app.agent.state import VideoState

log = structlog.get_logger()


def finalize(state: VideoState) -> dict:
    agent_id = state.get("agent_name", "unknown")
    log.info("finalize.start", agent=agent_id)

    # Confirm the narrated video has both a video stream AND an audio stream.
    _validate_narrated(state["narrated_video_path"])

    # Confirm the silent video has a video stream and NO audio stream.
    _validate_silent(state["silent_video_path"])

    # Delete the large raw recording and intermediate WAV clips — only the
    # final MP4s are needed after this point.
    _cleanup(state)

    log.info(
        "finalize.done",
        agent=agent_id,
        narrated=state["narrated_video_path"],
        silent=state["silent_video_path"],
    )
    return {
        "status": "done",
        "completed_steps": state.get("completed_steps", []) + ["finalize"],
    }


# ---------------------------------------------------------------------------
# ffprobe helpers
# ---------------------------------------------------------------------------

def _ffprobe(path: str) -> dict:
    """Run ffprobe on the file and return stream/format info as parsed JSON.

    ffprobe is FFmpeg's companion inspection tool — it reads the file without
    decoding it and reports what streams (video, audio) are present, along
    with the duration and resolution.
    """
    cmd = [
        "ffprobe", "-v", "error",               # suppress verbose output; only show errors
        "-show_entries", "stream=codec_type,width,height",  # which stream fields to report
        "-show_entries", "format=duration",      # also report the container duration
        "-of", "json",                           # output as JSON so we can parse it easily
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}:\n{result.stderr}")
    return json.loads(result.stdout)


def _validate_narrated(path: str) -> None:
    """Assert the narrated video has both a video and an audio stream.

    If the audio is missing it means assemble_full failed to merge the
    voice-over, so we catch it here rather than delivering a silent video
    that was supposed to have narration.
    """
    info = _ffprobe(path)
    codec_types = {s.get("codec_type") for s in info.get("streams", [])}
    if "video" not in codec_types:
        raise RuntimeError(f"Narrated video has no video stream: {path}")
    if "audio" not in codec_types:
        raise RuntimeError(f"Narrated video has no audio stream: {path}")


def _validate_silent(path: str) -> None:
    """Assert the silent video has a video stream and NO audio stream.

    The silent cut is intentionally audio-free (captions only). If an audio
    stream is present it means assemble_silent's -an flag was not applied,
    so we reject it here.
    """
    info = _ffprobe(path)
    codec_types = {s.get("codec_type") for s in info.get("streams", [])}
    if "video" not in codec_types:
        raise RuntimeError(f"Silent video has no video stream: {path}")
    if "audio" in codec_types:
        raise RuntimeError(f"Silent video unexpectedly has an audio stream: {path}")


# ---------------------------------------------------------------------------
# Disk cleanup
# ---------------------------------------------------------------------------

def _cleanup(state: VideoState) -> None:
    """Delete intermediate files once both final videos are validated.

    Kept files:  output/narrated_*.mp4  and  output/silent_*.mp4
    Deleted:     output/raw/*.webm  (the raw Playwright screen recording)
                 output/audio/      (per-scene WAV clips + the concatenated narration WAV)
    """
    # Delete the raw screen recording (can be several hundred MB).
    raw_path = Path(state.get("raw_video_path", ""))
    if raw_path.exists():
        raw_path.unlink()
        log.info("finalize.cleanup.raw", path=str(raw_path))

    # Delete the entire audio/ folder — individual scene WAVs are no longer needed.
    audio_dir = Path(config.OUTPUT_DIR) / "audio"
    if audio_dir.exists():
        shutil.rmtree(audio_dir)
        log.info("finalize.cleanup.audio", path=str(audio_dir))
