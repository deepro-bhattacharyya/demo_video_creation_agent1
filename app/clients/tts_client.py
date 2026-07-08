"""Text-to-speech via Google Gemini TTS.

Uses the same GEMINI_API_KEY as script generation — no separate TTS provider needed.
Output is a WAV file (PCM 24 kHz, mono, 16-bit) at the given path.
"""

import wave

from google import genai
from google.genai import types

from app import config

# Voice used for all narration. Change here to swap globally.
_VOICE = "Kore"
_TTS_MODEL = "gemini-2.0-flash-preview-tts"


def synthesize(text: str, out_path: str) -> str:
    """Render `text` to a WAV file at `out_path`; return the path."""
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    response = client.models.generate_content(
        model=_TTS_MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=_VOICE
                    )
                )
            ),
        ),
    )

    audio_bytes: bytes = (
        response.candidates[0].content.parts[0].inline_data.data
    )

    # Gemini TTS returns raw 16-bit PCM at 24 kHz mono; wrap in a WAV container.
    with wave.open(out_path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)   # 16-bit = 2 bytes
        wav.setframerate(24000)
        wav.writeframes(audio_bytes)

    return out_path
