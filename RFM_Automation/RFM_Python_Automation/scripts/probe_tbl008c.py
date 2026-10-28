"""Where does the 'Update series' button render in current builds?

Hypotheses tested against the live app:
  S: single code, one generate  -> button appeared here on 2026-10-09 (ics3/ics4)
  M: two codes, two generates   -> button ABSENT after editing code A (tbl008b)
  M5: edit the code of the LAST generate batch (B) instead of A

Run:  python scripts/probe_tbl008c.py
Out:  artifacts/probe_tbl008c.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

CODE_A = "5057877230509"
CODE_B = "5057877257490"

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_tbl008c.txt"
LINES: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


def dump(page, label: str) -> None:
    info = page.evaluate(
        """() => {
        const vis = el => !!(el.offsetWidth || el.offsetHeight);
        const ids = [...document.querySelectorAll('[id*=current-series]')]
            .map(e => e.id + (vis(e) ? '' : ' [hidden]'));
        const statuses = [...document.querySelectorAll('.rfid-current-series-code')]
            .map(e => ({code: (e.querySelector('code')?.textContent||'').trim(),
                        qty: e.querySelector('input')?.value,
                        badge: (e.querySelector('[class*=status]')?.textContent||'').trim()}));
        const rows = document.querySelectorAll(
            'table.rfid-gen-table tbody tr:not(.rfid-gen-empty-row)').length;
        const refresh = document.querySelector('#rfid-current-series-refresh');
        return {ids, statuses, rows,
                refresh: !!refresh,
                refreshVisible: refresh ? vis(refresh) : null};
    }""")
    log(f"  [{label}] rows={info['rows']} refresh={info['refresh']}/"
        f"vis={info['refreshVisible']} ids={info['ids']}")
    log(f"    statuses={info['statuses']}")


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

        # ---------- S: single code, one generate (10/9 reference flow) -----
        gen.open()
        gen.select_tab(gen.TAB_ITEM_CODE) \
           .enter_item_codes(CODE_A) \
           .set_starting_serial(9700).set_quantity(4) \
           .generate_series().continue_summary()
        dump(page, "S1 after first generate (single)")
        gen.set_item_code_qty(CODE_A, 6)
        dump(page, "S2 qty 4->6 blurred (single)")
        if page.locator("#rfid-current-series-refresh").count():
            gen.update_series()
            dump(page, "S3 after update applied (single)")
        else:
            log("  S: refresh button MISSING in single-code flow too!")

        # ---------- M: two codes, two generates ----------------------------
        gen.open()
        gen.select_tab(gen.TAB_ITEM_CODE) \
           .enter_item_codes(CODE_A) \
           .set_starting_serial(9800).set_quantity(2) \
           .generate_series().continue_summary()
        dump(page, "M1 first generate A qty2")

        page.locator("#rfid-gtin").fill(f"{CODE_A}\n{CODE_B}: 5")
        page.locator("#rfid-gtin").press("Tab")
        page.wait_for_timeout(700)
        dump(page, "M2 textarea A + B:5 blurred")

        gen.generate_series(wait_for_summary=True)
        if gen.summary_visible(timeout=2000):
            gen.continue_summary()
        page.wait_for_timeout(700)
        dump(page, "M3 second generate (B x5) applied")

        gen.set_item_code_qty(CODE_A, 5)          # edit FIRST-batch code
        dump(page, "M4 A qty -> 5 (first-batch code)")

        gen.set_item_code_qty(CODE_B, 7)          # edit LAST-batch code
        dump(page, "M5 B qty -> 7 (last-batch code)")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
