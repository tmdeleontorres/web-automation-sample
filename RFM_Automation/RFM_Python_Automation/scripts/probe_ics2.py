"""Selector pass helper #9 - why Update series / Remove behave as they do.

Captures native dialogs, console errors and page errors around:
  1. qty 4 -> 6, blur, click "Update series"  (TC-ICS-003)
  2. remove one code from a 4-code series      (TC-ICS-005)

Run:  python scripts/probe_ics2.py
Out:  artifacts/probe_ics2.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils import test_data as data  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_ics2.txt"
LINES: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")


def attach(page, tag: str) -> list[str]:
    """Log dialogs / console errors / page errors under a tag."""
    events: list[str] = []
    page.on("dialog", lambda d: (
        events.append(f"dialog[{d.type}]: {d.message!r}"),
        d.accept() if d.type == "confirm" else d.dismiss(),
    ))
    page.on("console", lambda m: (
        events.append(f"console[{m.type}]: {m.text[:200]}")
        if m.type in ("error", "warning") else None))
    page.on("pageerror", lambda e: events.append(f"pageerror: {e}"))
    setattr(page, "_events_" + tag, events)
    return events


def state(page, label: str) -> None:
    rows = page.locator("table.rfid-gen-table tbody tr").count()
    counter = page.evaluate(
        r"() => (document.body.innerText.match(/TOTAL GENERATED[\s\S]{0,30}/)"
        r"|| [''])[0]").replace("\n", " ")
    entries = page.evaluate(
        "() => [...document.querySelectorAll('.rfid-current-series-code')]"
        ".map(e => (e.querySelector('code')?.textContent || '').trim())")
    refresh = page.evaluate(
        "() => {const b = document.querySelector('#rfid-current-series-refresh');"
        "if (!b) return 'absent'; const r = b.getBoundingClientRect();"
        "return r.width + 'x' + r.height;}")
    textarea = page.evaluate(
        "() => document.querySelector('#rfid-gtin')?.value.split(/\\s*\\n\\s*/)"
        ".filter(Boolean) || []")
    dirty = page.evaluate(
        "() => (document.querySelector('#rfid-current-series-update')"
        "?.innerText || '').replace(/\\n/g, ' ').slice(0, 60)")
    log(f"  [{label}] rows={rows} counter={counter!r} entries={entries} "
        f"textarea={textarea} refresh={refresh} dirty={dirty!r}")


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
        page = browser.new_context(viewport=settings.VIEWPORT,
                                   locale=settings.LOCALE).new_page()
        page.set_default_timeout(settings.TIMEOUT_MS)
        login(page)

        # ---- 1. Update series (qty 4 -> 6) ------------------------------
        ev1 = attach(page, "update")
        generate(page, [data.ITEM_CODE], 9600, 4)
        state(page, "after generate qty 4")
        page.locator(".rfid-current-series-code-quantity-input").first.fill("6")
        page.locator(".rfid-current-series-code-quantity-input").first.press("Tab")
        page.wait_for_timeout(500)
        state(page, "qty=6 blurred")
        try:
            page.locator("#rfid-current-series-refresh").click(timeout=5000)
            log("  refresh clicked")
        except Exception as exc:
            log(f"  refresh FAILED: {str(exc).splitlines()[0]}")
        page.wait_for_timeout(3500)
        state(page, "after update")
        log(f"  events: {ev1}")

        # ---- 2. Remove a code from a 4-code series ---------------------
        ev2 = attach(page, "remove")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        generate(page, data.ITEM_CODES_MULTILINE, 9700, 1)
        state(page, "4-code series")
        target = data.ITEM_CODES_NEW[0]
        try:
            page.locator(
                f".rfid-current-series-code-remove[aria-label*='{target}']"
            ).click(timeout=5000)
            log(f"  remove clicked for {target}")
        except Exception as exc:
            log(f"  remove FAILED: {str(exc).splitlines()[0]}")
        page.wait_for_timeout(2500)
        state(page, "after remove")
        log(f"  events: {ev2}")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
