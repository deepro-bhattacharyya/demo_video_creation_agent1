"""Unit tests for finalize validation helpers.

ffprobe subprocess calls are mocked — no real video files needed.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agent.nodes.finalize import _ffprobe, _validate_narrated, _validate_silent


def _mock_run(codec_types: list[str], returncode: int = 0) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = json.dumps({
        "streams": [{"codec_type": ct} for ct in codec_types],
        "format": {"duration": "120.0"},
    })
    m.stderr = ""
    return m


# --- _ffprobe ---

def test_ffprobe_returns_parsed_json():
    with patch("subprocess.run", return_value=_mock_run(["video", "audio"])):
        result = _ffprobe("fake.mp4")
    assert "streams" in result


def test_ffprobe_raises_on_nonzero_exit():
    m = MagicMock()
    m.returncode = 1
    m.stderr = "No such file"
    with patch("subprocess.run", return_value=m):
        with pytest.raises(RuntimeError, match="ffprobe failed"):
            _ffprobe("nonexistent.mp4")


# --- _validate_narrated ---

def test_narrated_passes_with_video_and_audio():
    with patch("subprocess.run", return_value=_mock_run(["video", "audio"])):
        _validate_narrated("narrated.mp4")  # should not raise


def test_narrated_raises_when_no_audio():
    with patch("subprocess.run", return_value=_mock_run(["video"])):
        with pytest.raises(RuntimeError, match="no audio stream"):
            _validate_narrated("narrated.mp4")


def test_narrated_raises_when_no_video():
    with patch("subprocess.run", return_value=_mock_run(["audio"])):
        with pytest.raises(RuntimeError, match="no video stream"):
            _validate_narrated("narrated.mp4")


# --- _validate_silent ---

def test_silent_passes_with_video_only():
    with patch("subprocess.run", return_value=_mock_run(["video"])):
        _validate_silent("silent.mp4")  # should not raise


def test_silent_raises_when_audio_present():
    with patch("subprocess.run", return_value=_mock_run(["video", "audio"])):
        with pytest.raises(RuntimeError, match="audio stream"):
            _validate_silent("silent.mp4")


def test_silent_raises_when_no_video():
    with patch("subprocess.run", return_value=_mock_run([])):
        with pytest.raises(RuntimeError, match="no video stream"):
            _validate_silent("silent.mp4")
