"""ListPage - shared behaviour for every *List* style module.

DOM verified 2026-10-09 against the live app. All export-style lists
(Recent Generated, RFID List, Style Number List, Mother List, Deleted List,
Rewrite RFIDs) reuse the same filter form built from `#rfid-export-*` inputs:

    KEYWORD          #rfid-export-keyword        JO NUMBER   #rfid-export-jo
    STYLE NUMBER     #rfid-export-style          COLOR       #rfid-export-color
    ITEM CODE / GTIN #rfid-export-gtin           SIZE        #rfid-export-size
    SERIAL           #rfid-export-serial         MOTHER RFID #rfid-export-mother-tag
    DATE FROM/TO     #rfid-export-date-from/to   USER        #rfid-export-created-by
    MOTHER STATUS    #rfid-export-mother-status  PRINTED     #rfid-export-printed
    WMS SYNC         #rfid-export-wms-sync       WEBSERVICE SYNC #rfid-export-webservice-sync

Buttons: Filter (submit), #rfid-export-clear (Clear),
#rfid-export-filtered-download (Export Filtered), #rfid-export-download (Export All)
Quick search: input[type=search][placeholder^="Quick search"]
Entries selector: select[name="rfid-export-table_length"] (20/50/100/250/500)

Modules that do NOT use this form (Transaction List, All Users, Operator List,
Generation History) override FILTER_IDS with their own prefix.
"""

from __future__ import annotations

import time
from typing import Sequence

from config import settings
from pages.base_page import BasePage
from playwright.sync_api import Locator, expect


