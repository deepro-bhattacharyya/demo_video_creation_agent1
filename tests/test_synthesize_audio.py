"""Unit tests for synthesize_audio._concatenate_wavs.

No TTS call is made — we test the WAV concatenation helper in isolation.
"""

import io
import struct
import wave

from app.agent.nodes.synthesize_audio import _concatenate_wavs


def _make_wav_bytes(num_frames: int) -> bytes:
    """Return a minimal valid WAV (PCM 16-bit 24kHz mono) as bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(struct.pack(f"<{num_frames}h", *([0] * num_frames)))
    return buf.getvalue()


def test_concatenate_two_wavs(tmp_path):
    a = tmp_path / "a.wav"
    b = tmp_path / "b.wav"
    out = tmp_path / "out.wav"

    a.write_bytes(_make_wav_bytes(100))
    b.write_bytes(_make_wav_bytes(200))

    _concatenate_wavs([str(a), str(b)], str(out))

    with wave.open(str(out), "rb") as w:
        assert w.getnframes() == 300


def test_concatenate_single_wav(tmp_path):
    a = tmp_path / "a.wav"
    out = tmp_path / "out.wav"
    a.write_bytes(_make_wav_bytes(50))

    _concatenate_wavs([str(a)], str(out))

    with wave.open(str(out), "rb") as w:
        assert w.getnframes() == 50


def test_concatenate_three_wavs(tmp_path):
    paths = []
    for i, n in enumerate([10, 20, 30]):
        p = tmp_path / f"{i}.wav"
        p.write_bytes(_make_wav_bytes(n))
        paths.append(str(p))
    out = tmp_path / "out.wav"

    _concatenate_wavs(paths, str(out))

    with wave.open(str(out), "rb") as w:
        assert w.getnframes() == 60


def test_output_preserves_format(tmp_path):
    a = tmp_path / "a.wav"
    out = tmp_path / "out.wav"
    a.write_bytes(_make_wav_bytes(100))

    _concatenate_wavs([str(a)], str(out))

    with wave.open(str(out), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == 24000
