"""DOM probe J - All Users keyword filter vs create-user validation.

Answers three questions that the failing TC-AU-004/006 tests depend on:

1. Does #user-filter-keyword + Filter actually narrow the table? We search a
   token that cannot exist ("zzznotarealuserzzz") and record the row count.
   If the count does not drop to 0, "row_count()==0" is not a usable signal
   and the negative tests must assert something else.

2. After submitting the create form with MISMATCHED passwords, does the app
   leave an inline error inside #user-edit-modal? We dump the modal's inner
   text and any element carrying an error/validation class.

3. Same for a submit with EMPTY required fields.

Run:  python scripts/probe_mod_j.py
Out:  artifacts/probe_mod_j.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils.helpers import random_suffix  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_j.txt"
LINES: list[str] = []

TABLE_JS = """() => {
  const vis = el => !!(el.offsetWidth || el.offsetHeight);
  const rows = [...document.querySelectorAll(
    'table tbody tr:not(.rfid-gen-empty-row)')].filter(vis);
  return {
    count: rows.length,
    first: rows[0] ? [...rows[0].querySelectorAll('td')]
      .map(td => (td.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 40)) : [],
  };
}"""

ERR_JS = """() => {
  const vis = el => !!(el.offsetWidth || el.offsetHeight);
  const out = [];
  for (const sel of ['.is-invalid', '.invalid-feedback', '.text-danger',
                     '.alert-danger', '[class*=error]', '[class*=invalid]',
                     '[role=alert]', '.rfid-gen-field-error']) {
    for (const el of document.querySelectorAll(sel)) {
      if (vis(el)) out.push({sel, cls: (el.className || '').slice(0, 60),
                             text: (el.innerText || '').trim()
                               .replace(/\\s+/g, ' ').slice(0, 160)});
    }
  }
  return out;
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

        page.goto(settings.BASE_URL + settings.MODULE_PATHS["all_users"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        baseline = page.evaluate(TABLE_JS)
        log(f"  baseline rows={baseline['count']}")

        # 1. filter by a token that cannot exist
        page.locator("#user-filter-keyword").first.fill("zzznotarealuserzzz")
        page.get_by_role("button", name="Filter", exact=False).first.click()
        page.wait_for_timeout(1200)
        filtered = page.evaluate(TABLE_JS)
        log(f"  after impossible-keyword filter rows={filtered['count']}")
        log(f"  first row now={filtered['first']}")

        # reset
        page.locator("#user-filter-keyword").first.fill("")
        page.get_by_role("button", name="Filter", exact=False).first.click()
        page.wait_for_timeout(1200)

        sfx = random_suffix()

        def submit_create(label, first, email, pw, conf):
            page.get_by_role("button", name="Create User",
                             exact=False).first.click()
            page.wait_for_timeout(700)
            if first is not None:
                page.locator("#user-edit-firstname").first.fill(first)
            if email is not None:
                page.locator("#user-edit-email").first.fill(email)
            if pw is not None:
                page.locator("#user-edit-password").first.fill(pw)
            if conf is not None:
                page.locator("#user-edit-password-confirm").first.fill(conf)
            page.locator("#user-edit-save-btn").first.click()
            page.wait_for_timeout(1500)
            errs = page.evaluate(ERR_JS)
            modal_vis = page.locator(".modal:visible").count()
            modal_text = ""
            if modal_vis:
                modal_text = page.locator(".modal:visible").last.inner_text() \
                    .replace("\n", " ")[:400]
            log(f"  [{label}] visible errors={errs}")
            log(f"  [{label}] modal still visible={modal_vis > 0}")
            log(f"  [{label}] modal text={modal_text!r}")
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            page.evaluate(
                "() => { document.querySelectorAll('.modal-backdrop')"
                ".forEach(b => b.remove());"
                " document.body.classList.remove('modal-open'); }")

        # 2. mismatched passwords
        submit_create("mismatched", "Mismatch",
                      f"mismatch{sfx.lower()}@trackerteer.com",
                      "Passw0rdOne", "Passw0rdTwo")

        # 3. empty required fields
        submit_create("empty-required", "Missing",
                      f"missing{sfx.lower()}@trackerteer.com", None, None)

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
