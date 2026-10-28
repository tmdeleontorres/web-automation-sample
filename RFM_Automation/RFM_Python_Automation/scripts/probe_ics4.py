"""Selector pass helper #11 - out-of-range per-item Qty (TC-ICS-004).

After a 1-row series: set Qty to 0, update; set Qty to 5001, update.
Logs validation feedback, modals, toasts, textarea and counters.

Run:  python scripts/probe_ics4.py
Out:  artifacts/probe_ics4.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils import test_data as data  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_ics4.txt"
LINES: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")


def state(page, label: str) -> None:
    rows = page.locator("table.rfid-gen-table tbody tr").count()
    counter = page.evaluate(
        r"() => (document.body.innerText.match(/TOTAL GENERATED[\s\S]{0,30}/)"
        r"|| [''])[0]").replace("\n", " ")
    textarea = page.evaluate(
        "() => (document.querySelector('#rfid-gtin')?.value || '')")
    qty_val = page.evaluate(
        "() => document.querySelector('.rfid-current-series-code-quantity-input')"
        "?.value")
    dirty = page.evaluate(
        "() => (document.querySelector('#rfid-current-series-update')"
        "?.innerText || '').replace(/\\n/g, ' ').slice(0, 50)")
    modals = page.evaluate(
        "() => [...document.querySelectorAll('.modal')].filter(m =>"
        " (m.offsetWidth || m.offsetHeight)).map(m =>"
        " (m.innerText || '').trim().slice(0, 120))")
    toasts = page.evaluate(
        "() => [...document.querySelectorAll('.toast, .alert, [role=alert],"
        " .rfid-gen-error, .invalid-feedback')]"
        ".filter(t => (t.offsetWidth || t.offsetHeight))"
        ".map(t => (t.innerText || '').trim().slice(0, 100))")
    validity = page.evaluate(
        "() => {const i = document.querySelector("
        "'.rfid-current-series-code-quantity-input');"
        "return i ? {valid: i.validity.valid, range: i.validationMessage,"
        " min: i.min, max: i.max, value: i.value} : null;}")
    log(f"  [{label}] rows={rows} counter={counter!r} qty={qty_val!r} "
        f"textarea={textarea!r} dirty={dirty!r} modals={modals} "
        f"toasts={toasts} validity={validity}")


def close_modal(page) -> None:
    """Close the generation preview without applying (x button)."""
    for sel in ("#rfid-save-confirm-modal button.close",
                "#rfid-confirm-x",
                ".modal.show .close"):
        btn = page.locator(sel)
        if btn.count() and btn.first.is_visible():
            try:
                btn.first.click(timeout=3000)
                page.wait_for_timeout(700)
                return
            except Exception:
                continue
    page.keyboard.press("Escape")
    page.wait_for_timeout(700)


def set_qty_and_update(page, qty) -> None:
    box = page.locator(".rfid-current-series-code-quantity-input").first
    box.fill(str(qty))
    box.press("Tab")
    page.wait_for_timeout(500)
    btn = page.locator("#rfid-current-series-refresh")
    log(f"  update button visible: {btn.count() and btn.first.is_visible()}")
    if btn.count() and btn.first.is_visible():
        btn.first.click()
        page.wait_for_timeout(2500)


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
        log(f"login -> {page.url}")

        page.locator("#rfid-gtin").fill(data.ITEM_CODE)
        page.locator("#rfid-gtin").press("Tab")
        page.wait_for_timeout(700)
        page.locator("#rfid-serial-start").fill("9800")
        page.locator("#rfid-quantity").fill("1")
        page.get_by_role("button", name="Generate Series").click()
        page.wait_for_timeout(2200)
        page.locator("#rfid-confirm-save:visible").first.click()
        page.wait_for_timeout(1500)
        state(page, "after generate qty 1")

        # ---- Qty = 0 ---------------------------------------------------
        set_qty_and_update(page, 0)
        state(page, "after update attempt qty=0")
        close_modal(page)
        state(page, "modal closed (qty=0)")

        # ---- Qty = 5001 ------------------------------------------------
        set_qty_and_update(page, 5001)
        state(page, "after update attempt qty=5001")
        close_modal(page)
        state(page, "modal closed (qty=5001)")

        # ---- Qty = 5000 (valid upper bound, do NOT continue) -----------
        set_qty_and_update(page, 5000)
        state(page, "after update attempt qty=5000")
        close_modal(page)
        state(page, "done")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
