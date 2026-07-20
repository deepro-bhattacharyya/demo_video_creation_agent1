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

    _validate_narrated(state["narrated_video_path"])
    _validate_silent(state["silent_video_path"])

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
    """Run ffprobe on path and return parsed JSON output."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type,width,height",
        "-show_entries", "format=duration",
        "-of", "json",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}:\n{result.stderr}")
    return json.loads(result.stdout)


def _validate_narrated(path: str) -> None:
    """Assert the narrated video has both a video and an audio stream."""
    info = _ffprobe(path)
    codec_types = {s.get("codec_type") for s in info.get("streams", [])}
    if "video" not in codec_types:
        raise RuntimeError(f"Narrated video has no video stream: {path}")
    if "audio" not in codec_types:
        raise RuntimeError(f"Narrated video has no audio stream: {path}")


def _validate_silent(path: str) -> None:
    """Assert the silent video has a video stream and NO audio stream."""
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
    """Remove the raw recording and intermediate audio files to free disk space."""
    raw_path = Path(state.get("raw_video_path", ""))
    if raw_path.exists():
        raw_path.unlink()
        log.info("finalize.cleanup.raw", path=str(raw_path))

    audio_dir = Path(config.OUTPUT_DIR) / "audio"
    if audio_dir.exists():
        shutil.rmtree(audio_dir)
        log.info("finalize.cleanup.audio", path=str(audio_dir))
