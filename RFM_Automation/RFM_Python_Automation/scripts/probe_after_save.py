"""Selector pass helper #4 - after-save timeline, post-save export modal,
generator counters and the Generated Series table container.

Run:  python scripts/probe_after_save.py
Out:  artifacts/probe_after_save.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils import test_data as data  # noqa: E402

OUT = Path(settings.ARTIFACTS_DIR)
OUT.mkdir(parents=True, exist_ok=True)
OUTFILE = OUT / "probe_after_save.txt"
LINES: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")


def visible_modals(page):
    return page.evaluate("""() => [...document.querySelectorAll('.modal, [role=dialog]')]
        .filter(m => m.offsetWidth || m.offsetHeight)
        .map(m => ({id: m.id, text: (m.innerText || '').trim().slice(0, 220),
                    buttons: [...m.querySelectorAll('button')]
                        .filter(b => b.offsetWidth || b.offsetHeight)
                        .map(b => ((b.innerText || '').trim() || b.id))}))""")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.HEADLESS)
        page = browser.new_context(viewport=settings.VIEWPORT,
                                   locale=settings.LOCALE).new_page()
        page.set_default_timeout(settings.TIMEOUT_MS)

        page.goto(settings.BASE_URL + "/en/login", wait_until="domcontentloaded")
        page.locator("#rfid-login-username").fill(settings.LOGIN_EMAIL)
        page.locator("#rfid-login-password").fill(settings.LOGIN_PASSWORD)
        page.locator("button[type=submit]").click()
        page.wait_for_timeout(3500)
        log(f"login -> {page.url}")

        # ---- counters before generating ---------------------------------- #
        counters = page.evaluate("""() => [...document.querySelectorAll('*')]
            .filter(el => el.children.length === 0 && /^Total\\s/i.test((el.innerText || '').trim()))
            .map(el => ({tag: el.tagName, cls: (el.className || '').toString().slice(0, 40),
                         text: el.innerText.trim(),
                         parent: (el.parentElement || {}).innerText
                           ? el.parentElement.innerText.trim().slice(0, 60) : ''}))""")
        log(f"counter-ish elements: {counters}")

        # ---- table container ---------------------------------------------- #
        chain = page.evaluate("""() => {
            let el = document.querySelector('table');
            const out = [];
            while (el && out.length < 6) {
                out.push({tag: el.tagName, id: el.id, cls: (el.className || '').toString().slice(0, 50)});
                el = el.parentElement;
            }
            return out;
        }""")
        log(f"first table ancestors: {chain}")

        # ---- generate + continue ------------------------------------------ #
        page.locator("#rfid-gtin").fill(data.ITEM_CODE_ADDED)
        page.locator("#rfid-serial-start").fill("10300")
        page.locator("#rfid-quantity").fill("2")
        page.get_by_role("button", name="Generate Series").click()
        page.wait_for_timeout(2000)
        page.locator("#rfid-confirm-save:visible").first.click()
        page.wait_for_timeout(1200)
        log(f"pending rows now: {page.locator('table').first.locator('tbody tr').count()}")

        counters = page.evaluate("""() => [...document.querySelectorAll('*')]
            .filter(el => el.children.length === 0 && /^Total\\s/i.test((el.innerText || '').trim()))
            .map(el => ({text: el.innerText.trim(),
                         parent: el.parentElement.innerText.trim().slice(0, 50)}))""")
        log(f"counters after generate: {counters}")

        # ---- save + poll the after-save timeline --------------------------- #
        page.locator("#rfid-save-generated").click()
        page.wait_for_timeout(1200)
        log(f"save summary modal: {visible_modals(page)}")
        page.locator("#rfid-confirm-save:visible").first.click()

        for second in range(1, 11):
            page.wait_for_timeout(1000)
            modals = visible_modals(page)
            if modals:
                log(f"t+{second}s modals: {modals}")
                break
        else:
            log("t+10s: no modal appeared")

        # keep polling to catch anything that follows
        for second in range(11, 16):
            page.wait_for_timeout(1000)
            modals = visible_modals(page)
            log(f"t+{second}s modals: {modals}")

        detail = page.evaluate("""() => {
            const m = document.querySelector('#rfid-post-save-export-modal');
            if (!m) return null;
            return {id: m.id, visible: !!(m.offsetWidth || m.offsetHeight),
                    text: (m.innerText || '').trim().slice(0, 400),
                    closers: [...m.querySelectorAll('button, a')]
                        .map(b => ({text: (b.innerText || '').trim(), id: b.id,
                                    dismiss: b.getAttribute('data-dismiss') || '',
                                    cls: (b.className || '').slice(0, 40)}))};
        }""")
        log(f"post-save export modal detail: {detail}")

        success = page.evaluate("""() => {
            const el = document.querySelector('.rfid-save-success, .toast, [role=alert]');
            return el ? el.innerText.trim().slice(0, 200) : null;
        }""")
        log(f"success element: {success}")
        log(f"page text has 'Saved Successfully': "
            f"{'Saved Successfully' in page.content()}")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
