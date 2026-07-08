"""FFmpeg: merge the screen recording with the voice-over -> narrated video."""

import subprocess
from pathlib import Path

from app import config
from app.agent.state import VideoState


def assemble_full(state: VideoState) -> dict:
    out_dir = Path(config.OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = str(out_dir / f"narrated_{state['agent_id']}.mp4")

    # Mux video + audio.  -c:v copy avoids re-encoding the video stream.
    # -c:a aac converts the WAV narration to AAC for the MP4 container.
    # -shortest stops at whichever stream ends first (video or audio).
    cmd = [
        "ffmpeg", "-y",
        "-i", state["raw_video_path"],
        "-i", state["narration_audio_path"],
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg assemble_full failed:\n{result.stderr}")

    return {
        "narrated_video_path": out_path,
        "status": "full_assembled",
    }
