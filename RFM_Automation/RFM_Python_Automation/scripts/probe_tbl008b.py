"""Focused DOM dump: where is 'Update series' in the TC-TBL-008 flow?

Replicates probe_tbl008 steps 1-4 (two codes, bypass qty, second generate,
first-code qty edit) and then dumps:
  * every id containing 'current-series'
  * #rfid-current-series-update outerHTML (dirty area)
  * every element whose text is 'Update series' (tag/id/class/visibility)
  * status panel outerHTML (truncated)

Run:  python scripts/probe_tbl008b.py
Out:  artifacts/probe_tbl008b.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

CODE_A = "5057877230509"
CODE_B = "5057877257490"

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_tbl008b.txt"
LINES: list[str] = []


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


DOM_DUMP = """() => {
    const vis = el => !!(el.offsetWidth || el.offsetHeight);
    const ids = [...document.querySelectorAll('[id*=current-series]')]
        .map(e => e.id + (vis(e) ? '' : ' [hidden]'));
    const dirty = document.querySelector('#rfid-current-series-update');
    const updateText = [...document.querySelectorAll('button, a, div, span')]
        .filter(e => (e.innerText || '').trim() === 'Update series')
        .map(e => ({tag: e.tagName, id: e.id, cls: (e.className||'').slice(0,60),
                    vis: vis(e)}));
    const refresh = document.querySelector('#rfid-current-series-refresh');
    const panel = document.querySelector('#rfid-current-series-code-list');
    return {
        ids: ids,
        dirtyHTML: dirty ? dirty.outerHTML.slice(0, 1200) : null,
        updateText: updateText,
        refreshExists: !!refresh,
        refreshVisible: refresh ? vis(refresh) : null,
        refreshHTML: refresh ? refresh.outerHTML.slice(0, 400) : null,
        panelHTML: panel ? panel.outerHTML.slice(0, 2500) : null,
    };
}"""


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

        from pages.generator_page import GeneratorPage
        gen = GeneratorPage(page)
        gen.open()

        # steps 1-3: generate A qty2, add "B: 5", generate again
        gen.select_tab(gen.TAB_ITEM_CODE) \
           .enter_item_codes(CODE_A) \
           .set_starting_serial(9600).set_quantity(2) \
           .generate_series().continue_summary()
        page.locator("#rfid-gtin").fill(f"{CODE_A}\n{CODE_B}: 5")
        page.locator("#rfid-gtin").press("Tab")
        page.wait_for_timeout(700)
        gen.generate_series(wait_for_summary=True)
        if gen.summary_visible(timeout=2000):
            gen.continue_summary()
        page.wait_for_timeout(700)

        # step 4: A qty -> 5
        log("--- after step4 (A qty -> 5, Tab blurred) ---")
        gen.set_item_code_qty(CODE_A, 5)
        page.wait_for_timeout(1500)
        info = page.evaluate(DOM_DUMP)
        for k, v in info.items():
            log(f"  {k}: {v}")

        # wait longer, check again (timing?)
        page.wait_for_timeout(2500)
        info2 = page.evaluate(DOM_DUMP)
        log(f"--- +3s refreshExists={info2['refreshExists']} "
            f"refreshVisible={info2['refreshVisible']} "
            f"updateText={info2['updateText']}")

        # does clicking the dirty-area container work instead?
        if info2["updateText"]:
            for t in info2["updateText"]:
                log(f"  candidate: {t}")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
