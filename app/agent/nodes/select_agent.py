"""Fetch the target agent's display name and spec.

Hub mode:        navigates to the platform and reads the agent card.
Standalone mode: reads agent_name and agent_description from demo_config.yaml
                 in the local agent folder — no network or browser needed.
"""

from app.agent.state import VideoState
from app.clients import hub_client


def select_agent(state: VideoState) -> dict:
    if state.get("source_type") == "standalone":
        from app.clients.standalone_client import load_demo_config
        cfg = load_demo_config(state["agent_folder"])
        return {
            "agent_display_name": cfg["agent_name"],
            "agent_spec": cfg.get("agent_description", ""),
            "status": "selected",
            "completed_steps": state.get("completed_steps", []) + ["select_agent"],
        }

    info = hub_client.get_agent_spec(state["project_name"], state["agent_name"])
    return {
        "agent_display_name": info["name"],
        "agent_spec": info["spec"],
        "status": "selected",
        "completed_steps": state.get("completed_steps", []) + ["select_agent"],
    }
