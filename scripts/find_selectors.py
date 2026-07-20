"""Diagnostic script — find the real login-form selectors on AgenticQEAHub.

Run this once with a headed browser so you can see what loads, and it will:
  1. Navigate to the login page
  2. Print all input elements and their attributes
  3. Save a screenshot to scripts/login_page.png

Usage:
    python scripts/find_selectors.py
"""

import sys
from pathlib import Path

# Make sure app/ is importable from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright
from app import config


def main():
    print(f"Navigating to: {config.HUB_BASE_URL}/marketplace")
    print("-" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)   # headed so you can see what's happening
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        page.goto(f"{config.HUB_BASE_URL}/marketplace", timeout=30_000)
        page.wait_for_load_state("networkidle", timeout=15_000)

        # Save a screenshot
        screenshot_path = Path(__file__).parent / "login_page.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"Screenshot saved -> {screenshot_path}")

        # Print the page title and URL
        print(f"Page title : {page.title()}")
        print(f"Current URL: {page.url}")
        print()

        # Find all input elements and their attributes
        print("=== INPUT ELEMENTS ===")
        inputs = page.query_selector_all("input")
        if not inputs:
            print("  (none found)")
        for el in inputs:
            attrs = {
                "id":          el.get_attribute("id"),
                "name":        el.get_attribute("name"),
                "type":        el.get_attribute("type"),
                "placeholder": el.get_attribute("placeholder"),
                "class":       el.get_attribute("class"),
                "data-testid": el.get_attribute("data-testid"),
                "aria-label":  el.get_attribute("aria-label"),
            }
            attrs = {k: v for k, v in attrs.items() if v}
            print(f"  input: {attrs}")

        # Find all buttons
        print()
        print("=== BUTTONS ===")
        buttons = page.query_selector_all("button")
        if not buttons:
            print("  (none found)")
        for btn in buttons:
            attrs = {
                "id":          btn.get_attribute("id"),
                "type":        btn.get_attribute("type"),
                "class":       btn.get_attribute("class"),
                "data-testid": btn.get_attribute("data-testid"),
                "aria-label":  btn.get_attribute("aria-label"),
                "text":        btn.inner_text().strip()[:60],
            }
            attrs = {k: v for k, v in attrs.items() if v}
            print(f"  button: {attrs}")

        print()
        print("=== FORMS ===")
        forms = page.query_selector_all("form")
        if not forms:
            print("  (none found — login may not use a <form> element)")
        for form in forms:
            print(f"  form id={form.get_attribute('id')} class={form.get_attribute('class')}")

        input("Press Enter to close the browser...")
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
