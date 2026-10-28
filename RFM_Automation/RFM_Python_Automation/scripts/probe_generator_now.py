"""Diff the live Generator page against the DOM verified on 2026-10-09.

Dumps tabs, buttons, inputs/selects/labels, headings and the flow-relevant
ids so any NEW scenario control (tab, field, modal, helper text) shows up.

Run:  python scripts/probe_generator_now.py
Out:  artifacts/probe_generator_now.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_generator_now.txt"
LINES: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")


DUMP_JS = """() => {
    const vis = el => !!(el.offsetWidth || el.offsetHeight);
    const out = {
        url: location.href,
        headings: [...document.querySelectorAll('h1,h2,h3,h4,h5,legend')]
            .filter(vis).map(h => h.innerText.trim()).filter(Boolean).slice(0, 40),
        buttons: [...document.querySelectorAll('button')].filter(vis)
            .map(b => (b.innerText || '').trim() || b.id || b.title || '?'),
        inputs: [...document.querySelectorAll('input,select,textarea')].filter(vis)
            .map(i => ({tag: i.tagName, id: i.id, type: i.type,
                        name: i.name, ph: i.placeholder,
                        aria: i.getAttribute('aria-label'),
                        cls: (i.className || '').slice(0, 40)})),
        labels: [...document.querySelectorAll('label,small,helper')].filter(vis)
            .map(l => (l.innerText || '').trim()).filter(t => t && t.length < 60)
            .slice(0, 60),
        helpers: [...document.querySelectorAll('.rfid-gen-help, .rfid-gen-field small,'
                    + ' .rfid-gen-note, [class*=help], [class*=hint]')].filter(vis)
            .map(h => (h.innerText || '').trim()).filter(Boolean).slice(0, 30),
        tables: [...document.querySelectorAll('table')].filter(vis)
            .map(t => ({cls: (t.className || '').slice(0, 40),
                        head: [...t.querySelectorAll('thead th')]
                            .map(th => th.innerText.trim())})),
        tabs: [...document.querySelectorAll('.rfid-gen-mode-btn, [role=tab]')]
            .map(t => (t.innerText || '').trim()),
        overlays: [...document.querySelectorAll('.modal, [role=dialog]')].filter(vis)
            .map(m => (m.innerText || '').trim().slice(0, 100)),
    };
    return out;
}"""


def dump(page, label: str) -> None:
    info = page.evaluate(DUMP_JS)
    log(f"===== {label} =====")
    for key, value in info.items():
        log(f"  {key}: {value}")


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
        page.wait_for_timeout(4000)
        log(f"login -> {page.url}")

        dump(page, "Item Code tab (default)")

        # switch to the Others tab and dump again
        others = page.locator(".rfid-gen-mode-btn", has_text="Others")
        if others.count():
            others.first.click()
            page.wait_for_timeout(800)
            dump(page, "Others tab")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
