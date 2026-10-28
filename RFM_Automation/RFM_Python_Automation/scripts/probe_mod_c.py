"""DOM probe C - three leftovers from probe_mod_a.

  1. Rewrite RFIDs: FULL text of the "RFID REWRITE" cell (probe_a truncated
     at 30 chars: 'BEFORE E28069150000700A47C4FC9') - where do Current EPCs live?
  2. Style Number List: wait until the async table really finished loading,
     then dump counters/badges (class contains stat/count/summary/badge).
  3. Mother List: open View -> expand the first size group
     (.rfid-mother-size-toggle) -> dump the modal text (child rows columns:
     Date Added / Source / Serial / RFID?).

Run:  python scripts/probe_mod_c.py
Out:  artifacts/probe_mod_c.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_c.txt"
LINES: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


def wait_table(page, timeout: int = 15000) -> bool:
    try:
        page.wait_for_function(
            """() => {
                const loading = document.querySelector(
                    'table tbody tr.rfid-gen-empty-row');
                if (loading && /loading/i.test(loading.innerText)) return false;
                return !!document.querySelector('table tbody');
            }""",
            timeout=timeout,
        )
        return True
    except Exception:
        return False


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

        # ---------------- 1. Rewrite RFID REWRITE cell -------------------- #
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["rewrite_rfids"],
                  wait_until="domcontentloaded")
        ok = wait_table(page)
        log(f"rewrite table ready={ok}")
        cell = page.evaluate(
            """() => {
            const vis = el => !!(el.offsetWidth || el.offsetHeight);
            const tables = [...document.querySelectorAll('table')].filter(vis);
            const t = tables.find(x =>
                x.querySelector('tbody tr:not(.rfid-gen-empty-row)')) || tables[0];
            const heads = [...t.querySelectorAll('thead th')]
                .map(h => h.innerText.trim());
            const idx = heads.findIndex(h => /rfid rewrite/i.test(h));
            const rows = [...document.querySelectorAll(
                'table tbody tr:not(.rfid-gen-empty-row)')];
            return {
              idx,
              values: rows.slice(0, 3).map(r => {
                const td = r.querySelectorAll('td')[idx];
                return td ? td.innerText : null;
              }),
              firstRowFull: rows[0] ? [...rows[0].querySelectorAll('td')]
                .map((c, i) => heads[i] + ' => ' + c.innerText.replace(/\\s+/g, ' | '))
                : [],
            };
        }""")
        log(f"  rewrite idx={cell['idx']}")
        for v in cell["values"]:
            log(f"  REWRITE cell raw={v!r}")
        for line in cell["firstRowFull"]:
            log(f"    {line}")

        # ---------------- 2. Style counters (loaded table) ---------------- #
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["style_number_list"],
                  wait_until="domcontentloaded")
        ok = wait_table(page)
        rows = page.locator(
            "table tbody tr:not(.rfid-gen-empty-row)").count()
        log(f"style table ready={ok} rows={rows}")
        counters = page.evaluate(
            """() => {
            const vis = el => !!(el.offsetWidth || el.offsetHeight);
            const hits = [...document.querySelectorAll(
              '[class*=stat], [class*=count], [class*=summary], [class*=badge], ' +
              '[class*=counter], [class*=tile]')]
              .filter(vis)
              .map(e => ({tag: e.tagName, cls: (e.className || '').toString().slice(0, 60),
                          text: (e.innerText || '').replace(/\\s+/g, ' ').slice(0, 100)}));
            const syncText = [...document.querySelectorAll('*')]
              .filter(e => vis(e) && e.children.length <= 3
                           && /synced|not synced/i.test(e.innerText || '')
                           && !['SELECT', 'OPTION'].includes(e.tagName))
              .slice(0, 12)
              .map(e => ({tag: e.tagName, id: e.id,
                          cls: (e.className || '').toString().slice(0, 50),
                          text: (e.innerText || '').replace(/\\s+/g, ' ').slice(0, 100)}));
            const tables = [...document.querySelectorAll('table')].filter(vis);
            const t = tables.find(x =>
                x.querySelector('tbody tr:not(.rfid-gen-empty-row)')) || tables[0];
            const headers = [...t.querySelectorAll('thead th')]
              .map(h => h.innerText.trim());
            const firstRow = (() => {
              const r = document.querySelector(
                'table tbody tr:not(.rfid-gen-empty-row)');
              return r ? [...r.querySelectorAll('td')]
                .map(c => c.innerText.replace(/\\s+/g, ' | ').slice(0, 60)) : [];
            })();
            const rowButtons = (() => {
              const r = document.querySelector(
                'table tbody tr:not(.rfid-gen-empty-row)');
              return r ? [...r.querySelectorAll('button, a.btn, [title]')].map(b => ({
                tag: b.tagName, text: (b.innerText || '').trim().slice(0, 20),
                title: b.getAttribute('title') || '',
                cls: (b.className || '').toString().slice(0, 50)})) : [];
            })();
            return {hits, syncText, headers, firstRow, rowButtons};
        }""")
        log(f"  style headers={counters['headers']}")
        log(f"  style firstRow={counters['firstRow']}")
        log(f"  style rowButtons={counters['rowButtons']}")
        for h in counters["hits"]:
            log(f"  style-badge: {h}")
        for h in counters["syncText"]:
            log(f"  style-sync-text: {h}")

        # ---------------- 3. Mother details + size expansion --------------- #
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["mother_list"],
                  wait_until="domcontentloaded")
        ok = wait_table(page)
        log(f"mother table ready={ok}")
        view = page.locator(
            "table tbody tr:not(.rfid-gen-empty-row)").first.get_by_role(
            "button", name="View", exact=False)
        if view.count():
            view.first.click()
            page.wait_for_timeout(1200)
            before = page.evaluate(
                """() => {
                const m = [...document.querySelectorAll('.modal')]
                  .find(x => x.offsetWidth || x.offsetHeight);
                return m ? m.innerText.replace(/\\s+/g, ' ').slice(0, 400) : null;
            }""")
            log(f"  mother modal (collapsed): {before!r}")
            toggles = page.locator(".rfid-mother-size-toggle:visible")
            log(f"  size toggles visible: {toggles.count()}")
            if toggles.count():
                toggles.first.click()
                page.wait_for_timeout(1000)
            after = page.evaluate(
                """() => {
                const m = [...document.querySelectorAll('.modal')]
                  .find(x => x.offsetWidth || x.offsetHeight);
                return m ? m.innerText.replace(/\\s+/g, ' ') : null;
            }""")
            log(f"  mother modal (expanded): {after!r}")
            close = page.evaluate(
                """() => {
                const vis = el => !!(el.offsetWidth || el.offsetHeight);
                const m = [...document.querySelectorAll('.modal')].filter(vis);
                const mm = m[m.length - 1];
                if (!mm) return null;
                return {id: mm.id,
                        btns: [...mm.querySelectorAll('button')].filter(vis)
                          .map(b => ({cls: (b.className || '').slice(0, 40),
                                      aria: b.getAttribute('aria-label') || '',
                                      text: b.innerText.trim().slice(0, 20)}))};
            }""")
            log(f"  mother modal close candidates: {close}")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
