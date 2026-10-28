"""DOM probe H2 - Rewrite old-EPC resolution in RFID List (TC-RW-003).

The CSV says: searching the old (Before) EPC in RFID List should display the
new, current RFID record. Probe H1 failed on load timing; this version waits
for real rows before reading/searching.

Steps:
  1. Rewrite RFIDs: wait for rows, read row 0 BEFORE/CURRENT EPCs.
  2. RFID List: wait for baseline rows, dump headers.
  3. Quick-search OLD EPC -> dump count + up to 3 rows.
  4. Quick-search NEW EPC -> dump count + up to 3 rows.
  5. Quick-search a unique fragment of the OLD EPC (first 8 chars).

Run:  python scripts/probe_mod_h2.py
Out:  artifacts/probe_mod_h2.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_h2.txt"
LINES: list[str] = []

ROWS_JS = """() => {
  const tables = [...document.querySelectorAll('table')]
    .filter(t => !!(t.offsetWidth || t.offsetHeight));
  const t = tables.find(x =>
    x.querySelector('tbody tr:not(.rfid-gen-empty-row)')) || tables[0];
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


def wait_rows(page, min_rows: int = 1, timeout: int = 20000) -> bool:
    try:
        page.wait_for_function(
            """min => [...document.querySelectorAll(
                 'table tbody tr:not(.rfid-gen-empty-row)')]
                 .filter(t => !!(t.offsetWidth || t.offsetHeight))
                 .length >= min""", arg=min_rows, timeout=timeout)
        return True
    except Exception:
        return False


def search(page, term: str):
    box = page.locator(
        "div[id$='_filter'] input[type=search], "
        "input[placeholder*='Quick' i]").first
    box.click()
    box.fill(term)
    box.press("Enter")
    page.wait_for_timeout(1200)
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

        # 1. BEFORE / CURRENT from Rewrite RFIDs
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["rewrite_rfids"],
                  wait_until="domcontentloaded")
        ready = wait_rows(page)
        log(f"  rewrite rows ready={ready}")
        pair = page.evaluate(
            """() => {
            const tables = [...document.querySelectorAll('table')]
              .filter(t => !!(t.offsetWidth || t.offsetHeight));
            const t = tables.find(x =>
              x.querySelector('tbody tr:not(.rfid-gen-empty-row)'));
            if (!t) return null;
            const heads = [...t.querySelectorAll('thead th')]
              .map(h => h.innerText.trim());
            const idx = heads.findIndex(h => /rewrite/i.test(h));
            const tr = t.querySelector('tbody tr:not(.rfid-gen-empty-row)');
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

        # 2. RFID List baseline
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["rfid_list"],
                  wait_until="domcontentloaded")
        ready = wait_rows(page, min_rows=1, timeout=25000)
        baseline = page.evaluate(ROWS_JS)
        log(f"  rfid list ready={ready} baseline rows={baseline['total']}")
        log(f"  headers={baseline['heads']}")

        # 3. search OLD
        if old:
            res = search(page, old)
            log(f"  search OLD full -> total={res['total']}")
            for r in res["rows"][:3]:
                log(f"      {r}")
            res = search(page, old[:8])
            log(f"  search OLD first8 -> total={res['total']}")
            for r in res["rows"][:3]:
                log(f"      {r}")

        # 4. search NEW
        if new:
            res = search(page, new)
            log(f"  search NEW full -> total={res['total']}")
            for r in res["rows"][:3]:
                log(f"      {r}")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
