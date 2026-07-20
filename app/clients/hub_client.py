"""All interaction with the AgenticQEAHub platform lives here.

Keep every UI selector (login fields, buttons, nav) in THIS file only, so a
platform UI change is a one-file fix.

Confirmed selectors (verified against the live platform via scripts/map_navigation.py
and video analysis of defect_triage_agent_80 (crew ai)_without audio.mp4):

  Login page  : /login
  Email field : input[type='email']
  Password    : input[type='password']
  Sign in btn : button:has-text('Sign in')
  Post-login  : sidebar nav text — "Projects" / "Agent Builder" / "Review Queue"
                (URL stays /login on this Next.js SPA even after successful auth)

  Projects URL: /projects
  Project nav : div[style*="cursor: pointer"] whose textContent contains the name
                (these are card divs in the grid — not the header context-switcher)
  Project page: /projects/{project-id}
  Agent link  : <a href="/workspace?agent={slug}&project={id}">Run</a>

  Workspace   : /workspace?agent={slug}&project={project-id}
  Run inputs  : passed per-agent from agents/<slug>.py as RUN_INPUTS list
  Submit btn  : button:has-text(submit_text) where text comes from agent config
  HITL prompt : "INPUT NEEDED" text visible in the left conversation panel;
                responses are button clicks (not text input)
  Completion  : status badge shows "Completed" after "Running" was seen
"""

import time

from playwright.sync_api import Page, sync_playwright

from app import config

# ---------------------------------------------------------------------------
# Timeouts / polling
# ---------------------------------------------------------------------------

_LOGIN_TIMEOUT    = 30_000   # ms — wait for post-login element
_NAV_TIMEOUT      = 15_000   # ms — page.goto / wait_for_url
_SUBMIT_WAIT      = 2        # s  — after clicking the workspace submit button
_RUN_TIMEOUT      = 600      # s  — max time to wait for agent run completion
_POLL_INTERVAL    = 5        # s  — how often to poll for completion


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def login(page: Page) -> None:
    """Log into the platform using credentials from environment variables.

    The platform is a Next.js SPA: after clicking Sign in the URL may stay on
    /login while the content switches to the authenticated view.  We confirm
    login by waiting for sidebar nav text to appear rather than checking the URL.
    """
    page.goto(f"{config.HUB_BASE_URL}/login", timeout=_NAV_TIMEOUT)
    time.sleep(2)  # let the page hydrate before filling
    page.fill("input[type='email']", config.HUB_EMAIL)
    page.fill("input[type='password']", config.HUB_PASSWORD)
    page.click("button:has-text('Sign in')")

    deadline = time.time() + _LOGIN_TIMEOUT / 1000
    while time.time() < deadline:
        try:
            for text in ["Projects", "Agent Builder", "Review Queue"]:
                if page.locator(f"text={text!r}").count() > 0:
                    return
        except Exception:
            pass
        time.sleep(1)

    raise RuntimeError(
        "Login failed: authenticated sidebar content not visible after sign-in. "
        "Check HUB_EMAIL / HUB_PASSWORD in .env"
    )


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

def navigate_to_project(page: Page, project_name: str) -> None:
    """Navigate to a project's agent-listing page by display name.

    Project cards on /projects are <div style="cursor: pointer"> elements —
    the entire card is clickable and navigates to /projects/{id}.
    (The header dropdown is a context-switcher for a different purpose;
     do not confuse it with the project cards in the grid.)
    """
    page.goto(f"{config.HUB_BASE_URL}/projects", timeout=_NAV_TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=_NAV_TIMEOUT)
    time.sleep(2)  # let cards finish rendering

    found = page.evaluate("""(name) => {
        const divs = Array.from(document.querySelectorAll('div[style*="cursor: pointer"]'));
        for (const div of divs) {
            if (div.textContent.toLowerCase().includes(name.toLowerCase())) {
                div.click();
                return true;
            }
        }
        return false;
    }""", project_name)

    if not found:
        raise RuntimeError(
            f"Could not find project card for '{project_name}'. "
            "Check that the project name matches exactly what's shown in the platform."
        )

    # Wait for navigation to /projects/{id}
    page.wait_for_url(f"{config.HUB_BASE_URL}/projects/*", timeout=_NAV_TIMEOUT)
    time.sleep(1)  # let the agent list finish rendering


