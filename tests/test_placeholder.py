"""Smoke test: verify the graph builds without errors.

First real test target: defect-triaging-crewai (reference videos exist).
Deeper unit tests live in test_generate_script.py, test_synthesize_audio.py,
and test_assemble.py.
"""


def test_graph_builds():
    from app.agent.graph import build_graph
    graph = build_graph()
    assert graph is not None
