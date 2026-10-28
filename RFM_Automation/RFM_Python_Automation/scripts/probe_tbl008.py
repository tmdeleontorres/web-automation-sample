"""Probe the TC-TBL-008 scenario: per-code quantity bypass + Update series.

Scenario (added by the user in the HTML test sheet):
  1. Generate RFID with one item code with the qty of 2
  2. Add another item code with a bypass qty of 5 [ex: 5057877257490 :5]
  3. Click Generate Series
  4. Edit the first item code's Qty to 5
  5. Click Update series

Dumps after every step: rows, per-code row counts, counters, textarea,
status entries (qty/status/removed), open modals, toasts.

Run:  python scripts/probe_tbl008.py
Out:  artifacts/probe_tbl008.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

CODE_A = "5057877230509"      # verified generator code
CODE_B = "5057877257490"      # user's bypass-qty example code

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_tbl008.txt"
LINES: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


def dump(page, gen, label: str) -> None:
    rows = gen.rows().count()
    per_code: dict[str, int] = {}
    for v in gen.column_values("Item Code"):
        per_code[v] = per_code.get(v, 0) + 1
    statuses = gen.item_code_statuses()
    textarea = page.locator("#rfid-gtin").input_value()
    modals = page.evaluate(
        "() => [...document.querySelectorAll('.modal, [role=dialog]')]"
        ".filter(m => m.offsetWidth || m.offsetHeight)"
        ".map(m => (m.innerText || '').trim().slice(0, 90))")
    toasts = page.evaluate(
        "() => [...document.querySelectorAll('[class*=toast],[class*=alert]')]"
        ".filter(m => m.offsetWidth || m.offsetHeight)"
        ".map(m => (m.innerText || '').trim().slice(0, 60))")
    log(f"  [{label}] rows={rows} per_code={per_code} "
        f"counter={gen.counters()['Total Generated']}")
    log(f"    textarea={textarea!r}")
    log(f"    statuses={statuses}")
    log(f"    modals={modals} toasts={toasts}")


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

        from pages.generator_page import GeneratorPage
        gen = GeneratorPage(page)
        gen.open()

        # --- step 1: one code, qty 2 -------------------------------------
        gen.select_tab(gen.TAB_ITEM_CODE) \
           .enter_item_codes(CODE_A) \
           .set_starting_serial(9600).set_quantity(2) \
           .generate_series().continue_summary()
        dump(page, gen, "step1 generate A qty2")

        # --- step 2: add second code with bypass qty 'B: 5' --------------
        page.locator("#rfid-gtin").fill(f"{CODE_A}\n{CODE_B}: 5")
        page.locator("#rfid-gtin").press("Tab")
        page.wait_for_timeout(800)
        dump(page, gen, "step2 textarea A + 'B: 5' (blurred)")

        # --- step 3: Generate Series -------------------------------------
        gen.generate_series(wait_for_summary=True)
        if gen.summary_visible(timeout=2000):
            log(f"    summary text={gen.summary_text()[:200]!r}")
            gen.continue_summary()
        else:
            log("    NO SUMMARY after generate!")
        page.wait_for_timeout(800)
        dump(page, gen, "step3 generate again")

        # --- step 4: edit first code's Qty to 5 --------------------------
        gen.set_item_code_qty(CODE_A, 5)
        dump(page, gen, "step4 A qty -> 5 (blurred)")

        # --- step 5: Update series ---------------------------------------
        update_btn = page.locator("#rfid-current-series-refresh")
        log(f"    update button visible: "
            f"{update_btn.count() and update_btn.first.is_visible()}")
        gen.update_series()
        dump(page, gen, "step5 update series applied")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