def navigate_to_agent_workspace(page: Page, project_name: str, agent_name: str) -> None:
    """Navigate to the agent's workspace page (the run form / chat interface).

    Flow: /projects -> click project (via context switcher) ->
          /projects/{id} -> click agent's 'Run' link ->
          /workspace?agent={slug}&project={id}
    """
    navigate_to_project(page, project_name)

    # Find the <a href="/workspace?...">Run</a> link whose sibling span
    # contains the agent name.
    workspace_href = page.evaluate("""(agentName) => {
        const spans = Array.from(document.querySelectorAll('span'));
        for (const span of spans) {
            if (span.textContent.trim().toLowerCase().includes(agentName.toLowerCase())) {
                let el = span.parentElement;
                for (let i = 0; i < 8; i++) {
                    if (!el) break;
                    const links = el.querySelectorAll('a[href*="/workspace"]');
                    if (links.length > 0) return links[0].getAttribute('href');
                    el = el.parentElement;
                }
            }
        }
        return null;
    }""", agent_name)

    if not workspace_href:
        raise RuntimeError(
            f"Could not find agent '{agent_name}' in project '{project_name}'. "
            "Check that both names match exactly what's shown in the platform."
        )

    page.goto(f"{config.HUB_BASE_URL}{workspace_href}", timeout=_NAV_TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=_NAV_TIMEOUT)
    # Wait for the form input to actually render before we try to fill it.
    page.wait_for_selector("input, textarea", timeout=10_000)
    # Zoom out to 80 % so the CONVERSATION panel and GENERATED OUTPUT panel
    # both fit fully on screen without horizontal overflow or cut-off cards.
    page.evaluate("document.documentElement.style.zoom = '0.8'")


# ---------------------------------------------------------------------------
# Agent spec (used by select_agent node — no recording)
# ---------------------------------------------------------------------------

