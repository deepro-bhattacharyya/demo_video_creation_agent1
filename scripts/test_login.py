"""Test login step only — print what's on the page."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright
from app import config

SCRIPTS = Path(__file__).parent


def main():
    print(f"HUB_BASE_URL = {config.HUB_BASE_URL}")
    print(f"HUB_EMAIL    = {config.HUB_EMAIL}")
    print(f"HUB_PASSWORD = {'*' * len(config.HUB_PASSWORD) if config.HUB_PASSWORD else '(empty)'}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        print(f"\nGoing to {config.HUB_BASE_URL}/login ...")
        page.goto(f"{config.HUB_BASE_URL}/login", timeout=30_000)
        time.sleep(3)
        print(f"URL: {page.url}")
        print(f"Title: {page.title()}")

        # Print all inputs
        inputs = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('input')).map(el => ({
                type: el.type, placeholder: el.placeholder,
                id: el.id, name: el.name, value: el.value
            }));
        }""")
        print(f"Inputs: {inputs}")

        # Print all buttons
        buttons = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('button')).map(b => ({
                text: b.innerText.trim().substring(0, 40),
                type: b.type, ariaLabel: b.getAttribute('aria-label') or ''
            }));
        }""")
        print(f"Buttons: {buttons}")

        # Try fill
        try:
            page.fill("input[type='email']", config.HUB_EMAIL, timeout=5_000)
            print("Email filled OK")
        except Exception as e:
            print(f"Email fill failed: {e}")

        try:
            page.fill("input[type='password']", config.HUB_PASSWORD, timeout=5_000)
            print("Password filled OK")
        except Exception as e:
            print(f"Password fill failed: {e}")

        page.screenshot(path=str(SCRIPTS / "test_login_filled.png"))

        try:
            page.click("button:has-text('Sign in')", timeout=5_000)
            print("Sign in clicked")
        except Exception as e:
            print(f"Sign in click failed: {e}")
            # Try alternatives
            for sel in ["button[type='submit']", "button:has-text('Login')", "button:has-text('Log in')"]:
                try:
                    page.click(sel, timeout=3_000)
                    print(f"Clicked {sel!r} instead")
                    break
                except Exception:
                    pass

        time.sleep(6)
        print(f"\nAfter sign-in, URL: {page.url}")
        page.screenshot(path=str(SCRIPTS / "test_login_after.png"))

        if "/login" in page.url:
            print("STILL ON LOGIN PAGE.")
            # Check for error messages
            errors = page.evaluate("""() => {
                const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                const out = []; let n;
                while ((n = w.nextNode())) {
                    const t = (n.textContent || '').trim();
                    if (t.length > 2) out.push(t);
                }
                return out.slice(0, 30);
            }""")
            print("Page text:", errors)
        else:
            print("Login SUCCESS!")

        input("Press Enter to close...")
        ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
