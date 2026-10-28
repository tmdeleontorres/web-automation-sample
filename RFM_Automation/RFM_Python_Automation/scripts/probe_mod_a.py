"""DOM probe A - tables, filters, row actions and dialogs on the list modules.

For each of Recent Generated / Style Number List / Mother List /
Rewrite RFIDs / Item Code Mismatch it dumps:
  * every visible table (id, headers, first-row cells, first-row buttons)
  * every visible <select> (id, label, options)
  * the Respipe support widget ancestry (needed to exclude it from modal())
  * after clicking the module's row action: every modal/dialog candidate
    (id/class/role/visible/text) and the visible modal's close controls
Extra: recent quick-search behaviour, style "Synced" counters, rewrite Logs.

Run:  python scripts/probe_mod_a.py
Out:  artifacts/probe_mod_a.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_a.txt"
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
    firstRowButtons: (() => {
      const r = t.querySelector('tbody tr:not(.rfid-gen-empty-row)');
      if (!r) return [];
      return [...r.querySelectorAll('button, a.btn, a[role=button], [title]')].map(b => ({
        tag: b.tagName, text: (b.innerText || '').trim().slice(0, 20),
        title: b.getAttribute('title') || '', aria: b.getAttribute('aria-label') || '',
        cls: (b.className || '').toString().slice(0, 50)}));
    })(),
  }))"""

SELECTS_JS = """() => [...document.querySelectorAll('select')]
  .filter(s => s.offsetWidth || s.offsetHeight)
  .slice(0, 15)
  .map(s => ({
    id: s.id, name: s.name || '', aria: s.getAttribute('aria-label') || '',
    label: (s.labels && s.labels[0] ? s.labels[0].innerText : '').trim().slice(0, 30),
    options: [...s.options].map(o => (o.label || o.text) + '|' + o.value).slice(0, 15),
  }))"""

WIDGET_JS = """() => {
  const inner = [...document.querySelectorAll('*')]
    .filter(e => /Powered by Respipe/i.test(e.textContent || '') && e.children.length <= 6);
  if (!inner.length) return null;
  let out = [], n = inner[inner.length - 1];
  for (let k = 0; k < 7 && n; k++, n = n.parentElement) {
    out.push({tag: n.tagName, id: n.id,
              cls: (n.className || '').toString().slice(0, 70),
              role: n.getAttribute('role')});
  }
  return out;
}"""

DIALOGS_JS = """() => [...document.querySelectorAll('.modal, .modal.show, .modal.in, [role=dialog]')]
  .map(m => ({
    tag: m.tagName, id: m.id,
    cls: (m.className || '').toString().slice(0, 80),
    role: m.getAttribute('role'),
    vis: !!(m.offsetWidth || m.offsetHeight),
    text: (m.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 300),
  }))"""

CLOSE_JS = """() => {
  const vis = el => !!(el.offsetWidth || el.offsetHeight);
  const open = [...document.querySelectorAll('.modal.show, .modal.in, .modal, [role=dialog]')]
    .filter(m => vis(m));
  const m = open[open.length - 1];
  if (!m) return null;
  const btns = [...m.querySelectorAll('button, [role=button], a')].filter(vis)
    .map(b => ({tag: b.tagName, cls: (b.className || '').toString().slice(0, 50),
                aria: b.getAttribute('aria-label') || '',
                text: (b.innerText || '').trim().slice(0, 25)}));
  return {modal: {id: m.id, cls: (m.className || '').toString().slice(0, 80)}, btns};
}"""


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


def dump_page(page, label: str) -> None:
    log(f"--- {label} ---")
    for t in page.evaluate(TABLES_JS):
        log(f"  table id={t['id']!r} cls={t['cls']!r}")
        log(f"    headers={t['headers']}")
        log(f"    firstRow={t['firstRow']}")
        log(f"    firstRowButtons={t['firstRowButtons']}")
    for s in page.evaluate(SELECTS_JS):
        log(f"  select id={s['id']!r} name={s['name']!r} aria={s['aria']!r} "
            f"label={s['label']!r} options={s['options']}")


