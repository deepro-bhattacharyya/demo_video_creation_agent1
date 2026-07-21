"""Unit tests for assemble_silent helpers.

No FFmpeg call is made — we test caption escaping and filter-complex
string construction in isolation.
"""

from app.agent.nodes.assemble_silent import _escape_drawtext, _build_filter_complex


# --- _escape_drawtext ---

def test_escape_colon():
    assert "\\:" in _escape_drawtext("step: one")


def test_escape_percent():
    assert "\\%" in _escape_drawtext("100% done")


def test_escape_backslash():
    result = _escape_drawtext("a\\b")
    assert "\\\\" in result


def test_escape_single_quote():
    result = _escape_drawtext("it's done")
    # Raw unescaped ' must not remain (except as part of \')
    assert "\\'" in result


def test_escape_plain_text_unchanged():
    assert _escape_drawtext("Hello World") == "Hello World"


# --- _build_filter_complex ---

def _scenes(n=2):
    return [
        {"start": i * 5, "end": (i + 1) * 5, "on_screen": f"Scene {i}", "narration": "..."}
        for i in range(n)
    ]


def test_output_label_is_out():
    _, label = _build_filter_complex(_scenes(1))
    assert label == "out"


def test_single_scene_filter():
    fc, _ = _build_filter_complex(_scenes(1))
    assert "trim=start=0:end=5" in fc
    assert "concat=n=1:v=1:a=0" in fc
    assert "Scene 0" in fc


def test_two_scene_filter():
    fc, _ = _build_filter_complex(_scenes(2))
    assert "trim=start=0:end=5" in fc
    assert "trim=start=5:end=10" in fc
    assert "concat=n=2:v=1:a=0" in fc


def test_all_scene_labels_present():
    scenes = _scenes(3)
    fc, _ = _build_filter_complex(scenes)
    for i in range(3):
        assert f"[v{i}]" in fc


def test_setpts_present():
    fc, _ = _build_filter_complex(_scenes(1))
    assert "setpts=PTS-STARTPTS" in fc


def test_drawtext_style_present():
    fc, _ = _build_filter_complex(_scenes(1))
    assert "fontsize=36" in fc
    assert "fontcolor=white" in fc
    assert "bordercolor=black" in fc
