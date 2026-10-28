"""DOM probe D - Operator form behaviour + All Users create/access flows.

Operator List (fresh page load, no modal left open):
  1. Add Operators modal: first-row controls (ids/classes of the name inputs,
     Section select options, User Email select options), the CHECK cell text
     with empty rows and after filling first+last name (defines
     check_indicator: 'Waiting for name' vs 'ready').
  2. Save Operators with EMPTY names -> what feedback appears (toast/alert/
     modal text) - defines TC-OP-003's negative assertion.
  3. Production Lines: from a fresh page click the toolbar button and dump
     whether #production-lines-modal actually opens (+console errors).
     If it opens: empty "Add Line" click -> feedback (TC-OP-009).

All Users:
  4. #user-filter-role options.
  5. Create User modal: exact id/class of the visible submit button.
  6. Valid create -> feedback (toast? modal closes? new row?).
  7. Access modal (row "Access" button): radios (Admin/User), Save Access
     button id - read-only, no save performed.

Run:  python scripts/probe_mod_d.py
Out:  artifacts/probe_mod_d.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils.helpers import random_suffix  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_d.txt"
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

ROW_JS = """() => {
  const modal = [...document.querySelectorAll('.modal')]
    .find(m => m.offsetWidth || m.offsetHeight);
  if (!modal) return null;
  const table = modal.querySelector('table');
  if (!table) return {note: 'no table in modal'};
  const row = table.querySelector('tbody tr');
  const cells = row ? [...row.querySelectorAll('td')]
    .map((td, i) => ({i, text: td.innerText.trim().replace(/\\s+/g, ' ').slice(0, 40),
                      html: td.innerHTML.replace(/\\s+/g, ' ').slice(0, 180)})) : [];
  const controls = row ? [...row.querySelectorAll('input, select, button')].map(c => ({
    tag: c.tagName, type: c.getAttribute('type') || '', id: c.id,
    cls: (c.className || '').toString().slice(0, 45),
    placeholder: c.getAttribute('placeholder') || '',
    maxlength: c.getAttribute('maxlength'),
    options: c.tagName === 'SELECT'
      ? [...c.options].map(o => o.label + '|' + o.value).slice(0, 20) : undefined,
    value: c.tagName === 'SELECT' ? undefined : c.value,
    visible: !!(c.offsetWidth || c.offsetHeight),
  })) : [];
  return {cells, controls};
}"""


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


def dump_feedback(page, label: str) -> None:
    log(f"  [{label}] feedback={page.evaluate(FEEDBACK_JS)}")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.HEADLESS)
        page = browser.new_context(viewport=settings.VIEWPORT,
                                   locale=settings.LOCALE).new_page()
        page.set_default_timeout(settings.TIMEOUT_MS)

        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: errors.append(f"console[{m.type}]: {m.text}")
                if m.type in ("error",) else None)

        page.goto(settings.BASE_URL + "/en/login", wait_until="domcontentloaded")
        page.locator("#rfid-login-username").fill(settings.LOGIN_EMAIL)
        page.locator("#rfid-login-password").fill(settings.LOGIN_PASSWORD)
        page.locator("button[type=submit]").click()
        page.wait_for_timeout(3500)
        log(f"login -> {page.url}")

        # ------------------------------------------------------------------ #
        # Operator List
        # ------------------------------------------------------------------ #
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["operator_list"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        # 1. Add Operators - row structure (empty state)
        page.get_by_role("button", name="Add Operators", exact=False).first.click()
        page.wait_for_timeout(800)
        log(f"  [add empty row] {page.evaluate(ROW_JS)}")

        # fill first+last name -> CHECK cell now?
        modal_row = page.locator(".modal:visible table tbody tr").first
        inputs = modal_row.locator("input[type=text]")
        log(f"  text inputs in row: {inputs.count()}")
        if inputs.count() >= 2:
            inputs.nth(0).fill("ProbeQA")
            inputs.nth(1).fill("Indicator")
            page.wait_for_timeout(500)
        log(f"  [add filled row] {page.evaluate(ROW_JS)}")
        indicator_hits = page.evaluate(
            """() => {
            const vis = el => !!(el.offsetWidth || el.offsetHeight);
            return [...document.querySelectorAll('.modal *')]
              .filter(e => vis(e) && e.children.length <= 2
                           && /waiting|ready|valid|invalid|check/i.test(
                                e.innerText || ''))
              .slice(0, 12)
              .map(e => ({tag: e.tagName, cls: (e.className || '').toString().slice(0, 45),
                          text: (e.innerText || '').replace(/\\s+/g, ' ').slice(0, 60)}));
        }""")
        log(f"  [add filled] check-ish elements: {indicator_hits}")
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        # 2. Empty-name save behaviour
        page.get_by_role("button", name="Add Operators", exact=False).first.click()
        page.wait_for_timeout(700)
        page.locator("#operator-save-btn").click()
        page.wait_for_timeout(1500)
        dump_feedback(page, "empty-save")
        log(f"  [empty-save] rows now: "
            f"{page.locator('.modal:visible table tbody tr').count()}")
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        # 3. Production Lines (fresh page, no other modal open)
        errors.clear()
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        page.locator("#operator-open-production-lines-modal").click()
        page.wait_for_timeout(1800)
        pl_visible = page.locator("#production-lines-modal").is_visible()
        log(f"  [production-lines] modal visible after toolbar click: {pl_visible}")
        log(f"  [production-lines] console: {errors[:6]}")
        if pl_visible:
            log(f"  [production-lines] text="
                f"{page.locator('#production-lines-modal').inner_text()[:300]!r}")
            add = page.locator("#production-lines-modal button:has-text('Add Line')")
            log(f"  [production-lines] Add Line buttons: {add.count()}")
            if add.count():
                add.first.click()
                page.wait_for_timeout(1200)
                dump_feedback(page, "empty-line")
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        # ------------------------------------------------------------------ #
        # All Users
        # ------------------------------------------------------------------ #
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["all_users"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        role = page.locator("#user-filter-role")
        if role.count():
            opts = role.first.evaluate(
                "s => [...s.options].map(o => o.label + '|' + o.value)")
            log(f"  [users] role options={opts}")

        # 5. Create User modal - submit button id
        page.get_by_role("button", name="Create User", exact=False).first.click()
        page.wait_for_timeout(900)
        submit = page.locator(".modal.in button[type=submit], "
                              ".modal.in button.rfid-gen-btn-primary")
        log(f"  [create-user] visible submit candidates: "
            f"{submit.all_inner_texts()}")
        ids = page.evaluate(
            """() => {
            const vis = el => !!(el.offsetWidth || el.offsetHeight);
            const m = [...document.querySelectorAll('.modal')]
              .find(x => x.offsetWidth || x.offsetHeight);
            if (!m) return null;
            return [...m.querySelectorAll('button')]
              .filter(vis)
              .map(b => ({id: b.id, text: b.innerText.trim(),
                          cls: (b.className || '').slice(0, 50),
                          type: b.getAttribute('type') || ''}));
        }""")
        log(f"  [create-user] modal buttons={ids}")

        # 6. Valid create -> feedback
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
        submit.first.click()
        page.wait_for_timeout(3000)
        dump_feedback(page, "create-valid")
        log(f"  [create-valid] modal still open: "
            f"{page.locator('.modal.in:visible').count() > 0}")
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        # 7. Access modal (read-only)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        access = page.locator("table tbody tr:not(.rfid-gen-empty-row) "
                              "button:has-text('Access')")
        log(f"  [access] Access buttons: {access.count()}")
        if access.count():
            access.first.click()
            page.wait_for_timeout(1000)
            info = page.evaluate(
                """() => {
                const vis = el => !!(el.offsetWidth || el.offsetHeight);
                const m = [...document.querySelectorAll('.modal')]
                  .find(x => x.offsetWidth || x.offsetHeight);
                if (!m) return null;
                return {
                  id: m.id,
                  text: m.innerText.replace(/\\s+/g, ' ').slice(0, 250),
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
