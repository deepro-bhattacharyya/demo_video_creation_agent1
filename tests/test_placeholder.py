"""First real test target: defect-triaging-crewai (reference videos exist).

Add unit tests here with the hub + TTS mocked as nodes get implemented
(see IMPLEMENTATION_PLAN.md, Milestone 8).
"""


def test_scaffold_imports():
    from app.agent.graph import build_graph
    assert build_graph() is not None
