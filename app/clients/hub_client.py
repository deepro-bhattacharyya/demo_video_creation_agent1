"""All interaction with the AgenticQEAHub platform lives here.

Keep every UI selector (login fields, buttons, nav) in THIS file only, so a
platform UI change is a one-file fix.
"""

from playwright.sync_api import sync_playwright, Page

from app import config

# ---------------------------------------------------------------------------
# UI selectors — update here if the platform UI changes.
# ---------------------------------------------------------------------------
EMAIL_FIELD = "#email"           # TODO: confirm real selector
PASSWORD_FIELD = "#password"     # TODO: confirm real selector
LOGIN_BUTTON = "#login"          # TODO: confirm real selector
POST_LOGIN_ELEMENT = ".user-menu"  # TODO: element that appears after a successful login

WORKSPACE_PATH = "/workspace"          # TODO: confirm workspace URL path (query params: ?agent=&project=)
AGENT_CATALOG_PATH = "/agents"         # TODO: confirm path in the platform
AGENT_NAME_SELECTOR = "h1.agent-name" # TODO: confirm selector on the agent detail page
AGENT_SPEC_SELECTOR = ".agent-spec"   # TODO: confirm selector for the spec/doc content

RUN_BUTTON_SELECTOR = ".run-agent-btn"     # TODO: confirm
RUN_COMPLETE_SELECTOR = ".run-status-done" # TODO: element that signals run completion
RUN_EVENT_SELECTOR = ".run-event-item"     # TODO: selector for individual step/HITL events


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def login(page: Page) -> None:
    """Log into the platform marketplace using credentials from config."""
    page.goto(f"{config.HUB_BASE_URL}/marketplace")
    page.fill(EMAIL_FIELD, config.HUB_EMAIL)
    page.fill(PASSWORD_FIELD, config.HUB_PASSWORD)
    page.click(LOGIN_BUTTON)
    # Wait for a post-login element to confirm the session is active.
    page.wait_for_selector(POST_LOGIN_ELEMENT, timeout=30_000)


# ---------------------------------------------------------------------------
# Agent catalog
# ---------------------------------------------------------------------------

def get_agent_spec(agent_id: str) -> dict:
    """Return {"name": ..., "spec": ...} for the given agent.

    Opens a short-lived Playwright session, logs in, navigates to the agent's
    detail page, and scrapes the display name and spec/doc text.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        login(page)

        # Navigate to the agent detail page.
        # TODO: confirm whether the platform uses a path like /agents/{id}
        # or a query-parameter URL like /catalog?agent={id}.
        page.goto(f"{config.HUB_BASE_URL}{AGENT_CATALOG_PATH}/{agent_id}")

        agent_name = page.inner_text(AGENT_NAME_SELECTOR).strip()
        agent_spec = page.inner_text(AGENT_SPEC_SELECTOR).strip()

        browser.close()

    return {"name": agent_name, "spec": agent_spec}


# ---------------------------------------------------------------------------
# Run capture (called from capture_run node)
# ---------------------------------------------------------------------------

def run_agent_and_collect_events(page: Page, agent_id: str) -> list[dict]:
    """Trigger a run for agent_id and collect its step/HITL events.

    Assumes the page is already logged in and on the agent workspace URL.
    Returns a list of event dicts: [{"type": ..., "content": ..., "timestamp": ...}]
    """
    # Trigger the run.
    page.click(RUN_BUTTON_SELECTOR)

    # Wait for the run to finish (adjust timeout for long-running agents).
    page.wait_for_selector(RUN_COMPLETE_SELECTOR, timeout=300_000)

    # Collect all step/HITL event elements from the run log.
    event_elements = page.query_selector_all(RUN_EVENT_SELECTOR)
    events = []
    for el in event_elements:
        # TODO: confirm the actual data attributes / inner structure of each event.
        events.append({
            "type": el.get_attribute("data-event-type") or "step",
            "content": el.inner_text().strip(),
            "timestamp": el.get_attribute("data-timestamp") or "",
        })

    return events
