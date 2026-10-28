"""Find the current Update-series control (id may have changed / subtree broken).

Captures pageerrors + console, then dumps after generate and after a qty edit:
  * every button/link/[role=button] (id, text, visibility)
  * every element with id/class containing update|refresh|dirty|pending
  * loose text matches for 'Update series' / 'Quantity changed'
  * entry + badge outerHTML (is the 'Update' badge interactive?)
Then, if a candidate exists, tries clicking it and reports the effect.

Run:  python scripts/probe_tbl008d.py
Out:  artifacts/probe_tbl008d.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

CODE_A = "5057877230509"

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_tbl008d.txt"
LINES: list[str] = []
EVENTS: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


DUMP_JS = """() => {
    const vis = el => !!(el.offsetWidth || el.offsetHeight);
    const all = [...document.querySelectorAll(
        'button, a, [role=button], [onclick], input[type=button]')];
    const buttons = all.map(b => ({
        id: b.id || '', cls: (b.className || '').toString().slice(0, 40),
        text: (b.innerText || b.value || '').trim().slice(0, 30),
        vis: vis(b)
    })).filter(b => b.text || b.id);
    const wide = [...document.querySelectorAll(
        '[id*=update], [id*=refresh], [id*=dirty], [id*=pending],' +
        ' [class*=update], [class*=refresh], [class*=dirty], [class*=pending]')]
        .map(e => ({tag: e.tagName, id: e.id, cls: (e.className||'').toString().slice(0,50),
                    text: (e.innerText||'').trim().slice(0, 40), vis: vis(e)}));
    const textHits = [...document.querySelectorAll('*')]
        .filter(e => /update series|quantity changed/i.test(e.textContent || '')
                     && e.children.length <= 3)
        .slice(0, 12)
        .map(e => ({tag: e.tagName, id: e.id, cls: (e.className||'').toString().slice(0,50),
                    text: (e.innerText||'').trim().slice(0, 50), vis: vis(e)}));
    const badge = document.querySelector('.rfid-current-series-code-status.is-pending');
    const entry = document.querySelector('.rfid-current-series-code');
    const rows = document.querySelectorAll(
        'table.rfid-gen-table tbody tr:not(.rfid-gen-empty-row)').length;
    return {buttons, wide, textHits, rows,
            badgeHTML: badge ? badge.outerHTML : null,
            entryHTML: entry ? entry.outerHTML.slice(0, 500) : null,
            counters: (document.body.innerText.match(
                /TOTAL GENERATED[\\s\\S]{0,20}/) || [''])[0].replace(/\\n/g, ' ')};
}"""


def dump(page, label: str) -> dict:
    info = page.evaluate(DUMP_JS)
    log(f"  [{label}] rows={info['rows']} counters={info['counters']!r}")
    log(f"    badge={info['badgeHTML']}")
    log(f"    wide={info['wide']}")
    log(f"    textHits={info['textHits']}")
    log(f"    buttons={[b for b in info['buttons'] if b['vis'] or 'upd' in (b['id']+b['cls']).lower()]}")
    if info["entryHTML"]:
        log(f"    entry={info['entryHTML']}")
    return info


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.HEADLESS)
        page = browser.new_context(viewport=settings.VIEWPORT,
                                   locale=settings.LOCALE).new_page()
        page.set_default_timeout(settings.TIMEOUT_MS)

        page.on("pageerror",
                lambda e: EVENTS.append(f"PAGEERROR: {str(e)[:160]}"))
        page.on("console",
                lambda m: EVENTS.append(f"CONSOLE.{m.type}: {m.text[:140]}")
                if m.type in ("error", "warning") else None)

        page.goto(settings.BASE_URL + "/en/login", wait_until="domcontentloaded")
        page.locator("#rfid-login-username").fill(settings.LOGIN_EMAIL)
        page.locator("#rfid-login-password").fill(settings.LOGIN_PASSWORD)
        page.locator("button[type=submit]").click()
        page.wait_for_timeout(3500)
        log(f"login -> {page.url}")

        from pages.generator_page import GeneratorPage
        gen = GeneratorPage(page)
        gen.open()

        gen.select_tab(gen.TAB_ITEM_CODE) \
           .enter_item_codes(CODE_A) \
           .set_starting_serial(9700).set_quantity(4) \
           .generate_series(wait_for_summary=True)
        EVENTS.clear()                          # only errors from continue onward
        if gen.summary_visible(timeout=2000):
            gen.continue_summary()
        page.wait_for_timeout(1000)
        dump(page, "S1 after generate")
        log(f"    events(S1)={EVENTS}")

        gen.set_item_code_qty(CODE_A, 6)
        page.wait_for_timeout(800)
        info = dump(page, "S2 qty 4->6 blurred")
        log(f"    events(S2)={EVENTS}")

        # candidate click order: text-button first, then the badge
        clicked = None
        for cand in info["textHits"]:
            if not cand["vis"]:
                continue
            sel = (f"#{cand['id']}" if cand["id"]
                   else f".{str(cand['cls']).split()[0]}" if cand["cls"] else None)
            if not sel:
                continue
            loc = page.locator(sel)
            if loc.count() and loc.first.is_visible():
                try:
                    loc.first.click(timeout=3000)
                    clicked = sel
                    break
                except Exception as exc:
                    log(f"    click {sel} failed: {str(exc).splitlines()[0]}")
        if clicked is None and page.locator(
                ".rfid-current-series-code-status.is-pending").count():
            page.locator(".rfid-current-series-code-status.is-pending").first.click(timeout=3000)
            clicked = "badge.is-pending"
        page.wait_for_timeout(2000)
        log(f"    clicked={clicked}")
        dump(page, "S3 after candidate click")
        log(f"    events(S3)={EVENTS}")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
