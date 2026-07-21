"""Turn the approved narration lines into a single voice-over track (TTS).

Each scene's narration is synthesized separately, then all clips are
concatenated in order into one WAV file that spans the full run.
"""

import re
import wave
from pathlib import Path

from app import config
from app.agent.state import VideoState
from app.clients import tts_client


def synthesize_audio(state: VideoState) -> dict:
    audio_dir = Path(config.OUTPUT_DIR) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    slug     = _slug(state["agent_name"])
    scenes   = state["scenes"]

    scene_wavs = []
    for i, scene in enumerate(scenes):
        wav_path = str(audio_dir / f"{slug}_scene_{i:03d}.wav")
        tts_client.synthesize(scene["narration"], wav_path)
        scene_wavs.append(wav_path)

    final_path = str(audio_dir / f"{slug}_narration.wav")
    _concatenate_wavs(scene_wavs, final_path)

    return {
        "narration_audio_path": final_path,
        "status": "audio_ready",
        "completed_steps": state.get("completed_steps", []) + ["synthesize_audio"],
    }


def _concatenate_wavs(paths: list[str], out_path: str) -> None:
    """Concatenate WAV files in order. All inputs must share the same format."""
    params_written = False
    with wave.open(out_path, "wb") as out_wav:
        for path in paths:
            with wave.open(path, "rb") as in_wav:
                if not params_written:
                    out_wav.setparams(in_wav.getparams())
                    params_written = True
                out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))


def _slug(name: str) -> str:
    """Convert a display name to a filesystem-safe slug."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")
