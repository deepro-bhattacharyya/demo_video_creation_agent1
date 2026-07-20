"""Agent-specific configuration files for DemoVideoBot.

Each module in this package corresponds to one agent on the AgenticQEAHub
platform and declares the HITL prompts that agent will send during a run,
along with the default responses the automation should supply so the
screen recording can proceed unattended.

Usage (in capture_run.py):
    from agents import get_agent_config
    config = get_agent_config(state["agent_name"])
    hitl_responses = config.HITL_RESPONSES if config else []
"""

import importlib
import re
from types import ModuleType


def _slug(name: str) -> str:
    """Normalise a display name to the module filename convention.

    "Defect Triage (CrewAI)"  ->  "defect_triage_crewai"
    "HCM Onboarding (LangGraph)" -> "hcm_onboarding_langgraph"
    """
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


# Map of normalised slug → module name in this package.
# Add a new entry each time a new agent config file is created.
_REGISTRY: dict[str, str] = {
    # Defect Triaging — Neo4j Lookup flow, 2 HITL prompts
    "defect_triaging":            "agents.defect_triaging",

    # Defect Triaging (CrewAI) — alternate implementation, 6 HITL prompts
    "defect_triage_crewai":       "agents.defect_triage_crewai",
    "defect_triaging__crewai_":   "agents.defect_triage_crewai",   # alternate slug form
    "defect_triage__crewai_":     "agents.defect_triage_crewai",   # legacy slug form
}


def get_agent_config(agent_name: str) -> ModuleType | None:
    """Return the config module for agent_name, or None if no config exists.

    Looks up by normalised slug so display-name spelling variations
    ("Defect Triage (CrewAI)" vs "defect triage crewai") all resolve
    to the same module.
    """
    slug = _slug(agent_name)
    module_path = _REGISTRY.get(slug)
    if module_path is None:
        return None
    return importlib.import_module(module_path)
