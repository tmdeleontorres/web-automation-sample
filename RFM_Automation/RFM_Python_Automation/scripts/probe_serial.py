"""Selector pass helper #12 - how STARTING SERIAL is applied.

Generates on fresh pages and logs the requested serial vs the serials the
app actually produces, for: a code with saved history (serial 9600 / 0) and
a never-used code (serial 0 / 5).

Run:  python scripts/probe_serial.py
Out:  artifacts/probe_serial.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils import test_data as data  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_serial.txt"
LINES: list[str] = []

ROWS_JS = """() => [...document.querySelectorAll('table.rfid-gen-table tbody tr')]
    .slice(0, 6).map(tr => {
        const td = [...tr.querySelectorAll('td')];
        return {code: (td[0]?.innerText || '').trim(),
                rfid: (td[6]?.innerText || '').trim(),
                serial: (td[7]?.innerText || '').trim()};
    })"""


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")


def new_authed_page(ctx):
    page = ctx.new_page()
    page.set_default_timeout(settings.TIMEOUT_MS)
    page.goto(settings.BASE_URL + settings.GENERATOR_PATH,
              wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    return page


def login(page) -> None:
    page.goto(settings.BASE_URL + "/en/login", wait_until="domcontentloaded")
    page.locator("#rfid-login-username").fill(settings.LOGIN_EMAIL)
    page.locator("#rfid-login-password").fill(settings.LOGIN_PASSWORD)
    page.locator("button[type=submit]").click()
    page.wait_for_timeout(3500)
    log(f"login -> {page.url}")


def generate_and_read(page, code: str, serial: int, qty: int, label: str) -> None:
    page.locator("#rfid-gtin").fill(code)
    page.locator("#rfid-gtin").press("Tab")
    page.wait_for_timeout(700)
    page.locator("#rfid-serial-start").fill(str(serial))
    page.locator("#rfid-quantity").fill(str(qty))
    serial_actual = page.evaluate(
        "() => document.querySelector('#rfid-serial-start')?.value")
    page.get_by_role("button", name="Generate Series").click()
    page.wait_for_timeout(2200)
    preview = page.locator("#rfid-save-confirm-modal:visible")
    preview_text = preview.first.inner_text().replace("\n", " ")[:120] \
        if preview.count() else "(no preview modal)"
    log(f"  [{label}] requested serial={serial} field held={serial_actual!r} "
        f"qty={qty} -> preview: {preview_text}")
    if preview.count():
        page.locator("#rfid-confirm-save:visible").first.click()
        page.wait_for_timeout(1500)
    log(f"  [{label}] rows: {page.evaluate(ROWS_JS)}")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.HEADLESS)
        ctx = browser.new_context(viewport=settings.VIEWPORT, locale=settings.LOCALE)

        page = new_authed_page(ctx)
        login(page)

        # 1. code WITH saved history, a high serial
        generate_and_read(page, data.ITEM_CODE, 9600, 2, "history/9600")
        page.close()

        # 2. same code, serial 0
        page = new_authed_page(ctx)
        generate_and_read(page, data.ITEM_CODE, 0, 1, "history/0")
        page.close()

        # 3. never-used code, serial 0
        page = new_authed_page(ctx)
        generate_and_read(page, data.ITEM_CODES_NEW[0], 0, 1, "fresh/0")
        page.close()

        # 4. never-used code, serial 5
        page = new_authed_page(ctx)
        generate_and_read(page, data.ITEM_CODES_NEW[0], 5, 1, "fresh/5")
        page.close()

        # 5. continuation rule: same fresh code again with serial 20
        page = new_authed_page(ctx)
        generate_and_read(page, data.ITEM_CODES_NEW[0], 20, 1, "fresh/20-again")
        page.close()

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
