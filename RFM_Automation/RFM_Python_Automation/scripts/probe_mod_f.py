"""DOM probe F - All Users create/validation feedback (real user-timing).

The modal stays open with an inline message when validation fails, and closes
with a toast on success. This probe captures the exact feedback element and
text for: valid create, mismatched passwords, and missing required fields.
It also checks what the leftover overlay is after closing.

Run:  python scripts/probe_mod_f.py
Out:  artifacts/probe_mod_f.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils.helpers import random_suffix  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_f.txt"
LINES: list[str] = []

FEEDBACK_JS = """() => {
  const vis = el => !!(el.offsetWidth || el.offsetHeight);
  const out = [];
  for (const sel of ['.toast', '.alert', '[role=alert]', '.notif', '.swal2-popup',
                     '.modal.show', '.modal.in', '.rfid-gen-alert', '.text-danger',
                     '.invalid-feedback', '.is-invalid']) {
    for (const el of document.querySelectorAll(sel)) {
      if (vis(el)) out.push({sel, id: el.id,
        cls: (el.className || '').toString().slice(0, 50),
        text: (el.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 250)});
    }
  }
  return out;
}"""

OVERLAY_JS = """() => {
  const vis = el => !!(el.offsetWidth || el.offsetHeight);
  const open = [...document.querySelectorAll('.modal')].filter(vis)
    .map(m => ({id: m.id, cls: (m.className || '').slice(0, 60)}));
  const backdrops = [...document.querySelectorAll('.modal-backdrop')].length;
  const body = document.body.className;
  return {open, backdrops, body};
}"""


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


def fill(page, first, last, email, pw, conf):
    for sel, val in (("#user-edit-firstname", first),
                     ("#user-edit-lastname", last),
                     ("#user-edit-email", email),
                     ("#user-edit-password", pw),
                     ("#user-edit-password-confirm", conf)):
        loc = page.locator(sel)
        if loc.count() and loc.first.is_visible():
            loc.first.fill(val)


def open_create(page):
    page.get_by_role("button", name="Create User", exact=False).first.click()
    page.wait_for_timeout(700)


def dismiss(page):
    """Close any open modal via Escape, and clear a stuck backdrop."""
    for _ in range(3):
        if page.locator(".modal.in:visible, .modal.show:visible").count():
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        else:
            break
    page.evaluate(
        "() => { document.querySelectorAll('.modal-backdrop').forEach("
        "b => b.remove()); document.body.classList.remove('modal-open');"
        " document.body.style.removeProperty('overflow'); }")
    page.wait_for_timeout(300)


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

        page.goto(settings.BASE_URL + settings.MODULE_PATHS["all_users"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        dismiss(page)

        sfx = random_suffix()

        # 1. mismatched passwords
        open_create(page)
        fill(page, "Mismatch", "Case", f"mis.{sfx.lower()}@trackerteer.com",
             "Passw0rdOne", "Passw0rdTwo")
        page.locator("#user-edit-save-btn").click()
        page.wait_for_timeout(1500)
        log(f"  [mismatch] feedback={page.evaluate(FEEDBACK_JS)}")
        dismiss(page)

        # 2. missing required fields (no password)
        open_create(page)
        fill(page, "Missing", "Case", f"miss.{sfx.lower()}@trackerteer.com", "", "")
        page.locator("#user-edit-save-btn").click()
        page.wait_for_timeout(1500)
        log(f"  [missing] feedback={page.evaluate(FEEDBACK_JS)}")
        log(f"  [missing] overlay={page.evaluate(OVERLAY_JS)}")
        dismiss(page)
        log(f"  [after dismiss] overlay={page.evaluate(OVERLAY_JS)}")

        # 3. valid create
        open_create(page)
        fill(page, f"Probe{sfx}", "Tester", f"probe.{sfx.lower()}@trackerteer.com",
             "TestPassw0rd!", "TestPassw0rd!")
        page.locator("#user-edit-save-btn").click()
        page.wait_for_timeout(2500)
        log(f"  [valid] feedback={page.evaluate(FEEDBACK_JS)}")
        log(f"  [valid] overlay={page.evaluate(OVERLAY_JS)}")
        dismiss(page)

        # 4. can we still click Create User afterwards?
        try:
            page.get_by_role("button", name="Create User", exact=False).first.click(
                timeout=5000)
            log("  [recreate] Create User clickable after dismiss: YES")
        except Exception as exc:
            log(f"  [recreate] Create User clickable after dismiss: NO "
                f"({str(exc).splitlines()[0]})")
        dismiss(page)

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
