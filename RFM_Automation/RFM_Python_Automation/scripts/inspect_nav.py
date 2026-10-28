"""Selector pass helper #2 - visits every sidebar module and records
its real URL, headings and a sample table row.

Run:  python scripts/inspect_nav.py
Out:  artifacts/inspect_nav.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

OUT = Path(settings.ARTIFACTS_DIR)
OUT.mkdir(parents=True, exist_ok=True)

MODULES = [
    "Generator", "Recent Generated", "RFID List", "Style Number List",
    "Mother List", "Transaction List", "All Users", "Operator List",
    "Warehouses", "Deleted List", "Rewrite RFIDs", "Import",
    "Item Code Mismatch", "Generation History",
]


def main() -> None:
    lines: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.HEADLESS)
        ctx = browser.new_context(viewport=settings.VIEWPORT, locale=settings.LOCALE,
                                  timezone_id=settings.TIMEZONE)
        page = ctx.new_page()
        page.set_default_timeout(settings.TIMEOUT_MS)

        # login
        page.goto(settings.BASE_URL + "/en/login", wait_until="domcontentloaded")
        page.locator("#rfid-login-username").fill(settings.LOGIN_EMAIL)
        page.locator("#rfid-login-password").fill(settings.LOGIN_PASSWORD)
        page.locator("button[type=submit]").click()
        page.wait_for_timeout(4000)
        assert "rfid_generator" in page.url, f"login did not complete: {page.url}"

        for name in MODULES:
            link = page.get_by_role("link", name=name, exact=True).first
            if not link.count():
                link = page.locator("a").filter(has_text=name).first
            if not link.count():
                lines.append(f"{name:<22} !! sidebar link not found")
                continue
            href = link.get_attribute("href") or ""
            link.click()
            try:
                page.wait_for_load_state("domcontentloaded")
            except Exception:
                pass
            page.wait_for_timeout(1800)

            info = page.evaluate("""() => {
                const txt = el => (el.innerText || '').trim();
                const heads = [];
                document.querySelectorAll('h1,h2,h3,h4,h5,.card-title,.page-title,.rfid-gen-panel-title')
                  .forEach(el => { const t = txt(el); if (t && t.length < 60) heads.push(t); });
                const row = document.querySelector('table tbody tr');
                const heads2 = [...document.querySelectorAll('table thead th')]
                  .map(th => txt(th)).filter(Boolean);
                return {
                    url: location.href, heads: heads.slice(0, 8), cols: heads2,
                    rowHtml: row ? row.outerHTML.slice(0, 700) : '',
                    buttons: [...document.querySelectorAll('button')]
                      .filter(b => b.offsetWidth || b.offsetHeight)
                      .map(b => txt(b)).filter(Boolean).slice(0, 14),
                    inputs: [...document.querySelectorAll('input,select,textarea')]
                      .filter(b => b.offsetWidth || b.offsetHeight)
                      .map(b => (b.id || b.name || b.type || 'x')).slice(0, 14),
                };
            }""")

            lines.append(f"===== {name} =====")
            lines.append(f"  href    : {href}")
            lines.append(f"  url     : {info['url']}")
            lines.append(f"  headings: {info['heads']}")
            lines.append(f"  columns : {info['cols']}")
            lines.append(f"  buttons : {info['buttons']}")
            lines.append(f"  inputs  : {info['inputs']}")
            if info["rowHtml"]:
                lines.append(f"  row html: {info['rowHtml']}")
            lines.append("")

        browser.close()

    text = "\n".join(lines)
    (OUT / "inspect_nav.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
