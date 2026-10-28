"""DOM probe L - quick-search wiring (TC-RG-002b, TC-RW-003, TC-RL-001).

Full run 2026-10-19: searching an impossible term in Recent Generated still
left 2 rows, and RFID List searches never changed the row set. This probe
answers: is the DataTables "Search:" input actually wired?

For Recent Generated and RFID List:
  1. list every input[type=search] (id, placeholder, owning div id, visible)
  2. baseline rows + #..._info text (DataTables info line: "Showing x of y")
  3. fill impossible term + Enter -> wait 2s -> info/rows + any ajax request
     fired (url contains 'draw=' or 'search%5Bvalue%5D')
  4. reference path: #rfid-export-keyword + Filter button -> rows
  5. clear again

Also records Style Number List + Transaction List row counts after open
(the full run skipped both with "No styles/transactions available").

Run:  python scripts/probe_mod_l.py
Out:  artifacts/probe_mod_l.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_l.txt"
LINES: list[str] = []

SEARCH_INPUTS_JS = """() => {
  const vis = el => !!(el.offsetWidth || el.offsetHeight);
  return [...document.querySelectorAll('input[type=search]')].map(i => ({
    id: i.id, ph: i.placeholder, value: i.value,
    owner: (i.closest('div[id]') || {}).id || '',
    visible: vis(i),
  }));
}"""

COUNT_JS = """() => {
  const vis = el => !!(el.offsetWidth || el.offsetHeight);
  const tables = [...document.querySelectorAll('table')].filter(vis);
  const t = tables.find(x =>
    x.querySelector('tbody tr:not(.rfid-gen-empty-row)')) || tables[0];
  const rows = t ? t.querySelectorAll(
    'tbody tr:not(.rfid-gen-empty-row)').length : -1;
  const info = [...document.querySelectorAll('[id$=_info]')]
    .map(e => e.innerText.trim()).join(' | ');
  return {rows, info, tableId: t ? (t.id || '<no-id>') : null};
}"""


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

        for key in ("recent_generated", "rfid_list"):
            log(f"=== {key} ===")
            page.goto(settings.BASE_URL + settings.MODULE_PATHS[key],
                      wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            log(f"  search inputs: {page.evaluate(SEARCH_INPUTS_JS)}")
            log(f"  baseline: {page.evaluate(COUNT_JS)}")

            ajax: list[str] = []
            page.on("request", lambda r: ajax.append(r.url)
                    if ("draw=" in r.url or "search%5B" in r.url
                        or "search[" in r.url) else None)

            box = page.locator(
                "div[id$='_filter'] input[type=search]").first
            if box.count():
                box.click()
                box.fill("zzz-impossible-term-zzz")
                box.press("Enter")
                page.wait_for_timeout(2000)
                log(f"  after quick search: {page.evaluate(COUNT_JS)}")
                log(f"  ajax fired: {len(ajax)} -> {ajax[:2]}")
                box.fill("")
                box.press("Enter")
                page.wait_for_timeout(1500)
            else:
                log("  NO quick search box (div[id$=_filter] input[type=search])")
            log(f"  after clear: {page.evaluate(COUNT_JS)}")

            # reference path: keyword field + Filter
            kw = page.locator("#rfid-export-keyword")
            if kw.count():
                kw.first.fill("zzz-impossible-term-zzz")
                page.get_by_role("button", name="Filter",
                                 exact=False).first.click()
                page.wait_for_timeout(1800)
                log(f"  after KEYWORD+Filter: {page.evaluate(COUNT_JS)}")
                page.locator("#rfid-export-keyword").first.fill("")
                page.get_by_role("button", name="Filter",
                                 exact=False).first.click()
                page.wait_for_timeout(1200)

        for key in ("style_number_list", "transaction_list"):
            log(f"=== {key} ===")
            page.goto(settings.BASE_URL + settings.MODULE_PATHS[key],
                      wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            log(f"  state: {page.evaluate(COUNT_JS)}")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