def get_agent_spec(project_name: str, agent_name: str) -> dict:
    """Return {"name": ..., "spec": ...} by navigating to the project agent list.

    The agent's description is the truncated <p> element next to its name.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        login(page)
        navigate_to_project(page, project_name)

        info = page.evaluate("""(agentName) => {
            const spans = Array.from(document.querySelectorAll('span'));
            for (const span of spans) {
                if (span.textContent.trim().toLowerCase().includes(agentName.toLowerCase())) {
                    let el = span.parentElement;
                    for (let i = 0; i < 6; i++) {
                        if (!el) break;
                        const p = el.querySelector('p');
                        if (p) return {name: span.textContent.trim(), spec: p.textContent.trim()};
                        el = el.parentElement;
                    }
                    return {name: span.textContent.trim(), spec: ''};
                }
            }
            return null;
        }""", agent_name)

        context.close()
        browser.close()

    if not info:
        raise RuntimeError(
            f"Could not find agent '{agent_name}' in project '{project_name}'."
        )
    return info


# ---------------------------------------------------------------------------
# Run capture (called from capture_run node — recording is active)
# ---------------------------------------------------------------------------

def run_agent_and_collect_events(
    page: Page,
    project_name: str,
    agent_name: str,
    run_inputs: list[dict] | None = None,
    hitl_responses: list[dict] | None = None,
    completion_texts: list[str] | None = None,
) -> list[dict]:
    """Navigate to the agent workspace, fill the run form, start the run,
    handle any mid-run HITL prompts, and return the collected event list.

    run_inputs       — pre-run form actions (click tabs, fill fields, submit)
    hitl_responses   — mid-run prompts to click through automatically
    completion_texts — page-text phrases that signal the run is done;
                       falls back to a generic "completed" check if empty
    """
    navigate_to_agent_workspace(page, project_name, agent_name)

    if run_inputs:
        _fill_run_inputs(page, run_inputs)

    _start_run(page, run_inputs)

    _wait_for_completion(page, hitl_responses or [], completion_texts or [])

    return _collect_events(page)


def _fill_run_inputs(page: Page, run_inputs: list[dict]) -> None:
    """Fill the workspace form fields from the agent's RUN_INPUTS config.

    Supported field_type values:
      "click"  — click a selector (e.g. a tab button) before filling inputs
      "fill"   — type into an input/textarea using pressSequentially so that
                 React's onChange fires per keystroke and enables the submit btn
      "select" — choose a <select> option by value
      "submit" — handled by _start_run(); skipped here
    """
    for field in run_inputs:
        ftype = field.get("field_type", "fill")

        if ftype == "submit":
            continue  # handled by _start_run()

        if ftype == "click":
            sel = field.get("selector", "")
            if sel:
                page.locator(sel).first.click()
                time.sleep(0.5)  # let the tab switch animate
            continue

        sel   = field.get("selector", "input")
        nth   = field.get("nth", 0)
        value = field.get("value", "")

        if not value:
            continue

        locator = page.locator(sel).nth(nth)
        if ftype == "select":
            locator.select_option(value)
        else:
            locator.click()  # focus the field first
            locator.press_sequentially(value, delay=30)  # fire onChange per keystroke


def _start_run(page: Page, run_inputs: list[dict] | None) -> None:
    """Click the submit button that starts the agent run.

    The button starts disabled and becomes enabled only after React processes
    the form-field changes.  We wait up to 10 s for it to be enabled before
    clicking; if it's still disabled we fall back to a JavaScript click so the
    recording can proceed even under slow platform conditions.
    """
    submit_text = None
    if run_inputs:
        for field in run_inputs:
            if field.get("field_type") == "submit":
                submit_text = field.get("value", "")
                break

    candidates = [submit_text] if submit_text else ["Run", "Start", "Submit", "Execute", "Triage Defect"]

    for text in candidates:
        if not text:
            continue
        btn = page.locator(f"button:has-text('{text}')")
        if btn.count() == 0:
            continue

        # Wait for React to enable the button after form validation.
        try:
            btn.wait_for(state="enabled", timeout=10_000)
        except Exception:
            # Still disabled — force-click via JS as a last resort.
            page.evaluate(
                "text => { const b = [...document.querySelectorAll('button')]"
                ".find(b => b.innerText.includes(text)); if (b) b.click(); }",
                text,
            )
            time.sleep(_SUBMIT_WAIT)
            return

        btn.click()
        break

    time.sleep(_SUBMIT_WAIT)


def _wait_for_completion(
    page: Page,
    hitl_responses: list[dict],
    completion_texts: list[str] | None = None,
) -> None:
    """Poll until the agent run completes, handling mid-run HITL prompts along the way.

    Run-started detection uses multiple signals because the status badge wording
    varies (e.g. "Running", "Fetching defect", "Extracting identifiers").
    After 30 s we stop requiring a start signal to guard against missed text.

    Completion is detected when any phrase from `completion_texts` (or the
    generic "completed") appears in the page text after the run has started.
    """
    _DONE_PHRASES = [p.lower() for p in (completion_texts or [])] or ["completed"]

    # Phrases that indicate the agent is actively running.
    _START_SIGNALS = [
        "running", "fetching defect", "extracting identifiers",
        "searching logs", "finding similar", "root cause", "identifying owner",
    ]

    deadline       = time.time() + _RUN_TIMEOUT
    start_deadline = time.time() + 30   # after 30 s assume run started regardless
    run_started    = False
    responded      = set()

    while time.time() < deadline:
        try:
            # page.evaluate is more reliable than inner_text for dynamic React pages.
            page_text = page.evaluate("() => document.body.innerText.toLowerCase()")
        except Exception:
            time.sleep(_POLL_INTERVAL)
            continue

        # Detect run in progress.
        if not run_started:
            if any(s in page_text for s in _START_SIGNALS) or time.time() > start_deadline:
                run_started = True

        # Check for completion.
        if run_started and any(phrase in page_text for phrase in _DONE_PHRASES):
            return

        # Handle mid-run HITL prompts.
        if hitl_responses:
            _handle_hitl(page, hitl_responses, responded, page_text)

        time.sleep(_POLL_INTERVAL)

    raise RuntimeError(
        f"Agent run did not complete within {_RUN_TIMEOUT}s. "
        "Check the platform for errors or increase _RUN_TIMEOUT."
    )


def _handle_hitl(
    page: Page,
    hitl_responses: list[dict],
    responded: set,
    page_text: str | None = None,
) -> None:
    """Click the matching HITL option when an 'INPUT NEEDED' prompt is visible.

    On this platform HITL prompts appear as 'INPUT NEEDED' boxes in the left
    conversation panel.  Responses are element clicks — no text typing.

    response_type in the config controls what element is clicked:
      "button" (default) — <button> whose text contains `response`
      "text"             — first element of any tag containing `response`
                           (used for assignee list picks that are not <button>s)
    """
    if page_text is None:
        try:
            page_text = page.evaluate("() => document.body.innerText.toLowerCase()")
        except Exception:
            return

    # The platform shows either "INPUT NEEDED" or returns the status badge to
    # "Awaiting Input" when the agent pauses for human input mid-run.
    hitl_visible = "input needed" in page_text or "awaiting input" in page_text
    if not hitl_visible:
        return

    for i, cfg in enumerate(hitl_responses):
        if i in responded:
            continue
        trigger = cfg.get("prompt_contains", "").lower()
        if not trigger or trigger not in page_text:
            continue

        response      = cfg.get("response", "")
        response_type = cfg.get("response_type", "button")

        try:
            if response_type == "text":
                # Assignee-list style: click the first element containing the text,
                # regardless of tag (could be <div>, <li>, <span>, …).
                page.get_by_text(response, exact=False).first.click(timeout=5_000)
            else:
                # Default: click a <button> with matching text.
                page.locator(f"button:has-text('{response}')").first.click(timeout=5_000)

            responded.add(i)
            time.sleep(2)
        except Exception:
            # Element not yet clickable — next poll cycle will retry.
            pass
        break


def _collect_events(page: Page) -> list[dict]:
    """Collect the trace/reasoning events from the workspace after the run."""
    events = page.evaluate("""() => {
        const out = [];
        // Agent reasoning trace steps (shown in AGENT REASONING panel)
        document.querySelectorAll('[class*="trace"], [class*="event"], [class*="step"]').forEach(el => {
            const t = el.innerText ? el.innerText.trim() : '';
            if (t) out.push({type: 'trace', content: t});
        });
        // Fallback: collect all visible text blocks that look like run output
        if (out.length === 0) {
            document.querySelectorAll('p, li, pre, code').forEach(el => {
                const t = el.innerText ? el.innerText.trim() : '';
                if (t.length > 10 && t.length < 2000) out.push({type: 'output', content: t});
            });
        }
        return out;
    }""")
    return events or [{"type": "run", "content": "Agent run completed (no structured events captured)"}]
