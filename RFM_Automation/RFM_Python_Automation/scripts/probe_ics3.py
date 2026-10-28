"""Selector pass helper #10 - attribute pageerrors + check Update series / Remove.

Timeline:  generate -> qty change -> "Update series" click -> "Generate Series"
click (textarea now holds 'code: qty'), each step logged with events so far.
Then a fresh page for the remove flow (entries/textarea/rows after removal).

Run:  python scripts/probe_ics3.py
Out:  artifacts/probe_ics3.txt
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils import test_data as data  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_ics3.txt"
LINES: list[str] = []
EVENTS: list[str] = []
T0 = time.monotonic()


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")


def on_dialog(d) -> None:
    EVENTS.append(f"[{time.monotonic() - T0:6.1f}s] dialog[{d.type}]: {d.message!r}")
    try:
        d.accept()
    except Exception as exc:                          # pragma: no cover
        EVENTS.append(f"    dialog accept failed: {exc}")


def on_console(m) -> None:
    if m.type in ("error", "warning"):
        EVENTS.append(f"[{time.monotonic() - T0:6.1f}s] console[{m.type}]: "
                      f"{m.text[:180]}")


def on_pageerror(e) -> None:
    EVENTS.append(f"[{time.monotonic() - T0:6.1f}s] PAGEERROR: {e}")


def attach(page) -> None:
    page.on("dialog", on_dialog)
    page.on("console", on_console)
    page.on("pageerror", on_pageerror)


def mark(label: str) -> None:
    log(f"  --- events so far ({label}): {EVENTS.copy()}")
    EVENTS.clear()


def state(page, label: str) -> None:
    rows = page.locator("table.rfid-gen-table tbody tr").count()
    counter = page.evaluate(
        r"() => (document.body.innerText.match(/TOTAL GENERATED[\s\S]{0,30}/)"
        r"|| [''])[0]").replace("\n", " ")
    entries = page.evaluate(
        "() => [...document.querySelectorAll('.rfid-current-series-code')]"
        ".map(e => {const r = e.getBoundingClientRect();"
        " return {code: (e.querySelector('code')?.textContent || '').trim(),"
        " cls: (e.className || '').slice(0, 50),"
        " w: Math.round(r.width), h: Math.round(r.height)};})")
    textarea = page.evaluate(
        "() => (document.querySelector('#rfid-gtin')?.value || '').split(/\\s*\\n\\s*/)"
        ".filter(Boolean)")
    modals = page.evaluate(
        "() => [...document.querySelectorAll('.modal')].filter(m =>"
        " (m.offsetWidth || m.offsetHeight)).map(m =>"
        " (m.innerText || '').trim().slice(0, 80))")
    toast = page.evaluate(
        "() => (document.querySelector('.toast, .alert, [role=alert]')"
        "?.innerText || '').trim().slice(0, 80)")
    log(f"  [{label}] rows={rows} counter={counter!r} entries={entries} "
        f"textarea={textarea} modals={modals} toast={toast!r}")


def login(page) -> None:
    page.goto(settings.BASE_URL + "/en/login", wait_until="domcontentloaded")
    page.locator("#rfid-login-username").fill(settings.LOGIN_EMAIL)
    page.locator("#rfid-login-password").fill(settings.LOGIN_PASSWORD)
    page.locator("button[type=submit]").click()
    page.wait_for_timeout(3500)
    log(f"login -> {page.url}")


def generate(page, codes: list[str], serial: int, qty: int) -> None:
    page.locator("#rfid-gtin").fill("\n".join(codes))
    page.locator("#rfid-gtin").press("Tab")
    page.wait_for_timeout(700)
    page.locator("#rfid-serial-start").fill(str(serial))
    page.locator("#rfid-quantity").fill(str(qty))
    page.get_by_role("button", name="Generate Series").click()
    page.wait_for_timeout(2200)
    page.locator("#rfid-confirm-save:visible").first.click()
    page.wait_for_timeout(1500)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.HEADLESS)
        ctx = browser.new_context(viewport=settings.VIEWPORT, locale=settings.LOCALE)
        page = ctx.new_page()
        page.set_default_timeout(settings.TIMEOUT_MS)
        attach(page)
        login(page)

        # ---- Stage U: update series ------------------------------------
        generate(page, [data.ITEM_CODE], 9600, 4)
        mark("generate")
        state(page, "after generate qty 4")

        page.locator(".rfid-current-series-code-quantity-input").first.fill("6")
        page.locator(".rfid-current-series-code-quantity-input").first.press("Tab")
        page.wait_for_timeout(500)
        mark("qty change + blur")
        state(page, "qty=6 blurred")

        page.locator("#rfid-current-series-refresh").click(timeout=5000)
        page.wait_for_timeout(2500)
        mark("Update series click")
        state(page, "after Update series (preview modal open?)")

        # the preview waits for Continue -> apply
        page.locator("#rfid-confirm-save:visible").first.click()
        page.wait_for_timeout(3000)
        mark("continue preview")
        state(page, "after Continue (qty applied?)")

        # ---- Stage R: remove flow on a fresh page ----------------------
        page2 = ctx.new_page()
        page2.set_default_timeout(settings.TIMEOUT_MS)
        attach(page2)
        # same context => already authenticated; go straight to the generator
        page2.goto(settings.BASE_URL + settings.GENERATOR_PATH,
                   wait_until="domcontentloaded")
        page2.wait_for_timeout(4000)
        log(f"page2 -> {page2.url}")

        generate(page2, data.ITEM_CODES_MULTILINE, 9700, 1)
        mark("4-code generate")
        state(page2, "4-code series")

        target = data.ITEM_CODES_NEW[0]
        page2.locator(
            f".rfid-current-series-code-remove[aria-label*='{target}']"
        ).click(timeout=5000)
        page2.wait_for_timeout(3000)
        mark("remove click")
        state(page2, "after remove (3s)")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
