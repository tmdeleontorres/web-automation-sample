"""DOM probe H - Rewrite old-EPC resolution in RFID List (TC-RW-003).

The CSV says: searching the old (Before) EPC in RFID List should display the
new, current RFID record. The test found only '-' placeholders. This probe:
  1. reads row 0's BEFORE/CURRENT EPCs from Rewrite RFIDs,
  2. searches RFID List for the OLD EPC  -> dumps headers/rows/count,
  3. searches RFID List for the NEW EPC  -> dumps headers/rows/count,
  4. checks whether an "Old"/"Previous"/"Rewrite" column exists at all.
This tells us whether the app can resolve old->new (testable) or whether the
old EPC is simply not indexed (a genuine finding to document).

Run:  python scripts/probe_mod_h.py
Out:  artifacts/probe_mod_h.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_h.txt"
LINES: list[str] = []

ROWS_JS = """() => {
  const t = document.querySelector('table.rfid-export-table')
         || document.querySelector('table');
  if (!t) return null;
  const heads = [...t.querySelectorAll('thead th')].map(h =>
    h.innerText.trim().replace(/\\s+/g, ' '));
  const rows = [...t.querySelectorAll('tbody tr:not(.rfid-gen-empty-row)')]
    .slice(0, 5)
    .map(tr => [...tr.querySelectorAll('td')].map(td =>
      td.innerText.trim().replace(/\\s+/g, ' ')));
  const total = t.querySelectorAll(
    'tbody tr:not(.rfid-gen-empty-row)').length;
  return {heads, rows, total};
}"""


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


def search(page, term):
    box = page.locator("div[id$='_filter'] input[type=search], "
                       "table input[type=search], "
                       "input[placeholder*='Quick' i]").first
    box.click()
    box.fill(term)
    box.press("Enter")
    page.wait_for_timeout(900)
    return page.evaluate(ROWS_JS)


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

        # BEFORE / CURRENT from Rewrite RFIDs
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["rewrite_rfids"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        pair = page.evaluate(
            """() => {
            const t = document.querySelector('table.rfid-export-table')
                   || document.querySelector('table');
            const heads = [...t.querySelectorAll('thead th')].map(h =>
              h.innerText.trim());
            const idx = heads.findIndex(h => /rewrite/i.test(h));
            const tr = t.querySelector(
              'tbody tr:not(.rfid-gen-empty-row)');
            if (!tr || idx < 0) return null;
            return tr.querySelectorAll('td')[idx].innerText;
        }""")
        log(f"  rewrite cell={pair!r}")
        tokens = [t.strip() for t in (pair or "").splitlines() if t.strip()]
        old = new = ""
        for i, tok in enumerate(tokens):
            if tok.upper() == "BEFORE" and i + 1 < len(tokens):
                old = tokens[i + 1]
            elif tok.upper() == "CURRENT" and i + 1 < len(tokens):
                new = tokens[i + 1]
        log(f"  old={old!r} new={new!r}")

        # RFID List
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["rfid_list"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        baseline = page.evaluate(ROWS_JS)
        log(f"  RFID List headers={baseline['heads'] if baseline else None}")
        log(f"  RFID List baseline rows={baseline['total'] if baseline else '?'}")

        if old:
            res = search(page, old)
            log(f"  search OLD -> total={res['total']}")
            for r in res["rows"][:3]:
                log(f"      {r}")
        if new:
            res = search(page, new)
            log(f"  search NEW -> total={res['total']}")
            for r in res["rows"][:3]:
                log(f"      {r}")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
