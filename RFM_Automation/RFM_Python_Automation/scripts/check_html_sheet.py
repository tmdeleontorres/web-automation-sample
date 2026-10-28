"""Smoke-check the HTML test-case project: renders, no JS errors, TC present.

Run:  python scripts/check_html_sheet.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent      # .../RFM_Automation
URL = (ROOT / "RFM_Test_Cases_HTML" / "index.html").as_uri()

from playwright.sync_api import sync_playwright  # noqa: E402


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL)
        page.wait_for_timeout(1500)

        rows = page.locator("tbody tr").count()
        tbl8 = page.get_by_text("TC-TBL-008").count()
        header = page.locator("h1, .title, header").first
        title = header.inner_text() if header.count() else ""
        browser.close()

    print(f"url: {URL}")
    print(f"title: {title.strip()[:80]}")
    print(f"rendered rows: {rows}")
    print(f"TC-TBL-008 present: {tbl8}")
    print(f"page errors: {errors or 'none'}")
    return 0 if (rows >= 135 and tbl8 and not errors) else 1


if __name__ == "__main__":
    sys.exit(main())
