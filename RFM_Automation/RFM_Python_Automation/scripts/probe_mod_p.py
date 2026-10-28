"""DOM probe P - style details modal internals (TC-SL-003/004, 2026-10-19).

sl_004 still fails: the Style Number Details modal has NEITHER a "Hide"
NOR a "View" button (probe_mod_o never got the page to load).  The style
page is serving rows right now, so grab the full truth in one shot:

  1. style list -> row 0 -> click its View action
  2. dump: every <button>/<a>/<span class*=toggle> inside the open modal
     (text, class, title), the modal's table headers, first rows
  3. if there is a row-level toggle, click it once and re-dump to see the
     label change (View -> Hide?)

Run:  python scripts/probe_mod_p.py
Out:  artifacts/probe_mod_p.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_p.txt"
LINES: list[str] = []

DUMP_JS = """() => {
  const m = document.querySelector('.modal.in, .modal.show');
  if (!m) return '<no open modal>';
  const actives = [...m.querySelectorAll(
    'button, a, span[class*=toggle], span[class*=view], div[class*=toggle]')]
    .map(b => ({
      tag: b.tagName,
      text: (b.innerText || '').trim().slice(0, 24),
      cls: (b.className || '').toString().slice(0, 50),
      title: (b.title || '').slice(0, 24),
    }));
  const tbl = m.querySelector('table');
  const headers = tbl
    ? [...tbl.querySelectorAll('thead th')].map(h => (h.innerText || '').trim())
    : [];
  const rows = tbl
    ? [...tbl.querySelectorAll('tbody tr')].slice(0, 4).map(
        tr => (tr.innerText || '').replace(/\\n/g, ' | ').slice(0, 140))
    : [];
  return JSON.stringify({actives, headers, rows}, null, 1);
}"""


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\\n".join(LINES), encoding="utf-8")
    print(msg)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.HEADLESS)
        page = browser.new_context(viewport=settings.VIEWPORT,
                                   locale=settings.LOCALE).new_page()
        page.set_default_timeout(settings.TIMEOUT_MS)

        page.goto(settings.BASE_URL + "/en/login",
                  wait_until="domcontentloaded")
        page.locator("#rfid-login-username").fill(settings.LOGIN_EMAIL)
        page.locator("#rfid-login-password").fill(settings.LOGIN_PASSWORD)
        page.locator("button[type=submit]").click()
        page.wait_for_timeout(3000)

        page.goto(settings.BASE_URL + settings.MODULE_PATHS["style_number_list"],
                  wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(6000)
        n = page.locator("table#rfid-export-table tbody tr").count()
        log(f"style rows visible: {n}")
        if not n:
            log("style page dead again - abort")
            browser.close()
            return

        row = page.locator("table#rfid-export-table tbody tr").first
        log(f"row0 buttons: {row.locator('button').all_inner_texts()}")
        view = row.get_by_role("button", name="View").first
        view.click()
        page.wait_for_timeout(1500)
        log("=== modal after View ===")
        log(page.evaluate(DUMP_JS))

        # try clicking whatever toggle-like element exists
        toggle = page.locator(
            ".modal.in .rfid-mother-size-toggle, "
            ".modal.in [class*=size-toggle], .modal.in [class*=child-toggle]")
        log(f"toggle candidates: {toggle.count()}")
        if toggle.count():
            log(f"toggle text before: {toggle.first.inner_text()!r}")
            toggle.first.click()
            page.wait_for_timeout(1200)
            log("=== modal after toggle click ===")
            log(page.evaluate(DUMP_JS))

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
