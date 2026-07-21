"""Text-to-speech via Microsoft Edge TTS (edge-tts).

Completely free — no API key, no quota, no billing required.
Uses the same neural voices as Microsoft Edge browser's Read Aloud feature.

Output is a WAV file (PCM 24 kHz, mono, 16-bit) compatible with the WAV
concatenation in synthesize_audio.py. FFmpeg converts edge-tts MP3 output
to WAV — FFmpeg is already a required system dependency (see docs/INSTALL.md).

To list all available voices:
    edge-tts --list-voices
"""

import asyncio
import subprocess
from pathlib import Path

import edge_tts

# Neural voice used for all narration.
# en-US-AriaNeural — clear, professional female voice (recommended)
# en-US-GuyNeural  — professional male voice
# Change here to swap globally; no other file needs updating.
_VOICE = "en-US-AriaNeural"


def synthesize(text: str, out_path: str) -> str:
    """Render `text` to a WAV file at `out_path`; return the path."""
    mp3_path = str(Path(out_path).with_suffix(".mp3"))

    # edge-tts is async; run it synchronously here so the rest of the
    # pipeline (which is synchronous) doesn't need to change.
    asyncio.run(_synthesize_mp3(text, mp3_path))

    # Convert MP3 → WAV (16-bit PCM, 24 kHz, mono) — same spec as the
    # previous Gemini TTS output so synthesize_audio.py is unchanged.
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", mp3_path,
            "-acodec", "pcm_s16le",
            "-ar", "24000",
            "-ac", "1",
            out_path,
        ],
        check=True,
        capture_output=True,
    )

    Path(mp3_path).unlink(missing_ok=True)
    return out_path


async def _synthesize_mp3(text: str, mp3_path: str) -> None:
    communicate = edge_tts.Communicate(text, voice=_VOICE)
    await communicate.save(mp3_path)
