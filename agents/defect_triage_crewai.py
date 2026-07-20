"""Run input configuration for the Defect Triaging (CrewAI) agent.

Workspace: /workspace?agent=defect-triaging-crewai&project=proj-rbac-test (HCM Project)

Initial form: one text input labelled "DEFECT ID" + "Triage Defect →" submit button.
Mid-run HITL: six button-click prompts in the left conversation panel, detected via
              the "INPUT NEEDED" header that appears above each prompt.

All HITL responses are button clicks — there is no text input during the run.
HITL sequence confirmed by watching defect_triage_agent_80 (crew ai)_without audio.mp4.
"""

AGENT_NAME = "Defect Triaging (CrewAI)"
AGENT_SLUG = "defect-triaging-crewai"

# ---------------------------------------------------------------------------
# RUN_INPUTS — pre-run workspace form filled before clicking the submit button.
#
# The workspace for this agent shows a single "DEFECT ID" text input and a
# "Triage Defect →" button.  There are no other fields (no textarea, no select).
# Change the "value" of the first entry to use a different defect.
# ---------------------------------------------------------------------------

RUN_INPUTS: list[dict] = [
    {
        "label":      "Defect ID",
        "selector":   "input",
        "nth":        0,
        "value":      "80",
        "field_type": "fill",
    },
    {
        # Must be last — this is the button that starts the run.
        "label":      "Submit",
        "field_type": "submit",
        "value":      "Triage Defect",   # matches "Triage Defect →" via has-text
    },
]

# ---------------------------------------------------------------------------
# HITL_RESPONSES — mid-run prompts that pause the agent for user input.
#
# Each entry is matched when the "INPUT NEEDED" box is visible AND the
# prompt text contains `prompt_contains` (case-insensitive substring).
# The automation clicks the button whose label equals `response`.
#
# Order matters: entries are consumed in sequence and each fires at most once.
# ---------------------------------------------------------------------------

HITL_RESPONSES: list[dict] = [
    # HITL 1 — "Do you want to publish logs to ADO?  [1] YES  [2] NO"
    {
        "prompt_contains": "publish logs to ado",
        "response": "YES",
    },
    # HITL 2 — "Please find below N fetched logs. Select the ones to publish to ADO."
    #           Buttons: "Use all filtered logs" / "Skip log publishing"
    {
        "prompt_contains": "fetched logs",
        "response": "Use all filtered logs",
    },
    # HITL 3 — "Do you want to continue with Defect Analyzer?  [1] YES  [2] NO"
    {
        "prompt_contains": "continue with defect analyzer",
        "response": "YES",
    },
    # HITL 4 — "Do you want to publish the defect resolution to ADO?  [1] YES  [2] NO"
    {
        "prompt_contains": "publish the defect resolution",
        "response": "YES",
    },
    # HITL 5 — "Do you want to proceed with assigning the analyzed defect?  [1] YES  [2] NO"
    {
        "prompt_contains": "proceed with assigning",
        "response": "YES",
    },
    # HITL 6 — Numbered list of potential assignees ending with "[N] Skip assignment"
    #           Choosing "Skip assignment" keeps the automated run non-disruptive.
    {
        "prompt_contains": "skip assignment",
        "response": "Skip assignment",
    },
]
