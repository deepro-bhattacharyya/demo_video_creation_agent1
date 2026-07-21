"""Map: login -> projects -> HCM Project -> Defect Triage (CrewAI) workspace."""

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


def click_project_card(page, project_name):
    """Click the project card div (cursor:pointer) matching project_name."""
    result = page.evaluate("""(name) => {
        const divs = Array.from(document.querySelectorAll('div[style*="cursor: pointer"]'));
        for (const div of divs) {
            if (div.textContent.toLowerCase().includes(name.toLowerCase())) {
                div.click();
                return { found: true, text: div.textContent.trim().substring(0, 60) };
            }
        }
        return { found: false };
    }""", project_name)
    return result


def click_agent_run(page, agent_name):
    """Find the Run link for agent_name and click it. Returns the href."""
    result = page.evaluate("""(name) => {
        // Find all agent name spans
        const spans = Array.from(document.querySelectorAll('span'));
        for (const span of spans) {
            if (span.textContent.trim().toLowerCase().includes(name.toLowerCase())) {
                // Walk up to find row container, then find Run <a> link
                let el = span.parentElement;
                for (let i = 0; i < 8; i++) {
                    if (!el) break;
                    const link = el.querySelector('a[href*="/workspace"]');
                    if (link) {
                        const href = link.getAttribute('href');
                        link.click();
                        return { found: true, href: href };
                    }
                    el = el.parentElement;
                }
            }
        }
        return { found: false };
    }""", agent_name)
    return result


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
            print("ERROR: Not logged in.")
            ctx.close(); browser.close(); return
        print(f"Logged in! URL: {page.url}")

        # ── Projects page ──────────────────────────────────────────────────
        page.goto(f"{config.HUB_BASE_URL}/projects", timeout=15_000)
        time.sleep(4)
        shot(page, "nav_projects.png")
        print(f"Projects URL: {page.url}")

        # ── Click HCM Project card ─────────────────────────────────────────
        print("\nClicking HCM Project card...")
        result = click_project_card(page, "HCM Project")
        print(f"Card click: {result}")
        time.sleep(4)
        shot(page, "nav_hcm_project.png")
        print(f"After click URL: {page.url}")

        # ── List all agents in HCM Project ────────────────────────────────
        links = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a[href*="/workspace"]')).map(a => ({
                text: a.innerText.trim().substring(0, 60),
                href: a.getAttribute('href') || '',
                parentText: a.closest('div')
                    ? a.closest('div').textContent.trim().substring(0, 80)
                    : ''
            }));
        }""")
        print("\n-- Agent Run links in HCM Project --")
        for lnk in links:
            print(f"  href={lnk['href']!r}: parent={lnk['parentText']!r}")

        texts = page.evaluate("""() => {
            const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            const out = []; let n;
            while ((n = w.nextNode())) {
                const t = (n.textContent || '').trim();
                if (t.length > 2 && t.length < 120) out.push(t);
            }
            return [...new Set(out)].slice(0, 60);
        }""")
        print("\n-- Text on HCM Project page --")
        print(texts[:30])

        # ── Click Defect Triage (CrewAI) Run link ─────────────────────────
        print("\nLooking for 'Defect Triage' Run link...")
        defect_link = None
        for lnk in links:
            if "defect" in lnk['href'].lower() and "crewai" in lnk['href'].lower():
                defect_link = lnk
                break
        if not defect_link:
            for lnk in links:
                if "defect" in lnk['href'].lower() or "defect" in lnk['parentText'].lower():
                    defect_link = lnk
                    break

        if defect_link:
            print(f"Found: {defect_link['href']!r}")
            page.goto(f"{config.HUB_BASE_URL}{defect_link['href']}", timeout=30_000)
        else:
            print("Not found via links, trying click_agent_run...")
            res = click_agent_run(page, "Defect Triage")
            print(f"Agent run click: {res}")

        time.sleep(5)
        shot(page, "nav_workspace.png")
        print(f"\nWorkspace URL: {page.url}")

        # ── Inspect workspace ──────────────────────────────────────────────
        main_html = page.evaluate("""() => {
            const main = document.querySelector('main') || document.body;
            return main.innerHTML.substring(0, 10000);
        }""")
        print("\n=== WORKSPACE MAIN HTML ===")
        print(main_html)
        print("=== END ===\n")

        all_btns = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('button')).map((b, i) => ({
                index: i,
                text: b.innerText.trim().substring(0, 80),
                ariaLabel: b.getAttribute('aria-label') || '',
                disabled: b.disabled,
                className: b.className.substring(0, 120),
                id: b.id || ''
            }));
        }""")
        print("\n-- ALL buttons on workspace --")
        for b in all_btns:
            dis = "DISABLED" if b['disabled'] else "enabled"
            print(f"  [{b['index']}] {dis} text={b['text']!r} aria={b['ariaLabel']!r} id={b['id']!r}")
            print(f"         class={b['className']!r}")

        inputs = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('input, textarea, [contenteditable]')).map((el, i) => ({
                index: i,
                tag: el.tagName,
                type: el.getAttribute('type') || '',
                placeholder: el.getAttribute('placeholder') || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                className: el.className.substring(0, 80)
            }));
        }""")
        print("\n-- Inputs/Textareas --")
        for inp in inputs:
            print(f"  [{inp['index']}] <{inp['tag']}> type={inp['type']!r} placeholder={inp['placeholder']!r} aria={inp['ariaLabel']!r}")

        page_texts = page.evaluate("""() => {
            const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            const out = []; let n;
            while ((n = w.nextNode())) {
                const t = (n.textContent || '').trim();
                if (t.length > 2 && t.length < 120) out.push(t);
            }
            return [...new Set(out)].slice(0, 80);
        }""")
        print("\n-- Text on workspace --")
        print(page_texts[:50])

        time.sleep(3)
        ctx.close()
        browser.close()
        print("\nDone.")


if __name__ == "__main__":
    main()
