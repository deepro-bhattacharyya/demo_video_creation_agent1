"""Turn the approved narration lines into a single voice-over track (TTS).

Each scene's narration is synthesized separately, then all clips are
concatenated in order into one WAV file that spans the full run.
"""

import wave
from pathlib import Path

from app import config
from app.agent.state import VideoState
from app.clients import tts_client


def synthesize_audio(state: VideoState) -> dict:
    audio_dir = Path(config.OUTPUT_DIR) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    agent_id = state["agent_id"]
    scenes = state["scenes"]

    # TTS each scene's narration into its own WAV file.
    scene_wavs = []
    for i, scene in enumerate(scenes):
        wav_path = str(audio_dir / f"{agent_id}_scene_{i:03d}.wav")
        tts_client.synthesize(scene["narration"], wav_path)
        scene_wavs.append(wav_path)

    # Concatenate all scene WAVs into one continuous narration track.
    final_path = str(audio_dir / f"{agent_id}_narration.wav")
    _concatenate_wavs(scene_wavs, final_path)

    return {
        "narration_audio_path": final_path,
        "status": "audio_ready",
    }


def _concatenate_wavs(paths: list[str], out_path: str) -> None:
    """Concatenate WAV files in order into out_path. All inputs must share the same format."""
    params_written = False
    with wave.open(out_path, "wb") as out_wav:
        for path in paths:
            with wave.open(path, "rb") as in_wav:
                if not params_written:
                    out_wav.setparams(in_wav.getparams())
                    params_written = True
                out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))
