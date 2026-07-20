"""Screenshot the DemoVideoBot UI (form + progress views) for visual QA.

Mocks the backend API so the progress view can be reached without a live run.
Run with the dev server up on :5173:
    python scripts/screenshot_ui.py
"""

import os
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "images")
os.makedirs(OUT, exist_ok=True)

STATUS_BODY = (
    '{"thread_id":"test","status":"running",'
    '"completed_steps":["select_agent","capture_run"],'
    '"current_node":"generate_script"}'
)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 720, "height": 1000})

    # ── Form view ──
    page.goto("http://localhost:5173", wait_until="networkidle")
    page.wait_for_selector("form.card")
    page.screenshot(path=os.path.join(OUT, "ui_form.png"))
    print("saved ui_form.png")

    # ── Standalone toggle variant (shows segmented control active state) ──
    page.get_by_text("Standalone Folder").click()
    page.wait_for_timeout(200)
    page.screenshot(path=os.path.join(OUT, "ui_form_standalone.png"))
    print("saved ui_form_standalone.png")

    # ── Progress view (mock the API) ──
    page.route("**/videos", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body='{"thread_id":"test","status":"running"}'))
    page.route("**/videos/*/status", lambda route: route.fulfill(
        status=200, content_type="application/json", body=STATUS_BODY))

    # Reload to reset to form, fill hub fields, start.
    page.goto("http://localhost:5173", wait_until="networkidle")
    page.get_by_placeholder("e.g. Dev test project").fill("Dev test project")
    page.get_by_placeholder("e.g. Defect Triage (CrewAI)").fill("Defect Triage (CrewAI)")
    page.get_by_role("button", name="Start Pipeline").click()

    page.wait_for_selector(".progress-card")
    # App polls every 5 s; wait for the first tick so ticks/spinner reflect state.
    page.wait_for_selector(".step-check", timeout=8000)
    page.wait_for_timeout(300)
    page.screenshot(path=os.path.join(OUT, "ui_progress.png"))
    print("saved ui_progress.png")

    browser.close()
