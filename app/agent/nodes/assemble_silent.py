"""FFmpeg: build a shorter, silent cut with burned-in captions.

Each scene from the approved script is trimmed from the raw recording,
has its on_screen caption burned in, and all clips are concatenated.
The final file has no audio track.
"""

import re
import subprocess
from pathlib import Path

from app import config
from app.agent.state import VideoState


def assemble_silent(state: VideoState) -> dict:
    out_dir = Path(config.OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    slug     = _slug(state["agent_name"])
    out_path = str(out_dir / f"silent_{slug}.mp4")

    filter_complex, out_label = _build_filter_complex(state["scenes"])

    cmd = [
        "ffmpeg", "-y",
        "-i", state["raw_video_path"],
        "-filter_complex", filter_complex,
        "-map", f"[{out_label}]",
        "-an",   # drop audio track
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg assemble_silent failed:\n{result.stderr}")

    return {
        "silent_video_path": out_path,
        "status": "silent_assembled",
    }


def _escape_drawtext(text: str) -> str:
    """Escape text for use inside an FFmpeg drawtext filter value."""
    text = text.replace("\\", "\\\\")
    text = text.replace("'",  "\\'")
    text = text.replace(":",  "\\:")
    text = text.replace("%",  "\\%")
    return text


def _build_filter_complex(scenes: list[dict]) -> tuple[str, str]:
    """Return (filter_complex_string, output_label) for the silent cut."""
    parts  = []
    labels = []

    for i, scene in enumerate(scenes):
        label   = f"v{i}"
        caption = _escape_drawtext(scene["on_screen"])
        parts.append(
            f"[0:v]"
            f"trim=start={scene['start']}:end={scene['end']},"
            f"setpts=PTS-STARTPTS,"
            f"drawtext=text='{caption}'"
            f":fontsize=36:fontcolor=white:borderw=2:bordercolor=black"
            f":x=(w-text_w)/2:y=h-th-40"
            f"[{label}]"
        )
        labels.append(f"[{label}]")

    n      = len(scenes)
    concat = "".join(labels) + f"concat=n={n}:v=1:a=0[out]"
    return ";".join(parts) + ";" + concat, "out"


def _slug(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")
