"""Verify the NEW Update-Series mechanism end to end (ICS-003 + TBL-008).

Flow U (single code, TC-ICS-003):  generate qty 4 -> qty 6 -> Update Series
                                    -> preview -> Continue -> expect 6 rows.
Flow T (TC-TBL-008 exact scenario):
  1. generate A qty 2                       -> 2 rows
  2. add second code as 'A\nB: 5' (bypass)
  3. Generate Series                        -> A:2 + B:5 = 7 rows
  4. edit first code (A) to 5
  5. Update Series                          -> expect A:5 + B:5 = 10 rows

Run:  python scripts/probe_tbl008e.py
Out:  artifacts/probe_tbl008e.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

CODE_A = "5057877230509"
CODE_B = "5057877257490"

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_tbl008e.txt"
LINES: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


def dump(page, gen, label: str) -> None:
    info = page.evaluate(
        """() => {
        const b = document.querySelector('#rfid-generate-series');
        const modals = [...document.querySelectorAll('.modal')]
            .filter(m => m.offsetWidth || m.offsetHeight)
            .map(m => (m.innerText || '').trim().slice(0, 80));
        const rows = [...document.querySelectorAll(
            'table.rfid-gen-table tbody tr:not(.rfid-gen-empty-row)')];
        const per = {};
        const th = [...document.querySelectorAll('table.rfid-gen-table thead th')]
            .findIndex(h => /item code/i.test(h.innerText));
        rows.forEach(r => {
            const v = r.children[th]?.innerText.trim() || '?';
            per[v] = (per[v] || 0) + 1;
        });
        return {
            button: b ? {id: b.id, cls: (b.className || '').slice(0, 60),
                         text: (b.innerText || '').trim()} : null,
            rows: rows.length, per,
            textarea: document.querySelector('#rfid-gtin')?.value || '',
            counters: (document.body.innerText.match(
                /TOTAL GENERATED[\\s\\S]{0,40}/) || [''])[0].replace(/\\n/g, ' '),
            modals
        };
    }""")
    log(f"  [{label}] rows={info['rows']} per_code={info['per']}")
    log(f"    button={info['button']} counters={info['counters']!r}")
    log(f"    textarea={info['textarea']!r} modals={info['modals']}")


def login(page) -> None:
    page.goto(settings.BASE_URL + "/en/login", wait_until="domcontentloaded")
    page.locator("#rfid-login-username").fill(settings.LOGIN_EMAIL)
    page.locator("#rfid-login-password").fill(settings.LOGIN_PASSWORD)
    page.locator("button[type=submit]").click()
    page.wait_for_timeout(3500)
    log(f"login -> {page.url}")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.HEADLESS)
        page = browser.new_context(viewport=settings.VIEWPORT,
                                   locale=settings.LOCALE).new_page()
        page.set_default_timeout(settings.TIMEOUT_MS)
        login(page)

        from pages.generator_page import GeneratorPage
        gen = GeneratorPage(page)

        # ---------- Flow U: TC-ICS-003 (single code 4 -> 6) ---------------
        gen.open()
        gen.select_tab(gen.TAB_ITEM_CODE) \
           .enter_item_codes(CODE_A) \
           .set_starting_serial(9700).set_quantity(4) \
           .generate_series().continue_summary()
        dump(page, gen, "U1 generated qty4")
        gen.set_item_code_qty(CODE_A, 6)
        dump(page, gen, "U2 qty 4->6 pending")
        gen.update_series()
        dump(page, gen, "U3 update applied (expect 6)")

        # ---------- Flow T: TC-TBL-008 ------------------------------------
        gen.open()
        gen.select_tab(gen.TAB_ITEM_CODE) \
           .enter_item_codes(CODE_A) \
           .set_starting_serial(9800).set_quantity(2) \
           .generate_series().continue_summary()
        dump(page, gen, "T1 A qty2 (expect 2)")

        page.locator("#rfid-gtin").fill(f"{CODE_A}\n{CODE_B}: 5")
        page.locator("#rfid-gtin").press("Tab")
        page.wait_for_timeout(700)
        dump(page, gen, "T2 textarea bypass entered")

        gen.generate_series(wait_for_summary=True)
        if gen.summary_visible(timeout=2000):
            log(f"    summary={gen.summary_text()[:120]!r}")
            gen.continue_summary()
        page.wait_for_timeout(600)
        dump(page, gen, "T3 second generate (expect 7)")

        gen.set_item_code_qty(CODE_A, 5)
        dump(page, gen, "T4 A qty -> 5 pending")
        gen.update_series()
        dump(page, gen, "T5 update applied (expect 10, A=5)")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