class ListPage(BasePage):
    # form controls (verified ids)
    BTN_FILTER = "Filter"
    BTN_CLEAR = "#rfid-export-clear"
    BTN_EXPORT_FILTERED = "#rfid-export-filtered-download"
    BTN_EXPORT_ALL = "#rfid-export-download"
    TABLE_SEARCH = "input[type=search][placeholder*='Quick search']"
    ENTRIES_SELECTOR = "select[name$='_length']"

    # label -> css id of the filter control (export-style lists)
    FILTER_IDS = {
        "keyword": "#rfid-export-keyword",
        "style number": "#rfid-export-style",
        "jo number": "#rfid-export-jo",
        "item code / gtin": "#rfid-export-gtin",
        "gtin": "#rfid-export-gtin",
        "color": "#rfid-export-color",
        "size": "#rfid-export-size",
        "serial": "#rfid-export-serial",
        "mother rfid": "#rfid-export-mother-tag",
        "date from": "#rfid-export-date-from",
        "date to": "#rfid-export-date-to",
        "user": "#rfid-export-created-by",
        "mother status": "#rfid-export-mother-status",
        "printed": "#rfid-export-printed",
        "wms sync": "#rfid-export-wms-sync",
        "webservice sync": "#rfid-export-webservice-sync",
    }

    # documented filter labels (used for documentation / validation)
    FILTER_LABELS = tuple(FILTER_IDS)

    # ------------------------------------------------------------------ #
    # Loading state
    # ------------------------------------------------------------------ #
    def wait_for_table(self, timeout: int = 10000) -> "ListPage":
        """Wait until the DataTable finished its async fetch.

        The app renders <tr class="rfid-gen-empty-row"> with a
        "Loading RFID records..." / "Loading RFID transaction records..."
        placeholder while the data is being retrieved; once it disappears the
        table either has rows or is genuinely empty.
        """
        try:
            self.page.wait_for_function(
                """() => {
                    const loading = document.querySelector(
                        'table tbody tr.rfid-gen-empty-row');
                    if (loading && /loading/i.test(loading.innerText)) return false;
                    return !!document.querySelector('table tbody');
                }""",
                timeout=timeout,
            )
        except Exception:                       # pragma: no cover - keep best effort
            pass
        return self

    def open(self) -> "ListPage":
        super().open()
        self.wait_for_table()
        return self

    # ------------------------------------------------------------------ #
    # Filters
    # ------------------------------------------------------------------ #
    def apply_filters(self, **values: str) -> "ListPage":
        """Fill any subset of the documented filter fields, then press Filter."""
        for label, value in values.items():
            nice = label.replace("_", " ").strip().lower()
            css = self.FILTER_IDS.get(nice)
            if css and self.page.locator(css).count():
                field = self.page.locator(css).first
                # <select> has no type attribute; detect by tagName instead
                if field.evaluate("e => e.tagName.toUpperCase()") == "SELECT":
                    self.select_option(css, value)   # label first, then value
                else:
                    field.fill(str(value))
                    field.press("Enter")
            else:
                try:
                    self.fill_field(nice, value)
                except AssertionError:
                    raise AssertionError(
                        f"Filter field '{nice}' not found on {self.__class__.__name__}")
        self.click_button(self.BTN_FILTER)
        try:
            self.page.wait_for_load_state("networkidle")
        except Exception:                       # pragma: no cover - long polling
            pass
        self.page.wait_for_timeout(600)
        return self

    def clear_filters(self) -> "ListPage":
        try:
            self.resolve(self.BTN_CLEAR).click(timeout=4000)
        except Exception:                       # name fallback (e.g. "Clear")
            self.page.get_by_role("button", name="Clear", exact=False).first.click()
        self.page.wait_for_timeout(400)
        return self

    def table_search(self, text: str) -> "ListPage":
        box = self.find(
            self.page.locator(self.TABLE_SEARCH),
            self.page.locator("table input[type=search]"),
            self.page.locator("div[id$='_filter'] input[type=search]"),
            self.page.get_by_role("searchbox"),
        )
        before_value = box.input_value()
        before_info = self._info_text()
        before_rows = self.row_count()
        box.click()
        box.fill(text)
        # DataTables listens for keyup; fill() alone does not re-filter.
        box.press("Enter")
        if before_value == text:
            # Nothing actually changed in the input - no redraw to wait for.
            self.page.wait_for_timeout(400)
            return self
        # Filtering is asynchronous (measured 2026-10-19, probe_mod_n):
        # Recent Generated ~1.6 s, RFID List ~4.0 s over 1,150,551 rows.
        # A fixed 500 ms sleep read the UNFILTERED table and caused the
        # TC-TBL-005 failure - poll the DataTables info line / row count
        # instead, up to 15 s.
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            self.page.wait_for_timeout(250)
            if (self._info_text() != before_info
                    or self.row_count() != before_rows):
                break
        return self

    def _info_text(self) -> str:
        """DataTables info line, e.g. \"Showing 1 to 20 of 189 entries ...\"."""
        info = self.page.locator("[id$=_info]")
        if not info.count():
            return ""
        return " | ".join(info.nth(i).inner_text().strip()
                          for i in range(info.count()))

    # ------------------------------------------------------------------ #
    # Table
    # ------------------------------------------------------------------ #
    @property
    def _main_table(self) -> Locator:
        """The primary data table (never a modal's batch-entry table)."""
        named = self.page.locator(
            "table.rfid-export-table, table#rfid-user-table, "
            "table#rfid-operator-table, table#rfid-mismatch-table")
        if named.count():
            return named.first
        # Fallback: first table not embedded in a modal (Transaction,
        # Generation History, Deleted use plain <table>).
        return self.page.locator("table:not(.modal table)").first

    @property
    def table(self) -> Locator:
        return self._main_table

    def rows(self) -> Locator:
        # Exclude every placeholder row shape:
        #  - the generator's own .rfid-gen-empty-row (loading state)
        #  - DataTables' empty-state row: classed td.dataTables_empty.
        #    Its text is customised per page ("No matching records found"
        #    vs something else), so match the CLASS, not the text - after
        #    an impossible search the text filter alone still counted 1 row
        #    (TC-TBL-005, 2026-10-19).
        return self.page.locator(
            "table:not(.operator-entry-table):not(.modal table) "
            "tbody tr:not(.rfid-gen-empty-row)"
            ":not(:has(td.dataTables_empty))")

    def row_count(self) -> int:
        return self.rows().count()

    def wait_for_rows(self, minimum: int = 1,
                      timeout_ms: int = 12000) -> bool:
        """Poll until at least `minimum` data rows have rendered.

        Export pages (?act=...) sometimes take >15 s to finish loading
        (Style Number List DCL exceeded 15 s on 2026-10-19, which made
        row-count guards skip although data existed).  Returns True as
        soon as rows appear, False when still empty after the timeout.
        """
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            if self.row_count() >= minimum:
                return True
            self.page.wait_for_timeout(300)
        return self.row_count() >= minimum

    def cell(self, row: int, column: int) -> str:
        return rows_text(self.rows().nth(row), column)

    def column_values(self, header: str) -> Sequence[str]:
        """All values of one column, located by its header text."""
        idx = self.header_index(header)
        return [rows_text(r, idx) for r in self.rows().all()]

    def header_index(self, header: str) -> int:
        # Scope to thead OUTSIDE any modal so a batch-entry table's "CHECK"
        # or "REMOVE" header can never be matched as a data column.
        # Two passes: exact match first, because a substring match would read
        # "MOTHER RFID" for a request of "RFID" (that returned the '-' mother
        # column instead of real EPCs in TC-RW-003, 2026-10-19).
        headers = self.page.locator(
            "table:not(.modal table):not(.operator-entry-table) thead th")
        texts = [headers.nth(i).inner_text().strip().lower()
                 for i in range(headers.count())]
        want = header.strip().lower()
        if want in texts:
            return texts.index(want)
        for i, text in enumerate(texts):
            if want in text:
                return i
        raise AssertionError(f"Column '{header}' not found on {self.__class__.__name__}")

    def click_row_action(self, row: int = 0, action: str = "View") -> None:
        target = self.rows().nth(row).get_by_role("button", name=action, exact=False)
        if not target.count():
            target = self.rows().nth(row).locator(f"button:has-text('{action}')")
        if not target.count():
            target = self.rows().nth(row).get_by_text(action, exact=True)
        target.first.click()
        self.page.wait_for_timeout(500)

    def sort_by(self, header: str) -> None:
        self.page.locator("table:visible thead th", has_text=header).first.click()
        self.page.wait_for_timeout(300)

    def set_page_size(self, size: int) -> None:
        select = self.page.locator(self.ENTRIES_SELECTOR).first
        select.select_option(str(size))
        self.page.wait_for_timeout(400)

    # ------------------------------------------------------------------ #
    # Modals (transaction history, style details, mother details ...)
    # ------------------------------------------------------------------ #
    def modal(self) -> Locator:
        """The one visible app modal.

        Every app dialog is a `.modal` that also carries `.in`/`.show` while
        open. The third-party Respipe support widget masquerades as
        `[role=dialog]` (text "IT Support ... Powered by Respipe") but has no
        `.modal` class, so restricting to `.modal` excludes it. All app modals
        stay in the DOM hidden; only the open one is visible, so taking the
        last visible `.modal.in`/`.show` is the live modal.
        """
        return self.page.locator(".modal.show:visible, .modal.in:visible").last

    def _clear_any_modal(self) -> None:
        """Escape out of a modal left open by a previous step.

        The app keeps modals mounted in the DOM, so a stray open dialog
        intercepts the next toolbar/row click (observed 2026-10-15: clicking
        "Add Operators" while a modal was open timed out on pointer events).
        Escape alone is not enough for every dialog (the Access Settings modal
        ignored it), so we fall back to its Close button, then to force-
        unmounting the .in/.show state, and always scrub the backdrop.
        """
        if self.page.locator(".modal:visible").count():
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(400)
        if self.page.locator(".modal:visible").count():
            modal = self.page.locator(".modal:visible").last
            for sel in ("button.close", "[data-dismiss=modal]",
                        "button:has-text('Close')"):
                btn = modal.locator(sel)
                if btn.count():
                    try:
                        btn.first.click(timeout=2500)
                        break
                    except Exception:               # pragma: no cover - defensive
                        pass
            self.page.wait_for_timeout(400)
        if self.page.locator(".modal:visible").count():
            self.page.evaluate(
                """() => document.querySelectorAll('.modal.in, .modal.show')
                    .forEach(m => { m.classList.remove('in', 'show');
                                    m.style.setProperty('display', 'none'); })""")
        self.page.evaluate(
            """() => {
                document.querySelectorAll('.modal-backdrop')
                  .forEach(b => b.remove());
                document.body.classList.remove('modal-open');
            }""")

    def close_modal(self) -> None:
        """Close the visible modal, clearing any leftover backdrop.

        Clicks the first visible Close/Cancel/Dismiss control, then falls back
        to Escape. If the app leaves the modal element open (it keeps the
        modal in the DOM even when "closed"), we still scrub the
        `.modal-backdrop` and the body lock so subsequent clicks are not
        intercepted (observed 2026-10-15 on the All Users create flow).
        """
        modal = self.modal()
        if not modal.count():
            return
        for sel in ("button.close:visible", "[data-dismiss=modal]:visible",
                    "button:has-text('Close'):visible",
                    "button:has-text('Cancel'):visible"):
            btn = modal.locator(sel)
            if btn.count():
                btn.first.click()
                break
        else:
            self.page.keyboard.press("Escape")
        try:
            expect(modal).to_be_hidden(timeout=2500)
        except Exception:                           # app keeps it mounted
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(300)
        # Belt-and-braces: never leave an overlay that blocks the next click.
        self.page.evaluate(
            """() => {
                document.querySelectorAll('.modal-backdrop')
                  .forEach(b => b.remove());
                document.body.classList.remove('modal-open');
                document.body.style.removeProperty('overflow');
            }""")

    # ------------------------------------------------------------------ #
    # Export / more actions
    # ------------------------------------------------------------------ #
    def export_filtered(self):
        with self.page.expect_download() as dl:
            self.page.locator(self.BTN_EXPORT_FILTERED).first.click()
        return dl.value

    def export_all(self):
        with self.page.expect_download() as dl:
            self.page.locator(self.BTN_EXPORT_ALL).first.click()
        return dl.value


def rows_text(row: Locator, index: int) -> str:
    cells = row.locator("td")
    if index >= cells.count():
        return ""
    return cells.nth(index).inner_text().strip()
