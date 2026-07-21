"""FFmpeg: merge the screen recording with the voice-over -> narrated video."""

import re
import subprocess
from pathlib import Path

from app import config
from app.agent.state import VideoState


def assemble_full(state: VideoState) -> dict:
    out_dir = Path(config.OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    slug     = _slug(state["agent_name"])
    out_path = str(out_dir / f"narrated_{slug}.mp4")

    cmd = [
        "ffmpeg", "-y",                        # -y: overwrite output file if it already exists
        "-i", state["raw_video_path"],          # input 0: the raw screen recording (from Playwright)
        "-i", state["narration_audio_path"],    # input 1: the Edge TTS voice-over WAV
        "-map", "0:v:0",                        # take the video stream from input 0 (the recording)
        "-map", "1:a:0",                        # take the audio stream from input 1 (the voice-over)
        "-c:v", "copy",                         # copy video as-is — no re-encoding, much faster
        "-c:a", "aac",                          # encode audio to AAC so MP4 container accepts it
        "-shortest",                            # stop when the shorter stream ends (avoids silence padding)
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg assemble_full failed:\n{result.stderr}")

    return {
        "narrated_video_path": out_path,
        "status": "full_assembled",
        "completed_steps": state.get("completed_steps", []) + ["assemble_full"],
    }


def _slug(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")
