"""DOM probe K - why does #production-lines-modal never open? (TC-OP-008/009)

Probe B clicked #operator-open-production-lines-modal and the modal stayed
hidden. This probe, on a fresh page with no other modal open:
  1. records console errors/pageerrors while clicking the button,
  2. samples #production-lines-modal class/style at 100ms..3s (does it open
     and immediately close, or never open at all?),
  3. dumps the button's attributes (disabled? data-attrs?) and any network
     request fired on click.

Run:  python scripts/probe_mod_k.py
Out:  artifacts/probe_mod_k.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_k.txt"
LINES: list[str] = []


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

        messages: list[str] = []
        page.on("pageerror", lambda e: messages.append(f"pageerror: {e}"))
        page.on("console", lambda m: messages.append(f"console[{m.type}]: {m.text}")
                if m.type == "error" else None)
        requests: list[str] = []
        page.on("request", lambda r: requests.append(r.url)
                if "production" in r.url.lower() or "line" in r.url.lower()
                else None)

        page.goto(settings.BASE_URL + "/en/login", wait_until="domcontentloaded")
        page.locator("#rfid-login-username").fill(settings.LOGIN_EMAIL)
        page.locator("#rfid-login-password").fill(settings.LOGIN_PASSWORD)
        page.locator("button[type=submit]").click()
        page.wait_for_timeout(3500)

        page.goto(settings.BASE_URL + settings.MODULE_PATHS["operator_list"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        btn_info = page.evaluate(
            """() => {
            const b = document.querySelector(
                '#operator-open-production-lines-modal');
            if (!b) return null;
            return {text: b.innerText.trim(), disabled: b.disabled,
                    cls: (b.className || '').slice(0, 70),
                    attrs: [...b.attributes].map(a => a.name + '=' + a.value)};
        }""")
        log(f"  button={btn_info}")

        messages.clear()
        requests.clear()
        page.locator("#operator-open-production-lines-modal").click()
        log("  clicked")

        prev = 0

        for delay in (100, 300, 600, 1000, 2000, 3000):
            page.wait_for_timeout(delay - prev)
            prev = delay
            state = page.evaluate(
                """() => {
                const m = document.querySelector('#production-lines-modal');
                if (!m) return '<missing>';
                return {cls: m.className.slice(0, 80),
                        display: getComputedStyle(m).display,
                        visible: !!(m.offsetWidth || m.offsetHeight)};
            }""")
            log(f"  t={delay}ms modal={state}")

        log(f"  console={messages[:8]}")
        log(f"  requests={requests[:8]}")

        # Second click - maybe the first click only primes something
        messages.clear()
        page.locator("#operator-open-production-lines-modal").click()
        page.wait_for_timeout(1200)
        state2 = page.evaluate(
            """() => {
            const m = document.querySelector('#production-lines-modal');
            return m ? {cls: m.className.slice(0, 80),
                        visible: !!(m.offsetWidth || m.offsetHeight)} : null;
        }""")
        log(f"  after 2nd click modal={state2}")
        log(f"  console after 2nd={messages[:8]}")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
