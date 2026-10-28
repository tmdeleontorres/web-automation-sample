"""Selector pass helper #7 - exact markup of the Item Code Status panel:
entry container, code element, Added/New badge classes, per-code Qty input,
Remove control and the Update series button.

Run:  python scripts/probe_status2.py
Out:  artifacts/probe_status2.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils import test_data as data  # noqa: E402

OUT = Path(settings.ARTIFACTS_DIR)
OUTFILE = OUT / "probe_status2.txt"
LINES: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")


PANEL_JS = """() => {
    const badge = document.querySelector('.rfid-current-series-code-status');
    if (!badge) return {found: false};
    // walk up to the panel container (the node holding every entry)
    let entry = badge, panel = badge.parentElement;
    for (let i = 0; i < 6 && panel; i++) {
        if (panel.querySelectorAll('.rfid-current-series-code-status').length > 1) break;
        entry = panel;
        panel = panel.parentElement;
    }
    const entries = [...(panel || badge.parentElement).querySelectorAll(
        '[class*=current-series]')].map(n => ({
            tag: n.tagName, cls: (n.className || '').slice(0, 60),
            text: (n.innerText || '').trim().slice(0, 60)})).slice(0, 24);
    return {
        found: true,
        panelTag: panel ? panel.tagName : null,
        panelId: panel ? panel.id : null,
        panelCls: panel ? (panel.className || '').slice(0, 80) : null,
        panelHead: panel ? (panel.innerText || '').trim().slice(0, 300) : null,
        entryHtml: entry ? entry.outerHTML.slice(0, 900) : null,
        badges: [...document.querySelectorAll('.rfid-current-series-code-status')]
            .map(b => ({cls: (b.className || '').slice(0, 60), text: b.innerText.trim()})),
        nearby: entries,
    };
}"""


def dump(page, label: str) -> None:
    info = page.evaluate(PANEL_JS)
    log(f"===== {label} =====")
    if not info.get("found"):
        log("  panel NOT present")
        return
    log(f"  panel: <{info['panelTag']} id='{info['panelId']}' class='{info['panelCls']}'>")
    log(f"  panel text: {info['panelHead']!r}")
    log(f"  badges: {info['badges']}")
    log(f"  nearby [class*=current-series] nodes: {info['nearby']}")
    log(f"  entry html: {info['entryHtml']}")
    buttons = page.evaluate(
        "() => [...document.querySelectorAll('button')]"
        ".filter(b => b.offsetWidth || b.offsetHeight)"
        ".map(b => ((b.innerText || '').trim() || b.id || b.title || '?'))")
    log(f"  visible buttons: {buttons}")


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

        # 1. four codes typed, no generation yet (blur the textarea first)
        page.locator("#rfid-gtin").fill("\n".join(data.ITEM_CODES_MULTILINE))
        page.locator("#rfid-quantity").click()          # force blur
        page.wait_for_timeout(1500)
        dump(page, "4 codes typed, NOT generated (after blur)")

        # 2. generate (quantity applies per code)
        page.locator("#rfid-serial-start").fill("9200")
        page.locator("#rfid-quantity").fill("1")
        page.get_by_role("button", name="Generate Series").click()
        page.wait_for_timeout(2200)
        page.locator("#rfid-confirm-save:visible").first.click()
        page.wait_for_timeout(1500)
        dump(page, "after generating")

        # 3. add a brand-new code while the panel exists
        page.locator("#rfid-gtin").fill(
            "\n".join(data.ITEM_CODES_MULTILINE + ["5057877230509"]))
        page.locator("#rfid-quantity").click()
        page.wait_for_timeout(1500)
        dump(page, "panel exists + codes retyped")

        # 4. which control updates quantity / removes a code?
        info = page.evaluate("""() => {
            const panel = document.querySelector('[class*=current-series]')
                ? document.querySelector('[class*=current-series]').closest('section, div')
                : null;
            const rows = panel
                ? [...panel.querySelectorAll('input, button, select')].map(el => ({
                    tag: el.tagName, id: el.id, type: el.type,
                    cls: (el.className || '').slice(0, 50),
                    title: el.title, aria: el.getAttribute('aria-label'),
                    value: (el.value || '').slice(0, 12),
                    text: (el.innerText || '').trim().slice(0, 20)}))
                : [];
            const update = [...document.querySelectorAll('button')]
                .filter(b => /update/i.test(b.innerText))
                .map(b => ({id: b.id, text: b.innerText.trim(),
                            visible: !!(b.offsetWidth || b.offsetHeight)}));
            return {controls: rows.slice(0, 30), update};
        }""")
        log(f"===== panel controls =====\n  {info}")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