def dump_dialogs(page, label: str) -> None:
    for d in page.evaluate(DIALOGS_JS):
        log(f"  [{label}] dialog <{d['tag']} id={d['id']!r} cls={d['cls']!r} "
            f"role={d['role']!r} vis={d['vis']}> text={d['text']!r}")
    log(f"  [{label}] visible-close={page.evaluate(CLOSE_JS)}")


def click_row_action(page, row: int, names: list[str]) -> str | None:
    r = page.locator("table tbody tr:not(.rfid-gen-empty-row)").nth(row)
    for name in names:
        loc = r.get_by_role("button", name=name, exact=False)
        if not loc.count():
            loc = r.locator(f"button:has-text('{name}')")
        if not loc.count():
            loc = r.get_by_text(name, exact=True)
        if loc.count():
            try:
                loc.first.click(timeout=4000)
                return name
            except Exception as exc:
                log(f"    click {name!r} failed: {str(exc).splitlines()[0]}")
    return None


def close_dialog(page) -> None:
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)


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

        pages = [
            ("recent", settings.MODULE_PATHS["recent_generated"],
             ["Action", "History", "View", "Transaction"]),
            ("style", settings.MODULE_PATHS["style_number_list"], ["View", "Details"]),
            ("mother", settings.MODULE_PATHS["mother_list"], ["View", "Details"]),
            ("rewrite", settings.MODULE_PATHS["rewrite_rfids"], ["View", "Details"]),
            ("mismatch", settings.MODULE_PATHS["item_code_mismatch"], []),
        ]

        widget_dumped = False
        for name, path, actions in pages:
            page.goto(settings.BASE_URL + path, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            dump_page(page, name)
            if not widget_dumped:
                log(f"  widget ancestry: {page.evaluate(WIDGET_JS)}")
                widget_dumped = True

            if name == "recent":
                # quick-search behaviour
                box = page.locator("table:visible input[type=search]")
                log(f"  quick search inputs in visible table: {box.count()}")
                if box.count():
                    before = page.locator(
                        "table tbody tr:not(.rfid-gen-empty-row)").count()
                    box.first.fill("zzz-no-such-record-zzz")
                    page.wait_for_timeout(900)
                    during = page.locator(
                        "table tbody tr:not(.rfid-gen-empty-row)").count()
                    box.first.fill("")
                    page.wait_for_timeout(900)
                    after = page.locator(
                        "table tbody tr:not(.rfid-gen-empty-row)").count()
                    log(f"  quick-search rows: before={before} "
                        f"filtered={during} cleared={after}")

            if actions:
                clicked = click_row_action(page, 0, actions)
                page.wait_for_timeout(1200)
                log(f"  clicked row action: {clicked!r}")
                dump_dialogs(page, f"{name}-action")
                close_dialog(page)
                if name == "rewrite":
                    # second action (Logs)
                    clicked2 = click_row_action(page, 0, ["Logs"])
                    page.wait_for_timeout(1200)
                    log(f"  clicked row action2: {clicked2!r}")
                    dump_dialogs(page, "rewrite-logs")
                    close_dialog(page)

            if name == "mismatch":
                row = page.locator("table tbody tr:not(.rfid-gen-empty-row)")
                if row.count():
                    link = row.first.locator("td a, td button")
                    log(f"  mismatch row links/buttons: {link.count()}")
                    if link.count():
                        link.first.click()
                        page.wait_for_timeout(1200)
                        dump_dialogs(page, "mismatch-open")
                        close_dialog(page)

            if name == "style":
                hits = page.evaluate(
                    """() => [...document.querySelectorAll('*')]
                    .filter(e => /synced/i.test(e.innerText || '')
                                 && e.children.length <= 4
                                 && (e.offsetWidth || e.offsetHeight))
                    .slice(0, 10)
                    .map(e => ({tag: e.tagName, id: e.id,
                                cls: (e.className || '').toString().slice(0, 50),
                                text: (e.innerText || '').replace(/\\s+/g, ' ').slice(0, 90),
                                parent: (e.parentElement?.innerText || '')
                                  .replace(/\\s+/g, ' ').slice(0, 90)}))""")
                for h in hits:
                    log(f"  style-synced hit: {h}")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
