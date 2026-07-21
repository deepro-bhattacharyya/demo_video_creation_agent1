"""Run input and HITL configuration for the Defect Triaging agent (Neo4j flow).

Workspace URL (HCM Project):
  /workspace?agent=defect-triaging&project=proj-rbac-test

== Full run walkthrough (from defect_triage_agent_without_audio.mp4) ==

Step 1 — Navigate to workspace, click "Neo4j Lookup" tab.
Step 2 — Fill the single DEFECT ID field with the ticket number (default: "80").
Step 3 — Click "Triage Defect →" to start the run. Status becomes "Running".
Step 4 — The agent auto-fetches defect details, steps, and logs from Neo4j/ADO.

HITL prompt 1 (fires after log fetch):
  "Do you want to continue with Defect Analyzer? [1] YES  [2] NO"
  → Click the "YES" button.

HITL prompt 2 (fires after root-cause analysis, status returns to "Awaiting Input"):
  A numbered list of candidate assignees is shown, ending with "Skip assignment".
  → Click the chosen assignee's name from the list.

Completion — all three of these appear when the run succeeds:
  • "Triage Summary"
  • "Resolution published to ADO"
  • "Flow ended" (or "Successfully assigned defect")

== HOW TO CHANGE THE DEFECT ==
  Update RUN_INPUTS[1]["value"] to a different Defect ID.

== HOW TO CHANGE THE ASSIGNEE ==
  Update HITL_RESPONSES[1]["response"] to the exact name shown in the platform list.
"""

AGENT_NAME = "Defect Triaging"
AGENT_SLUG = "defect-triaging"

# ---------------------------------------------------------------------------
# RUN_INPUTS — actions taken before / at run start, in order.
#
# field_type values:
#   "click"  — click a selector (e.g. a tab button)
#   "fill"   — type into an input or textarea (uses pressSequentially for React)
#   "select" — choose a <select> option by value
#   "submit" — the button that kicks off the agent run (must be last)
# ---------------------------------------------------------------------------

RUN_INPUTS: list[dict] = [
    {
        # Switch to the Neo4j Lookup tab (one input field: Defect ID only).
        "label":      "Select Neo4j Lookup tab",
        "field_type": "click",
        "selector":   "button:has-text('Neo4j Lookup')",
    },
    {
        # The single DEFECT ID field (placeholder: e.g. "DEF-123" or "BANK-389").
        # Change this value to triage a different defect.
        "label":      "Defect ID",
        "field_type": "fill",
        "selector":   "input",
        "nth":        0,
        "value":      "80",
    },
    {
        # Clicking "Triage Defect" starts the agent run. Must be last.
        "label":      "Submit",
        "field_type": "submit",
        "value":      "Triage Defect",
    },
]

# ---------------------------------------------------------------------------
# HITL_RESPONSES — prompts that pause the run for user input, in order.
#
# Matching: when "INPUT NEEDED" is visible AND prompt_contains is a
# case-insensitive substring of the page text, the automation clicks
# the element whose label equals `response`.
#
# response_type values:
#   "button" — click a <button> with that text  (default)
#   "text"   — click the first element (any tag) containing that text;
#              used for list-style picks where items are not <button>s
# ---------------------------------------------------------------------------

HITL_RESPONSES: list[dict] = [
    {
        # HITL 1 — fires after the agent fetches the defect and logs.
        # Prompt: "Do you want to continue with Defect Analyzer? [1] YES  [2] NO"
        "prompt_contains": "continue with defect analyzer",
        "response":        "YES",
        "response_type":   "button",
    },
    {
        # HITL 2 — fires after root-cause analysis.
        # Prompt: a numbered list of candidate assignees + "Skip assignment" at the end.
        # "skip assignment" is always present in the prompt text → reliable trigger.
        # The response is the exact name to click from the list.
        "prompt_contains": "skip assignment",
        "response":        "Arul Amuthan, Ahill Savio (Cognizant)",
        "response_type":   "text",
    },
]

# ---------------------------------------------------------------------------
# COMPLETION_TEXTS — any one of these appearing in the page confirms the run
# is done. Used by hub_client._wait_for_completion().
# ---------------------------------------------------------------------------

COMPLETION_TEXTS: list[str] = [
    "flow ended",
    "successfully assigned defect",
    "triage summary",
    "resolution published to ado",
]
