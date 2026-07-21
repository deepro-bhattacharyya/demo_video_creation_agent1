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

    # Build the filter graph: one trim+caption segment per scene, then concat them all.
    filter_complex, out_label = _build_filter_complex(state["scenes"])

    cmd = [
        "ffmpeg", "-y",                         # -y: overwrite output if it exists
        "-i", state["raw_video_path"],           # single input: the raw screen recording
        "-filter_complex", filter_complex,       # the full trim+caption+concat filter graph
        "-map", f"[{out_label}]",               # use the final concatenated stream as output
        "-an",                                   # -an: strip audio — this is the silent cut
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg assemble_silent failed:\n{result.stderr}")

    return {
        "silent_video_path": out_path,
        "status": "silent_assembled",
        "completed_steps": state.get("completed_steps", []) + ["assemble_silent"],
    }


def _escape_drawtext(text: str) -> str:
    """Escape special characters that would break FFmpeg's drawtext filter syntax."""
    text = text.replace("\\", "\\\\")  # backslash must come first
    text = text.replace("'",  "\\'")   # single quotes wrap the text value
    text = text.replace(":",  "\\:")   # colons separate filter key=value pairs
    text = text.replace("%",  "\\%")   # percent signs are format specifiers in drawtext
    return text


def _build_filter_complex(scenes: list[dict]) -> tuple[str, str]:
    """Build the FFmpeg filter_complex string for the silent cut.

    For each scene we:
      1. trim      — cut the exact start→end window from the recording
      2. setpts    — reset timestamps to 0 so clips join seamlessly
      3. drawtext  — burn the on_screen caption onto the bottom-centre of the frame

    All scene clips are then fed into concat to produce one continuous video.
    """
    parts  = []   # one filter chain per scene
    labels = []   # output label of each scene clip e.g. [v0], [v1], …

    for i, scene in enumerate(scenes):
        label   = f"v{i}"
        caption = _escape_drawtext(scene["on_screen"])
        parts.append(
            f"[0:v]"                                        # read from the single input video
            f"trim=start={scene['start']}:end={scene['end']},"  # cut this scene's time window
            f"setpts=PTS-STARTPTS,"                         # reset PTS so clip starts at t=0
            f"drawtext=text='{caption}'"                    # burn the caption text onto the frame
            f":fontsize=36:fontcolor=white:borderw=2:bordercolor=black"  # white text, black outline
            f":x=(w-text_w)/2:y=h-th-40"                   # centred horizontally, near the bottom
            f"[{label}]"                                    # label this clip's output stream
        )
        labels.append(f"[{label}]")

    n      = len(scenes)
    # Join all labelled clips in order; v=1 (video only), a=0 (no audio)
    concat = "".join(labels) + f"concat=n={n}:v=1:a=0[out]"
    return ";".join(parts) + ";" + concat, "out"


def _slug(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")
