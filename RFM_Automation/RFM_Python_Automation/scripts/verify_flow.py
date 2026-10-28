"""Selector pass helper #3 - walks the full generate -> summary -> save flow
and records every modal/button/toast it meets, plus the real table ids.

Run:  python scripts/verify_flow.py
Out:  artifacts/verify_flow.txt   (written after every stage)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402
from utils import test_data as data  # noqa: E402

OUT = Path(settings.ARTIFACTS_DIR)
OUT.mkdir(parents=True, exist_ok=True)
OUTFILE = OUT / "verify_flow.txt"

VISIBLE_BUTTONS = """() => [...document.querySelectorAll('button')]
    .filter(b => b.offsetWidth || b.offsetHeight)
    .map(b => ((b.innerText || '').trim() || b.id))"""

VISIBLE_MODALS = """() => [...document.querySelectorAll('.modal, [role=dialog]')]
    .filter(m => m.offsetWidth || m.offsetHeight)
    .map(m => ({id: m.id, title: (m.querySelector('.modal-title') || {}).innerText || '',
                text: (m.innerText || '').trim().slice(0, 160)}))"""

LINES: list[str] = []


def stage(label: str) -> None:
    LINES.append("")
    LINES.append(f"----- {label} -----")
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print("\n".join(LINES[-6:]))


def probe(page, label: str) -> None:
    try:
        modals = page.evaluate(VISIBLE_MODALS)
        buttons = page.evaluate(VISIBLE_BUTTONS)
        LINES.append(f"[{label}] modals  : {modals}")
        LINES.append(f"[{label}] buttons : {buttons}")
    except Exception as exc:
        LINES.append(f"[{label}] probe failed: {exc}")
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")


def close_blocking_modals(page) -> None:
    """Close whatever modal is open (post-save export, confirmation ...)."""
    for sel in ("#rfid-post-save-export-modal .close",
                "#rfid-post-save-export-modal button[data-bs-dismiss=modal]",
                "#rfid-post-save-export-modal button[data-dismiss=modal]",
                ".modal.show .close", ".modal.show [data-dismiss=modal]",
                ".modal.show button"):
        loc = page.locator(sel + ":visible")
        if loc.count():
            try:
                loc.first.click(timeout=3000)
                page.wait_for_timeout(600)
                if not page.locator(".modal.show").count():
                    return
            except Exception:
                continue


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.HEADLESS)
        ctx = browser.new_context(viewport=settings.VIEWPORT, locale=settings.LOCALE,
                                  timezone_id=settings.TIMEZONE)
        page = ctx.new_page()
        page.set_default_timeout(settings.TIMEOUT_MS)

        # ---- login ------------------------------------------------------- #
        page.goto(settings.BASE_URL + "/en/login", wait_until="domcontentloaded")
        page.locator("#rfid-login-username").fill(settings.LOGIN_EMAIL)
        page.locator("#rfid-login-password").fill(settings.LOGIN_PASSWORD)
        page.locator("button[type=submit]").click()
        page.wait_for_timeout(3500)
        assert "rfid_generator" in page.url, f"login failed: {page.url}"
        stage(f"login OK -> {page.url}")

        tables = page.evaluate("""() => [...document.querySelectorAll('table')]
            .map(t => ({id: t.id, headers: [...t.querySelectorAll('thead th')]
                .map(th => th.innerText.trim()).slice(0, 12)}))""")
        LINES.append(f"generator tables: {tables}")

        # ---- generate ----------------------------------------------------- #
        serial, qty = 10200, 2
        page.locator("#rfid-gtin").fill(data.ITEM_CODE_ADDED)
        page.locator("#rfid-serial-start").fill(str(serial))
        page.locator("#rfid-quantity").fill(str(qty))
        page.get_by_role("button", name="Generate Series").click()
        page.wait_for_timeout(2200)
        probe(page, "after Generate")

        # ---- continue ----------------------------------------------------- #
        cont = page.locator("#rfid-confirm-save:visible")
        LINES.append(f"continue(#rfid-confirm-save) visible count = {cont.count()}")
        if cont.count():
            cont.first.click()
            page.wait_for_timeout(1500)
        probe(page, "after Continue")

        # ---- save --------------------------------------------------------- #
        page.locator("#rfid-save-generated").click()
        page.wait_for_timeout(1800)
        probe(page, "after Save click")

        confirm = page.locator("#rfid-confirm-save:visible")
        if confirm.count():
            LINES.append("clicking the save confirmation ...")
            confirm.first.click()
            page.wait_for_timeout(2500)
            probe(page, "after save confirm")

        toast = page.evaluate("""() => {
            for (const s of ['.toast', '.alert', '[role=alert]', '.swal2-popup',
                             '.modal.show', '.rfid-save-success']) {
                const el = document.querySelector(s);
                if (el && (el.offsetWidth || el.offsetHeight))
                    return {sel: s, text: el.innerText.trim().slice(0, 200)};
            }
            return null;
        }""")
        LINES.append(f"toast after save: {toast}")
        OUTFILE.write_text("\n".join(LINES), encoding="utf-8")

        # ---- RFID List ---------------------------------------------------- #
        close_blocking_modals(page)
        stage(f"modals closed, url={page.url}")
        link = page.locator("a").filter(has_text="RFID List").first
        link.click()
        page.wait_for_timeout(2500)
        info = page.evaluate("""() => {
            const t = document.querySelector('table');
            const s = document.querySelector('input[type=search]');
            return {url: location.href,
                    tableId: t ? t.id : null,
                    searchPlaceholder: s ? s.getAttribute('placeholder') : null,
                    lengthId: (document.querySelector('select[id$=_length]') || {}).id || null};
        }""")
        LINES.append(f"RFID List: {info}")
        OUTFILE.write_text("\n".join(LINES), encoding="utf-8")

        browser.close()

    stage("DONE")


if __name__ == "__main__":
    main()
