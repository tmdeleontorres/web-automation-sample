"""DOM probe G - Rewrite Logs modal (exact event labels + Details button).

TC-RW-004 expects "rewrite_rfid" / "rewrite_rfid_sync" and a working
"Details" button. This probe opens Logs on the first row and dumps the raw
EVENT/NOTES cell text plus every visible button, so we can compare the
documented expectation against the real rendering.

Run:  python scripts/probe_mod_g.py
Out:  artifacts/probe_mod_g.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_g.txt"
LINES: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


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

        page.goto(settings.BASE_URL + settings.MODULE_PATHS["rewrite_rfids"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        row = page.locator("table.rfid-export-table tbody tr:not(.rfid-gen-empty-row)").first
        logs_btn = row.locator("button:has-text('Logs')")
        log(f"  Logs buttons in row 0: {logs_btn.count()}")
        if not logs_btn.count():
            browser.close()
            log("DONE")
            return
        logs_btn.click()
        page.wait_for_timeout(1500)

        modal = page.locator(".modal.in:visible, .modal.show:visible").last
        log(f"  modal id={modal.get_attribute('id')}")
        log(f"  modal text=\n    {modal.inner_text()}")

        cells = modal.evaluate(
            """m => [...m.querySelectorAll('tbody tr')].slice(0, 4).map(tr =>
                [...tr.querySelectorAll('td')].map(td =>
                  td.innerText.trim().replace(/\\s+/g, ' ')))""")
        for i, r in enumerate(cells):
            log(f"  log row {i}: {r}")

        btns = modal.evaluate(
            """m => { const vis = e => !!(e.offsetWidth || e.offsetHeight);
                 return [...m.querySelectorAll('button')].filter(vis).map(b => ({
                   id: b.id, cls: (b.className||'').slice(0,45),
                   text: b.innerText.trim().slice(0,25)})); }""")
        log(f"  visible buttons={btns}")

        # Does 'Details' open a nested dialog?
        det = modal.locator("button:has-text('Details')")
        if det.count():
            det.first.click()
            page.wait_for_timeout(1200)
            nested = page.locator(".modal.in:visible, .modal.show:visible").last
            log(f"  after Details -> id={nested.get_attribute('id')}")
            log(f"  after Details -> text=\n    {nested.inner_text()[:600]}")
        else:
            log("  no Details button present")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
