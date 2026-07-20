"""Explore the workspace page for defect-triaging-crewai to map selectors."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright
from app import config

SCRIPTS = Path(__file__).parent


def shot(page, name):
    p = str(SCRIPTS / name)
    page.screenshot(path=p, full_page=False)
    print(f"[screenshot] {name}  url={page.url}")


def is_logged_in(page):
    for text in ["Agent Builder", "Review Queue", "Projects"]:
        if page.locator(f"text={text!r}").count() > 0:
            return True
    return "/login" not in page.url


def dump_buttons_and_links(page, label=""):
    info = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('button').forEach((b, i) => results.push({
            kind: 'button', index: i,
            text: b.innerText.trim().substring(0, 60),
            ariaLabel: b.getAttribute('aria-label') || '',
            role: b.getAttribute('role') || '',
            disabled: b.disabled,
            className: b.className.substring(0, 100)
        }));
        document.querySelectorAll('a').forEach((a, i) => results.push({
            kind: 'a', index: i,
            text: a.innerText.trim().substring(0, 60),
            href: a.getAttribute('href') || '',
            className: a.className.substring(0, 100)
        }));
        return results;
    }""")
    print(f"\n-- Buttons + links {label} --")
    for el in info:
        if el['kind'] == 'button':
            print(f"  [BTN:{el['index']}] text={el['text']!r} aria={el['ariaLabel']!r} disabled={el['disabled']}")
        else:
            if el['text']:
                print(f"  [A:{el['index']}] text={el['text']!r} href={el['href']!r}")
    return info


def dump_text(page, label=""):
    texts = page.evaluate("""() => {
        const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        const out = []; let n;
        while ((n = w.nextNode())) {
            const t = (n.textContent || '').trim();
            if (t.length > 2 && t.length < 120) out.push(t);
        }
        return [...new Set(out)].slice(0, 80);
    }""")
    print(f"\n-- Text {label} --")
    print(texts[:40])
    return texts


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        # ── Login ──────────────────────────────────────────────────────────
        page.goto(f"{config.HUB_BASE_URL}/login", timeout=30_000)
        time.sleep(2)
        page.fill("input[type='email']", config.HUB_EMAIL)
        page.fill("input[type='password']", config.HUB_PASSWORD)
        page.click("button:has-text('Sign in')")
        time.sleep(8)
        if not is_logged_in(page):
            print("ERROR: Not logged in."); ctx.close(); browser.close(); return
        print(f"Logged in! URL: {page.url}")

        # ── Find HCM Project ID ──────────────────────────────────────────────
        page.goto(f"{config.HUB_BASE_URL}/projects", timeout=15_000)
        time.sleep(4)

        # Click HCM Project card using JS (cards are <div> elements, not <button>)
        navigated = page.evaluate("""() => {
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walker.nextNode())) {
                const txt = (node.textContent || '').trim();
                if (txt.toLowerCase() === 'hcm project') {
                    let el = node.parentElement;
                    for (let i = 0; i < 10; i++) {
                        if (!el) break;
                        const cls = el.className || '';
                        if (cls.includes('rounded') || cls.includes('transition')) {
                            el.click();
                            return {clicked: true, tag: el.tagName, cls: cls.substring(0, 80)};
                        }
                        el = el.parentElement;
                    }
                }
            }
            return {clicked: false};
        }""")
        print(f"HCM click result: {navigated}")
        time.sleep(4)
        print(f"After HCM click URL: {page.url}")
        shot(page, "nav_hcm_project.png")

        # Get HCM project ID from URL
        hcm_project_id = None
        if '/projects/' in page.url:
            hcm_project_id = page.url.split('/projects/')[-1].split('/')[0].split('?')[0]
            print(f"HCM Project ID: {hcm_project_id}")

        # Dump agents in HCM project
        agents_info = dump_buttons_and_links(page, "in HCM Project")
        dump_text(page, "in HCM Project")

        # Find defect-triaging-crewai link
        defect_href = None
        for el in agents_info:
            href = el.get('href', '')
            if 'defect-triaging-crewai' in href:
                defect_href = href
                print(f"\nFound Defect Triaging CrewAI link: {href!r}")
                break

        if not defect_href:
            # Check dev-project-001 if HCM didn't work
            print("Not found in HCM, checking dev-project-001...")
            defect_href = f"/workspace?agent=defect-triaging-crewai&project=dev-project-001"

        # ── Navigate to workspace ─────────────────────────────────────────
        print(f"\nNavigating to workspace: {defect_href}")
        page.goto(f"{config.HUB_BASE_URL}{defect_href}", timeout=15_000)
        time.sleep(5)
        shot(page, "nav_workspace.png")
        print(f"Workspace URL: {page.url}")

        # Map everything on workspace page
        dump_buttons_and_links(page, "on workspace page")
        dump_text(page, "on workspace page")

        # Get main area HTML
        main_html = page.evaluate("""() => {
            const main = document.querySelector('main') || document.body;
            return main.innerHTML.substring(0, 8000);
        }""")
        print(f"\n=== WORKSPACE HTML ===\n{main_html[:4000]}\n=== END ===")

        # ── Click Run on workspace and observe HITL ────────────────────────
        # Look for a Run button (different from the listing page's Run link)
        run_button = None
        btns = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('button')).map((b, i) => ({
                i, text: b.innerText.trim(), aria: b.getAttribute('aria-label') || '',
                disabled: b.disabled, cls: b.className.substring(0, 80)
            }));
        }""")
        for b in btns:
            t = b['text'].lower()
            if 'run' in t or 'start' in t or 'execute' in t or 'launch' in t:
                print(f"\nRun button candidate: [{b['i']}] text={b['text']!r} aria={b['aria']!r}")
                if not run_button:
                    run_button = b['i']

        if run_button is not None:
            print(f"\nClicking run button [{run_button}]...")
            page.locator("button").nth(run_button).click()
            time.sleep(3)
            shot(page, "nav_workspace_running.png")
            print(f"After run click URL: {page.url}")
            dump_buttons_and_links(page, "AFTER clicking run")
            dump_text(page, "AFTER clicking run")

            # Watch for HITL prompts for 30s
            print("\nWatching for HITL prompts (30s)...")
            for i in range(15):
                time.sleep(2)
                page_text = page.evaluate("""() => {
                    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                    const out = []; let n;
                    while ((n = w.nextNode())) {
                        const t = (n.textContent || '').trim();
                        if (t.length > 3 && t.length < 120) out.push(t);
                    }
                    return [...new Set(out)].slice(0, 30);
                }""")
                print(f"  [{i*2}s] {page_text[:10]}")
                # Check for input fields (HITL indicator)
                inputs = page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('input, textarea')).map(el => ({
                        type: el.type, placeholder: el.placeholder,
                        visible: el.offsetParent !== null
                    }));
                }""")
                if any(inp['visible'] for inp in inputs):
                    print(f"  HITL INPUT VISIBLE: {inputs}")
                    shot(page, f"nav_hitl_{i}.png")
                    break
        else:
            print("No run button found! Dumping full workspace HTML for inspection...")
            print(main_html)

        time.sleep(3)
        ctx.close()
        browser.close()
        print("\nDone.")


if __name__ == "__main__":
    main()
