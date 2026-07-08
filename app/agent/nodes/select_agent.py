"""Fetch the target agent's name and spec/doc from the platform."""

from app.agent.state import VideoState
from app.clients import hub_client


def select_agent(state: VideoState) -> dict:
    info = hub_client.get_agent_spec(state["agent_id"])
    return {
        "agent_name": info["name"],
        "agent_spec": info["spec"],
        "status": "selected",
    }
