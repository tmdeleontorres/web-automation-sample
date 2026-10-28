"""Selector pass helper #6 - dumps the Item Code Status panel (generator
table #2): its Added/New badges, qty input, Update series and Remove controls,
and how the panel search behaves.

Run:  python scripts/probe_status.py
Out:  artifacts/probe_status.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils import test_data as data  # noqa: E402

OUT = Path(settings.ARTIFACTS_DIR)
OUTFILE = OUT / "probe_status.txt"
LINES: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")


def dump_status_panel(page, label: str) -> None:
    info = page.evaluate("""() => {
        const tables = [...document.querySelectorAll('table')];
        const t = tables.find(x => /Item Code/i.test(x.innerText.slice(0, 400)) ||
                                   [...x.querySelectorAll('thead th')]
                                     .some(th => /Model Set/i.test(th.innerText)));
        if (!t) return {found: false, tables: tables.length};
        const heads = [...t.querySelectorAll('thead th')].map(th => th.innerText.trim());
        const rows = [...t.querySelectorAll('tbody tr')].map(tr =>
            [...tr.querySelectorAll('td')].map(td => ({
                text: td.innerText.trim().slice(0, 40),
                html: td.innerHTML.slice(0, 220),
            })));
        // panel heading + controls that live next to the table
        const panel = t.closest('section, .rfid-gen-results, div');
        const badges = [...document.querySelectorAll(
            '[class*=status], [class*=badge], .rfid-item-status')]
            .filter(b => b.offsetWidth || b.offsetHeight)
            .map(b => ({cls: (b.className || '').slice(0, 50), text: b.innerText.trim()}))
            .slice(0, 12);
        const buttons = [...document.querySelectorAll('button')]
            .filter(b => b.offsetWidth || b.offsetHeight)
            .map(b => ((b.innerText || '').trim() || b.id));
        const inputs = [...document.querySelectorAll('input')]
            .filter(b => b.offsetWidth || b.offsetHeight)
            .map(b => ({id: b.id, type: b.type, value: (b.value || '').slice(0, 20),
                        ph: b.placeholder}));
        return {found: true, heads, rows, panelHead: (panel || {}).innerText
                  ? panel.innerText.slice(0, 200) : '', badges, buttons, inputs};
    }""")
    log(f"===== {label} =====")
    if not info.get("found"):
        log(f"  status table NOT found (tables on page: {info.get('tables')})")
        return
    log(f"  headers: {info['heads']}")
    for i, row in enumerate(info["rows"]):
        log(f"  row {i}: " + " | ".join(c["text"] for c in row))
        if i == 0:
            for j, c in enumerate(row):
                log(f"      td{j} html: {c['html']}")
    log(f"  badges: {info['badges']}")
    log(f"  buttons: {info['buttons']}")
    log(f"  inputs: {info['inputs']}")


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

        # enter several codes WITHOUT generating
        page.locator("#rfid-gtin").fill("\n".join(data.ITEM_CODES_MULTILINE))
        page.wait_for_timeout(1500)
        dump_status_panel(page, "after entering 4 codes (no generate)")

        # generate one of them
        page.locator("#rfid-serial-start").fill("9100")
        page.locator("#rfid-quantity").fill("2")
        page.get_by_role("button", name="Generate Series").click()
        page.wait_for_timeout(2000)
        page.locator("#rfid-confirm-save:visible").first.click()
        page.wait_for_timeout(1500)
        dump_status_panel(page, "after generating 2 rows")

        # search box behaviour
        target = data.ITEM_CODES_NEW[0]
        page.locator("#rfid-current-series-search").fill(target)
        page.wait_for_timeout(900)
        dump_status_panel(page, f"after searching '{target}'")
        page.locator("#rfid-current-series-search").fill("")
        page.wait_for_timeout(600)

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
