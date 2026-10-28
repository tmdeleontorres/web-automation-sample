"""DOM probe N - measure quick-search FILTER LATENCY (fixes rg_002b/rw_003).

Probe M showed search state depends on wait time: Recent filtered within
2000 ms (probe L) but not within 1500 ms (probe M), while table_search()
waits only 500 ms - too short.  RFID List has 1,150,551 client-side rows,
so its filter may take many seconds.

probe N polls the DataTables info line + row count every 250 ms and records
HOW LONG filtering/clearing actually takes:

  Recent Generated : impossible term -> time to "0 of 0"; clear -> time to
                     "Showing 1 to 2 of 2"
  RFID List        : (a) real term   = first 8 chars of first-page RFID
                     (b) old EPC from the Rewrite page's BEFORE line
                     each: time until info/rows change; then clear
  Style/Transaction: goto timeout raised to 60 s, then 10 s settle -
                     confirms whether rows exist at all (full run skipped
                     both) and collects console/page errors.

Run:  python scripts/probe_mod_n.py
Out:  artifacts/probe_mod_n.txt
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

OUTFILE = Path(settings.ARTIFACTS_DIR) / "probe_mod_n.txt"
LINES: list[str] = []

METRIC_JS = """() => {
  const info = [...document.querySelectorAll('[id$=_info]')]
    .map(e => e.innerText.trim()).join(' | ');
  const t = document.querySelector('table.rfid-export-table');
  const rows = t
    ? t.querySelectorAll('tbody tr:not(.rfid-gen-empty-row)').length : -1;
  const box = document.querySelector(
    "input[type=search][placeholder*='Quick search']");
  return {info, rows, value: box ? box.value : null};
}"""


def log(msg: str) -> None:
    LINES.append(msg)
    OUTFILE.write_text("\n".join(LINES), encoding="utf-8")
    print(msg)


def metric(page) -> dict:
    return page.evaluate(METRIC_JS)


def poll_until_change(page, before: dict, timeout_s: float,
                      label: str) -> float | None:
    """Poll metric every 250 ms; return seconds until it differs from before."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        page.wait_for_timeout(250)
        now = metric(page)
        if now["info"] != before["info"] or now["rows"] != before["rows"]:
            elapsed = timeout_s - (deadline - time.monotonic())
            log(f"      {label}: changed after ~{elapsed:.1f}s "
                f"-> info={now['info']!r} rows={now['rows']}")
            return elapsed
    now = metric(page)
    log(f"      {label}: NO change within {timeout_s}s "
        f"(info={now['info']!r} rows={now['rows']} value={now['value']!r})")
    return None


def search(page, text: str, wait_s: float, label: str) -> None:
    box = page.locator(
        "input[type=search][placeholder*='Quick search']").first
    before = metric(page)
    box.click()
    box.fill(text)
    box.press("Enter")
    poll_until_change(page, before, wait_s, label)


def clear_search(page, wait_s: float, label: str) -> None:
    box = page.locator(
        "input[type=search][placeholder*='Quick search']").first
    before = metric(page)
    box.click()
    box.fill("")
    box.press("Enter")
    poll_until_change(page, before, wait_s, label)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.HEADLESS)
        page = browser.new_context(viewport=settings.VIEWPORT,
                                   locale=settings.LOCALE).new_page()
        page.set_default_timeout(settings.TIMEOUT_MS)
        page.on("console", lambda m: log(f"      console[{m.type}]: "
                                         f"{m.text[:140]}")
                if m.type == "error" else None)
        page.on("pageerror", lambda e: log(f"      pageerror: {str(e)[:140]}"))

        page.goto(settings.BASE_URL + "/en/login",
                  wait_until="domcontentloaded")
        page.locator("#rfid-login-username").fill(settings.LOGIN_EMAIL)
        page.locator("#rfid-login-password").fill(settings.LOGIN_PASSWORD)
        page.locator("button[type=submit]").click()
        page.wait_for_timeout(3500)

        # ------------------------------------------------------------------ #
        log("=== recent_generated (fast dataset) ===")
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["recent_generated"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        log(f"  baseline: {metric(page)}")
        search(page, "zzz-no-such-record-zzz", 10, "filter to zero")
        clear_search(page, 10, "clear/restore")

        # ------------------------------------------------------------------ #
        log("=== rewrite_rfids: grab a real BEFORE epc ===")
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["rewrite_rfids"],
                  wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        before_epc = page.evaluate("""() => {
          const t = document.querySelector('table.rfid-export-table')
                || document.querySelector('table');
          for (const tr of t.querySelectorAll('tbody tr')) {
            const txt = tr.innerText || '';
            const m = txt.match(/BEFORE\\s+([0-9A-Fa-f]{24})/);
            if (m) return m[1];
          }
          return null;
        }""")
        log(f"  before_epc={before_epc}")

        # ------------------------------------------------------------------ #
        log("=== rfid_list (1,150,551 rows, client-side) ===")
        page.goto(settings.BASE_URL + settings.MODULE_PATHS["rfid_list"],
                  wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        log(f"  baseline: {metric(page)}")

        real = page.evaluate("""() => {
          const t = document.querySelector('table.rfid-export-table');
          if (!t) return null;
          const hs = [...t.querySelectorAll('thead th')]
            .map(h => (h.innerText || '').trim().toLowerCase());
          const i = hs.findIndex(h => h.includes('rfid')
                                  && !h.includes('mother'));
          const td = t.querySelector(
            'tbody tr:not(.rfid-gen-empty-row) td');
          const cells = td
            ? td.parentElement.querySelectorAll('td') : [];
          const cell = cells[i < 0 ? cells.length - 1 : i];
          return cell ? (cell.innerText || '').trim().slice(0, 10) : null;
        }""")
        log(f"  real-term sample (first-page RFID prefix): {real!r}")

        if real:
            search(page, real, 45, "filter real term")
            clear_search(page, 30, "clear real term")

        if before_epc:
            search(page, before_epc, 45, "filter OLD epc")
            if metric(page)["rows"] not in (0, -1):
                log(f"      rows now: {metric(page)}")
            clear_search(page, 30, "clear old epc")

        search(page, "zzz-no-such-record-zzz", 45, "filter impossible")
        clear_search(page, 30, "clear impossible")

        # ------------------------------------------------------------------ #
        for key in ("style_number_list", "transaction_list"):
            log(f"=== {key} (goto timeout 60s, settle 10s) ===")
            try:
                page.goto(settings.BASE_URL + settings.MODULE_PATHS[key],
                          wait_until="domcontentloaded", timeout=60000)
            except Exception as exc:
                log(f"  goto failed: {type(exc).__name__}: "
                    f"{str(exc)[:120]}")
            page.wait_for_timeout(10000)
            log(f"  state: {metric(page)}")
            inv = page.evaluate("""() => [...document.querySelectorAll('table')]
              .map(t => ({id: t.id || '<no-id>',
                          vis: !!(t.offsetWidth || t.offsetHeight),
                          rows: t.querySelectorAll(
                            'tbody tr:not(.rfid-gen-empty-row)').length}))""")
            log(f"  tables: {inv}")

        browser.close()
    log("DONE")


if __name__ == "__main__":
    main()
