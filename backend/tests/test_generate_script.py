"""Unit tests for generate_script._parse_and_validate.

No Gemini API call is made — we test the parser/validator in isolation.
"""

import json
import pytest

from app.agent.nodes.generate_script import _parse_and_validate


def _scene(start=0, end=5, on_screen="Hello", narration="Hi there"):
    return {"start": start, "end": end, "on_screen": on_screen, "narration": narration}


def _raw(scenes):
    return json.dumps(scenes)


# --- happy path ---

def test_single_valid_scene():
    scenes = _parse_and_validate(_raw([_scene()]))
    assert len(scenes) == 1
    assert scenes[0]["start"] == 0
    assert scenes[0]["end"] == 5


def test_multiple_scenes_in_order():
    scenes = _parse_and_validate(_raw([_scene(0, 5), _scene(5, 10)]))
    assert len(scenes) == 2


def test_strips_markdown_fences():
    raw = "```json\n" + _raw([_scene()]) + "\n```"
    scenes = _parse_and_validate(raw)
    assert len(scenes) == 1


def test_first_scene_start_nudged_to_zero():
    # Gemini sometimes starts at a small positive number — we fix it.
    scenes = _parse_and_validate(_raw([_scene(start=0.5, end=5)]))
    assert scenes[0]["start"] == 0


# --- validation errors ---

def test_empty_list_raises():
    with pytest.raises(ValueError, match="empty"):
        _parse_and_validate("[]")


def test_missing_narration_raises():
    bad = [{"start": 0, "end": 5, "on_screen": "Hello"}]
    with pytest.raises(ValueError, match="missing fields"):
        _parse_and_validate(json.dumps(bad))


def test_missing_on_screen_raises():
    bad = [{"start": 0, "end": 5, "narration": "Hi"}]
    with pytest.raises(ValueError, match="missing fields"):
        _parse_and_validate(json.dumps(bad))


def test_end_before_start_raises():
    with pytest.raises(ValueError, match="end.*<=.*start"):
        _parse_and_validate(_raw([_scene(start=5, end=3)]))


def test_end_equal_start_raises():
    with pytest.raises(ValueError, match="end.*<=.*start"):
        _parse_and_validate(_raw([_scene(start=5, end=5)]))


def test_overlapping_scenes_raises():
    scenes = [_scene(0, 10), _scene(5, 15)]   # overlap at 5-10
    with pytest.raises(ValueError, match="overlap"):
        _parse_and_validate(_raw(scenes))


def test_invalid_json_raises():
    with pytest.raises(Exception):
        _parse_and_validate("not json at all")
