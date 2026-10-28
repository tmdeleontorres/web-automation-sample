"""DOM probe O - empty-search row markup + style details modal (2026-10-19).

1) TC-TBL-005 (rg_002b) now reads row_count() == 1 after filtering to zero:
   the DataTables empty-state row is NOT excluded, so its text differs from
   "No matching records found".  Dump the remaining <tr> markup on Recent
   after an impossible search to learn the exact text/class.

2) TC-SL-004: the style page loaded during the latest pytest run but the
   details modal had no "Hide" button.  Style page is flaky today (DataTables
   sometimes never initialises) -> retry navigation up to 4 times, then open
   row 0's View and dump every button/toggle in the modal.

Run:  python scripts/probe_mod_o.py
Out:  artifacts/probe_mod_o.txt
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_o.txt"
LINES: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


def wait_rows(page, tries: int = 4, settle_s: int = 12) -> bool:
    """Navigate + wait for rows; style page is flaky today -> retry."""
    for attempt in range(1, tries + 1):
        try:
            page.goto(settings.BASE_URL + page_path_from_url(page),
                      wait_until="domcontentloaded", timeout=45000)
        except Exception as exc:
            log(f"    goto attempt {attempt} failed: {type(exc).__name__}")
        deadline = time.monotonic() + settle_s
        while time.monotonic() < deadline:
            page.wait_for_timeout(500)
            n = page.evaluate("""() => {
              const t = document.querySelector('table.rfid-export-table');
              return t ? t.querySelectorAll(
                'tbody tr:not(.rfid-gen-empty-row)').length : -1;
            }""")
            if n and n > 0:
                log(f"    rows appeared on attempt {attempt} ({n} rows)")
                return True
        log(f"    attempt {attempt}: no rows in {settle_s}s")
    return False


def page_path_from_url(page) -> str:
    return page.url.replace(settings.BASE_URL, "")


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
        page.wait_for_timeout(3500)

        # ------------------------------------------------------------------ #
        log("=== A. Recent: empty-state row markup ===")
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["recent_generated"],
                  wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3500)
        box = page.locator(
            "input[type=search][placeholder*='Quick search']").first
        box.click()
        box.fill("zzz-no-such-record-zzz")
        box.press("Enter")
        page.wait_for_timeout(4000)          # > measured 1.6 s latency
        html = page.evaluate("""() => {
          const t = document.querySelector('table#rfid-export-table')
                 || document.querySelector('table.rfid-export-table');
          if (!t) return '<no table>';
          const trs = [...t.querySelectorAll('tbody tr')];
          return trs.map(tr => tr.outerHTML.slice(0, 400)).join('\\n---\\n');
        }""")
        log(f"  tbody rows after impossible search:\\n{html}")
        box.click()
        box.fill("")
        box.press("Enter")
        page.wait_for_timeout(2500)

        # ------------------------------------------------------------------ #
        log("=== B. Style Number List: details modal structure ===")
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["style_number_list"],
                  wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)
        if wait_rows(page):
            # row 0 action buttons
            acts = page.evaluate("""() => {
              const t = document.querySelector('table#rfid-export-table');
              const tr = t.querySelector('tbody tr');
              if (!tr) return [];
              return [...tr.querySelectorAll('button, a')]
                .map(b => ({tag: b.tagName,
                            text: (b.innerText || '').trim().slice(0, 20),
                            cls: (b.className || '').slice(0, 40)}));
            }""")
            log(f"  row0 action elements: {acts}")
            view = page.locator(
                "table#rfid-export-table tbody tr").first.get_by_role(
                "button", name="View").first
            if not view.count():
                view = page.locator(
                    "table#rfid-export-table tbody tr").first.get_by_text(
                    "View", exact=True).first
            view.click()
            page.wait_for_timeout(1500)
            modal_html = page.evaluate("""() => {
              const m = document.querySelector('.modal.in, .modal.show');
              if (!m) return '<no modal>';
              const btns = [...m.querySelectorAll('button, a')]
                .map(b => ((b.innerText || '').trim() || b.className)
                          .slice(0, 30));
              const tbl = m.querySelector('table');
              const head = tbl
                ? [...tbl.querySelectorAll('thead th')]
                    .map(h => (h.innerText || '').trim())
                : [];
              return JSON.stringify({buttons: btns, headers: head});
            }""")
            log(f"  modal buttons/headers: {modal_html}")
            first_rows = page.evaluate("""() => {
              const m = document.querySelector('.modal.in, .modal.show');
              if (!m) return '';
              const trs = [...m.querySelectorAll('tbody tr')].slice(0, 4);
              return trs.map(tr => (tr.innerText || '')
                .replace(/\\n/g, ' | ').slice(0, 120)).join('\\n');
            }""")
            log(f"  modal first rows:\\n{first_rows}")
        else:
            log("  style page never showed rows - cannot inspect modal")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
