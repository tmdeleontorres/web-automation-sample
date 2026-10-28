"""DOM probe E - All Users only (create submit id + feedback + Access modal).

Run:  python scripts/probe_mod_e.py
Out:  artifacts/probe_mod_e.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils.helpers import random_suffix  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_e.txt"
LINES: list[str] = []

FEEDBACK_JS = """() => {
  const vis = el => !!(el.offsetWidth || el.offsetHeight);
  const out = [];
  for (const sel of ['.toast', '.alert', '[role=alert]', '.notif',
                     '.swal2-popup', '.modal.show', '.modal.in']) {
    for (const el of document.querySelectorAll(sel)) {
      if (vis(el)) out.push({sel, id: el.id,
        text: (el.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 300)});
    }
  }
  return out;
}"""

MODAL_BUTTONS_JS = """() => {
  const vis = el => !!(el.offsetWidth || el.offsetHeight);
  const m = [...document.querySelectorAll('.modal')]
    .find(x => x.offsetWidth || x.offsetHeight);
  if (!m) return null;
  return {id: m.id,
          buttons: [...m.querySelectorAll('button')].filter(vis)
            .map(b => ({id: b.id, text: b.innerText.trim(),
                        cls: (b.className || '').slice(0, 50),
                        type: b.getAttribute('type') || ''}))};
}"""


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


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

        page.goto(settings.BASE_URL + settings.MODULE_PATHS["all_users"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        role = page.locator("#user-filter-role")
        if role.count():
            opts = role.first.evaluate(
                "s => [...s.options].map(o => o.label + '|' + o.value)")
            log(f"  [users] role options={opts}")

        # Create User modal - submit buttons
        page.get_by_role("button", name="Create User", exact=False).first.click()
        page.wait_for_timeout(900)
        log(f"  [create-user] modal buttons={page.evaluate(MODAL_BUTTONS_JS)}")

        # fill + submit -> feedback
        suffix = random_suffix()
        for sel, val in (("#user-edit-firstname", f"Probe{suffix}"),
                         ("#user-edit-lastname", "Tester"),
                         ("#user-edit-email",
                          f"probe.{suffix.lower()}@trackerteer.com"),
                         ("#user-edit-password", "TestPassw0rd!"),
                         ("#user-edit-password-confirm", "TestPassw0rd!")):
            loc = page.locator(sel)
            if loc.count() and loc.first.is_visible():
                loc.first.fill(val)
            else:
                log(f"    field {sel} missing/hidden")
        # click the visible submit (Create User) inside the open modal
        submit = page.locator(".modal.in button.rfid-gen-btn-primary").first
        log(f"  [create-user] submit text={submit.inner_text()!r}")
        submit.click()
        page.wait_for_timeout(3000)
        log(f"  [create-valid] feedback={page.evaluate(FEEDBACK_JS)}")
        log(f"  [create-valid] modal open count="
            f"{page.locator('.modal.in:visible').count()}")
        page.keyboard.press("Escape")
        page.wait_for_timeout(600)

        # Access modal (read-only)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(2200)
        access = page.locator(
            "table tbody tr:not(.rfid-gen-empty-row) button:has-text('Access')")
        log(f"  [access] Access buttons: {access.count()}")
        if access.count():
            access.first.click()
            page.wait_for_timeout(1200)
            info = page.evaluate(
                """() => {
                const vis = el => !!(el.offsetWidth || el.offsetHeight);
                const m = [...document.querySelectorAll('.modal')]
                  .find(x => x.offsetWidth || x.offsetHeight);
                if (!m) return null;
                return {
                  id: m.id,
                  text: m.innerText.replace(/\\s+/g, ' ').slice(0, 220),
                  radios: [...m.querySelectorAll('input[type=radio]')].map(r => ({
                    name: r.name, value: r.value, checked: r.checked,
                    label: (r.labels && r.labels[0] ? r.labels[0].innerText : '')
                      .replace(/\\s+/g, ' ').slice(0, 40)})),
                  buttons: [...m.querySelectorAll('button')].filter(vis)
                    .map(b => ({id: b.id, text: b.innerText.trim(),
                                cls: (b.className || '').slice(0, 45)})),
                };
            }""")
            log(f"  [access] modal={info}")
            page.keyboard.press("Escape")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
