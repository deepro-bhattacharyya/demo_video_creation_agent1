"""Wires the pipeline nodes together into a runnable LangGraph.

Order matches CLAUDE.md. The narrated and silent cuts both branch off the
approved script and rejoin at finalize.
"""

from langgraph.graph import START, END, StateGraph
from langgraph.types import RetryPolicy

from app.agent.state import VideoState
from app.agent.nodes.select_agent import select_agent
from app.agent.nodes.capture_run import capture_run
from app.agent.nodes.generate_script import generate_script
from app.agent.nodes.review_script import review_script
from app.agent.nodes.synthesize_audio import synthesize_audio
from app.agent.nodes.assemble_full import assemble_full
from app.agent.nodes.assemble_silent import assemble_silent
from app.agent.nodes.finalize import finalize


def build_graph():
    builder = StateGraph(VideoState)

    builder.add_node("select_agent", select_agent)
    builder.add_node("capture_run", capture_run,
                     retry_policy=RetryPolicy(max_attempts=2))
    builder.add_node("generate_script", generate_script,
                     retry_policy=RetryPolicy(max_attempts=3))
    builder.add_node("review_script", review_script)
    builder.add_node("synthesize_audio", synthesize_audio)
    builder.add_node("assemble_full", assemble_full)
    builder.add_node("assemble_silent", assemble_silent)
    builder.add_node("finalize", finalize)

    builder.add_edge(START, "select_agent")
    builder.add_edge("select_agent", "capture_run")
    builder.add_edge("capture_run", "generate_script")
    builder.add_edge("generate_script", "review_script")

    # Both cuts only start once the script is approved
    builder.add_edge("review_script", "synthesize_audio")
    builder.add_edge("review_script", "assemble_silent")
    builder.add_edge("synthesize_audio", "assemble_full")

    builder.add_edge("assemble_full", "finalize")
    builder.add_edge("assemble_silent", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile()
