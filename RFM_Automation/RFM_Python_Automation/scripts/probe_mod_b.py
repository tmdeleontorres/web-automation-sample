"""DOM probe B - forms on Operator List and All Users.

Operator List:
  * #operator-filter-status options (apply_filters uses label=Active)
  * Add Operators form: inputs/selects (id, label, placeholder, maxlength,
    visibility), the Section select options, the "Waiting for name" indicator
  * Production Lines: what dialog opens, #production-line-name visibility,
    #production-line-save text/visibility
  * Edit row action -> dialog structure (close controls)
  * User RFID column: all visible tables + their headers (header_index may
    pick the wrong table)
All Users:
  * first row toggle/checkbox markup (toggle_rfm_admin selector)
  * Create User modal: are #user-edit-* ids present, close controls
  * feedback after a valid create: modals / toasts / alerts text

Run:  python scripts/probe_mod_b.py
Out:  artifacts/probe_mod_b.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils.helpers import random_suffix  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_b.txt"
LINES: list[str] = []

TABLES_JS = """() => [...document.querySelectorAll('table')]
  .filter(t => t.offsetWidth || t.offsetHeight)
  .map(t => ({
    id: t.id, cls: (t.className || '').toString().slice(0, 60),
    headers: [...t.querySelectorAll('thead th')]
      .map(h => (h.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 40)),
    firstRow: (() => {
      const r = t.querySelector('tbody tr:not(.rfid-gen-empty-row)');
      return r ? [...r.querySelectorAll('td')]
        .map(c => (c.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 30)) : [];
    })(),
    firstRowControls: (() => {
      const r = t.querySelector('tbody tr:not(.rfid-gen-empty-row)');
      if (!r) return [];
      return [...r.querySelectorAll(
        'button, input, a.btn, [role=button], [title], .toggle, .switch')]
        .map(b => ({tag: b.tagName, type: b.getAttribute('type') || '',
                    text: (b.innerText || '').trim().slice(0, 20),
                    title: b.getAttribute('title') || '',
                    aria: b.getAttribute('aria-label') || '',
                    cls: (b.className || '').toString().slice(0, 50)}));
    })(),
  }))"""

FORM_JS = """() => {
  const vis = el => !!(el.offsetWidth || el.offsetHeight);
  const fields = [...document.querySelectorAll('input, select, textarea')]
    .map(f => ({
      tag: f.tagName, type: f.getAttribute('type') || '', id: f.id,
      name: f.name || '',
      label: (f.labels && f.labels[0] ? f.labels[0].innerText : '').trim().slice(0, 30),
      aria: f.getAttribute('aria-label') || '',
      placeholder: f.getAttribute('placeholder') || '',
      maxlength: f.getAttribute('maxlength'),
      visible: vis(f),
    }));
  const buttons = [...document.querySelectorAll('button')].filter(vis)
    .map(b => ({id: b.id, cls: (b.className || '').toString().slice(0, 50),
                type: b.getAttribute('type') || '',
                text: (b.innerText || '').trim().slice(0, 30),
                aria: b.getAttribute('aria-label') || ''}));
  const indicators = [...document.querySelectorAll('*')]
    .filter(e => /waiting for name/i.test(e.innerText || '')
                 && e.children.length <= 4)
    .slice(0, 5)
    .map(e => ({tag: e.tagName, id: e.id, cls: (e.className || '').toString().slice(0, 50),
                visible: vis(e),
                text: (e.innerText || '').replace(/\\s+/g, ' ').slice(0, 80)}));
  return {fields, buttons, indicators};
}"""

DIALOGS_JS = """() => [...document.querySelectorAll('.modal, .modal.show, .modal.in, [role=dialog]')]
  .map(m => ({
    tag: m.tagName, id: m.id,
    cls: (m.className || '').toString().slice(0, 80),
    role: m.getAttribute('role'),
    vis: !!(m.offsetWidth || m.offsetHeight),
    text: (m.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 350),
    closeBtns: [...m.querySelectorAll('button, [role=button]')]
      .filter(b => !!(b.offsetWidth || b.offsetHeight))
      .map(b => ({cls: (b.className || '').toString().slice(0, 40),
                  aria: b.getAttribute('aria-label') || '',
                  text: (b.innerText || '').trim().slice(0, 25)}))
      .slice(0, 8),
  }))"""

FEEDBACK_JS = """() => {
  const vis = el => !!(el.offsetWidth || el.offsetHeight);
  const out = [];
  for (const sel of ['.toast', '.alert', '[role=alert]', '.notif', '.swal2-popup',
                     '.modal.show', '#rfid-post-save-export-modal']) {
    for (const el of document.querySelectorAll(sel)) {
      if (vis(el)) out.push({sel, text: (el.innerText || '')
        .trim().replace(/\\s+/g, ' ').slice(0, 250)});
    }
  }
  return out;
}"""


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


def dump_tables(page, label: str) -> None:
    for t in page.evaluate(TABLES_JS):
        log(f"  [{label}] table id={t['id']!r} cls={t['cls']!r}")
        log(f"    headers={t['headers']}")
        log(f"    firstRow={t['firstRow']}")
        log(f"    firstRowControls={t['firstRowControls']}")


def dump_dialogs(page, label: str) -> None:
    for d in page.evaluate(DIALOGS_JS):
        log(f"  [{label}] dialog <{d['tag']} id={d['id']!r} cls={d['cls']!r} "
            f"role={d['role']!r} vis={d['vis']}>")
        log(f"    text={d['text']!r}")
        log(f"    closeBtns={d['closeBtns']}")


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

        # ------------------------------------------------------------------ #
        # Operator List
        # ------------------------------------------------------------------ #
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["operator_list"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        log("=== OPERATOR LIST ===")
        dump_tables(page, "operators")

        status_sel = page.locator("#operator-filter-status")
        if status_sel.count():
            opts = status_sel.first.evaluate(
                "s => [...s.options].map(o => o.label + '|' + o.value)")
            log(f"  #operator-filter-status options={opts}")

        # Add Operators form
        add_btn = page.get_by_role("button", name="Add Operators", exact=False)
        if add_btn.count():
            add_btn.first.click()
            page.wait_for_timeout(800)
            info = page.evaluate(FORM_JS)
            log(f"  [add-operators] fields={info['fields']}")
            log(f"  [add-operators] buttons={info['buttons']}")
            log(f"  [add-operators] indicators={info['indicators']}")
            dump_dialogs(page, "add-operators")

        # Production Lines
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        pl_btn = page.get_by_role("button", name="Production Lines", exact=False)
        if pl_btn.count():
            pl_btn.first.click()
            page.wait_for_timeout(900)
            dump_dialogs(page, "production-lines")
            info = page.evaluate(FORM_JS)
            log(f"  [production-lines] fields={info['fields']}")
            log(f"  [production-lines] buttons={info['buttons']}")
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        # Edit row action
        row = page.locator("table tbody tr:not(.rfid-gen-empty-row)")
        if row.count():
            edit = row.first.get_by_role("button", name="Edit", exact=False)
            if not edit.count():
                edit = row.first.locator("button:has-text('Edit')")
            if not edit.count():
                edit = row.first.get_by_text("Edit", exact=True)
            if edit.count():
                edit.first.click()
                page.wait_for_timeout(1000)
                dump_dialogs(page, "edit-operator")
            else:
                log("  [edit-operator] no Edit control in row 0")
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        # ------------------------------------------------------------------ #
        # All Users
        # ------------------------------------------------------------------ #
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["all_users"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        log("=== ALL USERS ===")
        dump_tables(page, "users")

        cu_btn = page.get_by_role("button", name="Create User", exact=False)
        if cu_btn.count():
            cu_btn.first.click()
            page.wait_for_timeout(900)
            dump_dialogs(page, "create-user")
            info = page.evaluate(FORM_JS)
            log(f"  [create-user] fields={info['fields']}")

            # fill a valid form and submit -> what feedback appears?
            suffix = random_suffix()
            vals = {
                "#user-edit-firstname": f"Probe{suffix}",
                "#user-edit-lastname": "Tester",
                "#user-edit-email": f"probe.{suffix.lower()}@trackerteer.com",
                "#user-edit-password": "TestPassw0rd!",
                "#user-edit-password-confirm": "TestPassw0rd!",
            }
            for sel, val in vals.items():
                loc = page.locator(sel)
                if loc.count():
                    loc.first.fill(val)
                else:
                    log(f"    MISSING field {sel}")
            save = page.locator("#user-edit-save")
            if save.count() and save.first.is_visible():
                save.first.click()
            else:
                page.get_by_role("button", name="Save", exact=False).last.click()
            page.wait_for_timeout(2500)
            log(f"  [create-user feedback] {page.evaluate(FEEDBACK_JS)}")
            dump_dialogs(page, "create-user-after")
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
