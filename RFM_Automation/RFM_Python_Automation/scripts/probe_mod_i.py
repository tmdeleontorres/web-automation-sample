"""DOM probe I - Operator Add-modal CHECK cell behaviour.

TC-OP-002/003 depend on the CHECK cell (span.operator-exists-indicator).
Probe D found its empty-row text is "Enter an account code", not the
documented "Waiting for name". This probe records how that cell reacts to:
  (a) an untouched row,
  (b) first+last name typed (no account code),
  (c) account code typed too,
so the tests can assert the app's real gate instead of a stale string.

Run:  python scripts/probe_mod_i.py
Out:  artifacts/probe_mod_i.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils.helpers import random_suffix  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_i.txt"
LINES: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


def check_state(page) -> str:
    loc = page.locator(".modal:visible span.operator-exists-indicator").first
    if not loc.count():
        return "<no indicator>"
    cls = loc.get_attribute("class") or ""
    return f"{loc.inner_text().strip()!r}  class={cls!r}"


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

        page.goto(settings.BASE_URL + settings.MODULE_PATHS["operator_list"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        page.get_by_role("button", name="Add Operators", exact=False).first.click()
        page.wait_for_timeout(800)

        log(f"  (a) untouched row: {check_state(page)}")

        sfx = random_suffix()
        row = page.locator(".modal:visible table.operator-entry-table tbody tr").first
        row.locator("input.operator-entry-first-name").fill(f"Probe{sfx}")
        row.locator("input.operator-entry-last-name").fill("QA")
        page.wait_for_timeout(700)
        log(f"  (b) names typed:  {check_state(page)}")

        code = f"QA{sfx}"[:20]
        row.locator("input.operator-entry-account-code").fill(code)
        page.wait_for_timeout(900)
        log(f"  (c) code typed:   {check_state(page)}")

        # Does Save Operators give any feedback (toast/modal) when we back out?
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        page.evaluate(
            "() => { document.querySelectorAll('.modal-backdrop').forEach("
            "b => b.remove()); document.body.classList.remove('modal-open'); }")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
