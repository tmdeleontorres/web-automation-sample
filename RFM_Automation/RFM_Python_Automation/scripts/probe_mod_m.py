"""DOM probe M - why rg_002b/rw_003 still fail after probe L (2026-10-19).

Probe L proved the Recent quick-search DOES filter (info -> "0 of 0 of 2"),
yet pytest rg_002b read row_count() == 2. Three hypotheses to settle:

H1  rows() counts a SECOND (hidden/stale) table that still holds the rows,
    because rows() spans every non-modal table while probe L's counter only
    looked at VISIBLE tables. -> inventory ALL tables (id, visible, thead,
    tbody rows) per phase.

H2  clearing the quick-search never restores (probe L: info stayed
    "0 of 0 (filtered from 2)" after fill('')+Enter AND after Keyword+Filter).
    -> try strategies: fill('')+Enter, Ctrl+A+Backspace, app Clear button.

H3  on RFID List the quick-search is inert because Enter submits a form and
    reloads the page (probe L could not tell). -> watch framenavigated
    events + url, and try type() (real per-key keyups, no Enter).

Also re-checks Style/Transaction pages (full run skipped both with
"No styles/transactions available"; probe L saw rows=0, info='') with a
longer wait + full table inventory.

Run:  python scripts/probe_mod_m.py
Out:  artifacts/probe_mod_m.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_m.txt"
LINES: list[str] = []

INVENTORY_JS = """() => ({
  tables: [...document.querySelectorAll('table')].map(t => ({
    id: t.id || '<no-id>',
    cls: (t.className || '').slice(0, 40),
    visible: !!(t.offsetWidth || t.offsetHeight),
    thead: t.querySelectorAll('thead th').length,
    rows: t.querySelectorAll('tbody tr:not(.rfid-gen-empty-row)').length,
    first: (t.querySelector('tbody tr') || {}).innerText
      ? t.querySelector('tbody tr').innerText.slice(0, 50).replace(/\\n/g, ' | ')
      : ''
  })),
  info: [...document.querySelectorAll('[id$=_info]')]
    .map(e => e.innerText.trim()),
  searchValue: (document.querySelector(
    "input[type=search][placeholder*='Quick search']") || {}).value ?? null,
})"""


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


def snap(page, label: str) -> None:
    data = page.evaluate(INVENTORY_JS)
    log(f"  [{label}] url={page.url.split('/')[-1][:40]!r}")
    log(f"  [{label}] info={data['info']} searchValue={data['searchValue']!r}")
    for t in data["tables"]:
        log(f"      table id={t['id']!r} vis={t['visible']} "
            f"thead={t['thead']} rows={t['rows']} first={t['first']!r}")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.HEADLESS)
        page = browser.new_context(viewport=settings.VIEWPORT,
                                   locale=settings.LOCALE).new_page()
        page.set_default_timeout(settings.TIMEOUT_MS)

        navs: list[str] = []
        page.on("framenavigated",
                lambda f: navs.append(f.url) if f == page.main_frame else None)

        page.goto(settings.BASE_URL + "/en/login",
                  wait_until="domcontentloaded")
        page.locator("#rfid-login-username").fill(settings.LOGIN_EMAIL)
        page.locator("#rfid-login-password").fill(settings.LOGIN_PASSWORD)
        page.locator("button[type=submit]").click()
        page.wait_for_timeout(3500)

        # ------------------------------------------------------------------ #
        # Recent Generated: search -> clear strategies (H1 + H2)
        # ------------------------------------------------------------------ #
        log("=== recent_generated ===")
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["recent_generated"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        snap(page, "baseline")

        box = page.locator(
            "input[type=search][placeholder*='Quick search']").first
        box.click()
        box.fill("zzz-no-such-record-zzz")
        box.press("Enter")
        page.wait_for_timeout(1500)
        snap(page, "after search (impossible term)")

        # H2 strategy A: fill('') + Enter  (current table_search behaviour)
        box.fill("")
        box.press("Enter")
        page.wait_for_timeout(1200)
        snap(page, "clear A: fill('')+Enter")

        # H2 strategy B: Ctrl+A + Backspace (real keyups)
        box.click()
        page.keyboard.press("Control+a")
        page.keyboard.press("Backspace")
        page.wait_for_timeout(1200)
        snap(page, "clear B: Ctrl+A+Backspace")

        # H2 strategy C: app Clear/Clear Filters button
        try:
            page.get_by_role("button", name="Clear",
                             exact=False).first.click(timeout=3000)
        except Exception as exc:
            log(f"      app Clear button failed: {type(exc).__name__}")
        page.wait_for_timeout(1200)
        snap(page, "clear C: app Clear button")

        # ------------------------------------------------------------------ #
        # RFID List: does Enter reload? does type() filter? (H3)
        # ------------------------------------------------------------------ #
        log("=== rfid_list ===")
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["rfid_list"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        snap(page, "baseline")
        navs.clear()

        box = page.locator(
            "input[type=search][placeholder*='Quick search']").first
        box.click()
        box.fill("zzz-no-such-record-zzz")
        box.press("Enter")
        page.wait_for_timeout(2500)
        snap(page, "fill+Enter (impossible)")
        log(f"      frame navigations during fill+Enter: {len(navs)} {navs[:2]}")

        # real keystrokes, no Enter (H3 alternative trigger)
        box.click()
        page.keyboard.press("Control+a")
        page.keyboard.press("Backspace")
        page.wait_for_timeout(800)
        box.type("zzz-no-such-record-zzz", delay=60)
        page.wait_for_timeout(2000)
        snap(page, "type() (impossible, no Enter)")

        # a real term: take the first EPC-ish cell from the data table
        epc = page.evaluate("""() => {
          const t = document.querySelector('table.rfid-export-table');
          const hs = [...t.querySelectorAll('thead th')]
            .map(h => h.innerText.trim().toLowerCase());
          let i = hs.indexOf('rfid');
          if (i < 0) i = hs.length - 1;
          const c = t.querySelector('tbody tr:not(.rfid-gen-empty-row) td');
          const cells = [...t.querySelectorAll(
            'tbody tr:not(.rfid-gen-empty-row) td')];
          return cells[i] ? cells[i].innerText.trim().slice(0, 10) : null;
        }""")
        log(f"      first-page RFID column sample: {epc!r}")
        box.click()
        page.keyboard.press("Control+a")
        page.keyboard.press("Backspace")
        page.wait_for_timeout(800)
        if epc:
            box.type(epc, delay=60)
            page.wait_for_timeout(2500)
            snap(page, f"type() real term ({epc})")
        navs.clear()

        # ------------------------------------------------------------------ #
        # Style + Transaction: empty in the full run? (longer wait)
        # ------------------------------------------------------------------ #
        for key in ("style_number_list", "transaction_list"):
            log(f"=== {key} (wait 8s) ===")
            page.goto(settings.BASE_URL + settings.MODULE_PATHS[key],
                      wait_until="domcontentloaded")
            page.wait_for_timeout(8000)
            snap(page, "state")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
