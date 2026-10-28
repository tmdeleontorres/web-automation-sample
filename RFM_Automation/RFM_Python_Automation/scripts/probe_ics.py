"""Selector pass helper #8 - visibility of the Item Code Status controls.

Replicates the exact flows of TC-ICS-002 / 003 / 005 to learn:
  A. before generation: is the panel / search input / remove button visible?
  B. qty change -> does the "Update series" button appear? do counters change?
  C. after generation: is the remove button clickable, or hover-only?

Run:  python scripts/probe_ics.py
Out:  artifacts/probe_ics.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils import test_data as data  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_ics.txt"
LINES: list[str] = []

SEL = [
    ("panel", "#rfid-current-series-code-list"),
    ("entry", "#rfid-current-series-code-list .rfid-current-series-code"),
    ("search", "#rfid-current-series-search"),
    ("remove", ".rfid-current-series-code-remove"),
    ("refresh", "#rfid-current-series-refresh"),
    ("qty", ".rfid-current-series-code-quantity-input"),
]

STYLE_JS = """(sel) => [...document.querySelectorAll(sel)].slice(0, 5).map(el => {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return {display: cs.display, vis: cs.visibility, op: cs.opacity,
            w: Math.round(r.width), h: Math.round(r.height),
            dis: !!el.disabled, cls: (el.className || '').slice(0, 40)};
})"""

NOTICE_JS = """() => [...document.querySelectorAll('div,small,span,p,button')]
    .filter(el => (el.offsetWidth || el.offsetHeight) &&
                  /quantity changed|update series|clear changes/i.test(el.textContent))
    .slice(0, 8)
    .map(el => ({tag: el.tagName, id: el.id, cls: (el.className || '').slice(0, 40),
                 text: (el.innerText || '').trim().slice(0, 60)}))"""


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")


def dump(page, label: str) -> None:
    log(f"===== {label} =====")
    for name, sel in SEL:
        try:
            info = page.evaluate(STYLE_JS, sel)
        except Exception as exc:                       # pragma: no cover
            log(f"  {name:8} ERROR {exc}")
            continue
        log(f"  {name:8} {info}")
    log(f"  notices  {page.evaluate(NOTICE_JS)}")


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

        # ---- Stage A: TC-ICS-002 / 005 flow (codes typed, nothing generated)
        page.locator("#rfid-gtin").fill("\n".join(data.ITEM_CODES_MULTILINE))
        page.locator("#rfid-gtin").press("Tab")
        page.wait_for_timeout(1200)
        dump(page, "A: 4 codes typed, NOT generated")

        try:
            page.locator("#rfid-current-series-search").fill(
                data.ITEM_CODES_NEW[0], timeout=4000)
            page.wait_for_timeout(600)
            log(f"  search fill OK -> entries now "
                f"{page.locator('.rfid-current-series-code').count()}")
            page.locator("#rfid-current-series-search").fill("", timeout=4000)
            page.wait_for_timeout(400)
        except Exception as exc:
            log(f"  search fill FAILED: {str(exc).splitlines()[0]}")

        # remove attempt (TC-ICS-005 does this BEFORE generating)
        try:
            page.locator(
                f".rfid-current-series-code-remove[aria-label*='{data.ITEM_CODES_NEW[0]}']"
            ).click(timeout=4000)
            page.wait_for_timeout(600)
            log(f"  remove click OK -> entries now "
                f"{page.locator('.rfid-current-series-code').count()}")
        except Exception as exc:
            log(f"  remove click FAILED: {str(exc).splitlines()[0]}")
            # retry after hovering the entry
            try:
                entry = page.locator("#rfid-current-series-code-list "
                                     ".rfid-current-series-code",
                                     has_text=data.ITEM_CODES_NEW[0]).first
                entry.hover()
                page.wait_for_timeout(300)
                entry.locator(".rfid-current-series-code-remove").first.click(timeout=4000)
                log("  remove click OK after hover()")
            except Exception as exc2:
                log(f"  remove after hover FAILED: {str(exc2).splitlines()[0]}")

        # ---- Stage B: TC-ICS-003 flow (single code, generate, qty change)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        page.locator("#rfid-gtin").fill(data.ITEM_CODE)
        page.locator("#rfid-gtin").press("Tab")
        page.wait_for_timeout(800)
        page.locator("#rfid-serial-start").fill("9200")
        page.locator("#rfid-quantity").fill("4")
        page.get_by_role("button", name="Generate Series").click()
        page.wait_for_timeout(2200)
        page.locator("#rfid-confirm-save:visible").first.click()
        page.wait_for_timeout(1500)
        dump(page, "B1: after generate+continue (qty 4)")

        page.locator(".rfid-current-series-code-quantity-input").first.fill("6")
        page.wait_for_timeout(600)
        dump(page, "B2: qty input filled with 6 (no blur)")

        page.locator(".rfid-current-series-code-quantity-input").first.press("Tab")
        page.wait_for_timeout(600)
        dump(page, "B3: after blur (Tab)")

        try:
            page.locator("#rfid-current-series-refresh").click(timeout=4000)
            page.wait_for_timeout(2500)
            counter = page.evaluate(
                r"() => (document.body.innerText.match(/TOTAL GENERATED[\s\S]{0,40}/)"
                r"|| [''])[0]")
            log(f"  refresh clicked -> counter text {counter!r}")
        except Exception as exc:
            log(f"  refresh click FAILED: {str(exc).splitlines()[0]}")
        dump(page, "B4: after Update series")
        log(f"  series table rows: "
            f"{page.locator('table.rfid-gen-table tbody tr').count()}")

        # ---- Stage C: TC-ICS-002 / 005 flows WITH a generated series ----
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        page.locator("#rfid-gtin").fill("\n".join(data.ITEM_CODES_MULTILINE))
        page.locator("#rfid-gtin").press("Tab")
        page.wait_for_timeout(800)
        page.locator("#rfid-serial-start").fill("9500")
        page.locator("#rfid-quantity").fill("1")
        page.get_by_role("button", name="Generate Series").click()
        page.wait_for_timeout(2200)
        page.locator("#rfid-confirm-save:visible").first.click()
        page.wait_for_timeout(1500)
        dump(page, "C1: 4 codes + generated series")

        target = data.ITEM_CODES_NEW[0]
        try:
            page.locator("#rfid-current-series-search").fill(target, timeout=6000)
            page.wait_for_timeout(600)
            log(f"  search fill OK -> entries now "
                f"{page.locator('.rfid-current-series-code').count()}")
            page.locator("#rfid-current-series-search").fill("", timeout=6000)
            page.wait_for_timeout(600)
            log(f"  search cleared -> entries now "
                f"{page.locator('.rfid-current-series-code').count()}")
        except Exception as exc:
            log(f"  search flow FAILED: {str(exc).splitlines()[0]}")

        try:
            page.locator(
                f".rfid-current-series-code-remove[aria-label*='{target}']"
            ).click(timeout=6000)
            page.wait_for_timeout(600)
            log(f"  remove click OK -> entries now "
                f"{page.locator('.rfid-current-series-code').count()}, rows "
                f"{page.locator('table.rfid-gen-table tbody tr').count()}")
        except Exception as exc:
            log(f"  remove click FAILED: {str(exc).splitlines()[0]}")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
