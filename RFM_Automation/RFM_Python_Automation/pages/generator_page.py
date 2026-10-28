"""GeneratorPage - the RFID Master Generator (main module, `?act=view`).

DOM verified 2026-10-09 against https://dev.master.bwrfm.com/en/rfid_generator/?act=view

Layout
------
  Encoding Inputs (left)      Generated Series (right)
    Item Code / Others tabs     table.rfid-gen-table (ITEM CODE, STYLE NUMBER,
    textarea#rfid-gtin            STYLE NAME, COLOR, SIZE, SET, RFID, SERIAL, COPY)
    #rfid-serial-start           per-column search inputs #rfid-search-*
    #rfid-quantity               rows selector #rfid-page-size
    Generate Series / Clear      TOTAL GENERATED / STYLES / MOTHER / CHILD
    #rfid-save-generated (Save)  Item Code Status panel (#rfid-current-series-search)

Flow (verified)
---------------
  Generate Series -> modal #rfid-save-confirm-modal ("Generation Summary")
                  -> #rfid-confirm-save (Continue)
  Save            -> modal #rfid-save-confirm-modal ("Save Summary")
                  -> #rfid-confirm-save (Save)
                  -> modal #rfid-post-save-export-modal ("Saved Successfully")
                  -> #rfid-close-post-save-export ("Close & Clear Series")
  NOTE: after saving, the app shows #rfid-screen-overlay; until the post-save
  modal is dismissed every other click is intercepted.

Covers TC-GEN-*, TC-ICS-*, TC-TBL-*, TC-SUM-*, TC-SAVE-*.
"""

from __future__ import annotations

import re

from config import settings
from pages.base_page import BasePage
from playwright.sync_api import Locator


class GeneratorPage(BasePage):
    path = settings.GENERATOR_PATH
    sidebar_label = settings.NAV["generator"]
    heading = "Encoding Inputs"

    # --- encoding inputs (verified ids) ---------------------------------- #
    TAB_ITEM_CODE = "Item Code"
    TAB_OTHERS = "Others"
    TAB_CSS = ".rfid-gen-mode-btn"
    ITEM_TEXTAREA = "#rfid-gtin"
    STARTING_SERIAL = "#rfid-serial-start"
    QUANTITY = "#rfid-quantity"
    BTN_GENERATE = "Generate Series"
    BTN_CLEAR = "#rfid-clear"
    BTN_SAVE = "#rfid-save-generated"
    BTN_SHOW_SEARCH = "#rfid-toggle-search"

    # --- Others tab ------------------------------------------------------- #
    LABEL_PREFIX_LENGTH = "GS1 Company Prefix Length"
    LABEL_FILTER = "Filter"
    LABEL_SERIAL_STEP = "Serial Step"
    SELECT_GCP_LENGTH = "#rfid-gcp-length"
    SELECT_FILTER = "#rfid-filter"
    INPUT_SERIAL_STEP = "#rfid-serial-step"

    # --- generated series ------------------------------------------------- #
    TABLE = "table.rfid-gen-table"
    ROW_SIZES = ["10", "25", "50", "100"]
    SELECT_PAGE_SIZE = "#rfid-page-size"
    SEARCH_STYLE = "#rfid-search-style"
    SEARCH_INPUTS = ("#rfid-search-style", "#rfid-search-mother", "#rfid-search-item-code",
                     "#rfid-search-color", "#rfid-search-size", "#rfid-search-item",
                     "#rfid-search-serial", "#rfid-search-hex")
    # counters are spans whose parent prints "TOTAL GENERATED\n2"
    COUNTER_LABELS = ("Total Generated", "Total Styles", "Total Mother", "Total Child")

    # --- generation summary / save summary modal -------------------------- #
    MODAL = "#rfid-save-confirm-modal"
    SUMMARY_TITLE = "Generation Summary"
    SAVE_SUMMARY_TITLE = "Save Summary"
    BTN_CONTINUE = "#rfid-confirm-save"      # Continue (summary) and Save (save summary)
    BTN_CANCEL = "#rfid-save-confirm-modal button:has-text('Cancel')"

    # --- post-save export modal ------------------------------------------- #
    POST_SAVE_MODAL = "#rfid-post-save-export-modal"
    BTN_CLOSE_AND_CLEAR = "#rfid-close-post-save-export"        # "Close & Clear Series"
    BTN_EXPORT_SAVED = "#rfid-export-saved-excel"               # "Export"

    # --- item code status panel (verified 2026-10-09) --------------------- #
    # div#rfid-current-series-code-list holds one span.rfid-current-series-code
    # per item code: <code>5057877230509</code> + Qty input + status badge +
    # remove button.  The list refreshes only when the textarea BLURS.
    SEARCH_ITEM_CODE = "#rfid-current-series-search"     # aria: Search item code status
    CODE_LIST = "#rfid-current-series-code-list"
    CODE_ENTRY = "#rfid-current-series-code-list .rfid-current-series-code"
    CODE_STATUS = ".rfid-current-series-code-status"     # is-new | is-existing | is-duplicate
    CODE_QTY = ".rfid-current-series-code-quantity-input"   # min=1 max=5000 step=1
    CODE_REMOVE = ".rfid-current-series-code-remove"     # aria: Remove <code> ...
    # Update control (re-verified 2026-10-15): while any code has a pending
    # Qty change the MAIN #rfid-generate-series button morphs - class
    # `is-update-series`, label "Update Series".  The pre-2026-10 builds used
    # a separate #rfid-current-series-refresh button; both are supported.
    BTN_UPDATE_SERIES = "#rfid-generate-series.is-update-series"
    BTN_UPDATE_SERIES_LEGACY = "#rfid-current-series-refresh"

    # ================================================================== #
    # Encoding inputs
    # ================================================================== #
    def select_tab(self, name: str) -> "GeneratorPage":
        tabs = self.page.locator(self.TAB_CSS, has_text=name)
        (tabs.first if tabs.count() else self.page.get_by_role("button", name=name)).click()
        self.page.wait_for_timeout(250)
        return self

    def enter_item_codes(self, codes: list[str] | str) -> "GeneratorPage":
        if isinstance(codes, str):
            codes = [codes]
        box = self.find(
            self.page.locator(self.ITEM_TEXTAREA),
            self.page.get_by_label("Item Code", exact=False),
        )
        box.fill("\n".join(c.strip() for c in codes if c.strip()))
        # the Item Code Status list only refreshes when the textarea blurs
        box.press("Tab")
        try:
            self.page.locator(self.CODE_ENTRY).first.wait_for(state="visible", timeout=3000)
        except Exception:                       # pragma: no cover - panel is optional
            pass
        return self

    def set_starting_serial(self, value) -> "GeneratorPage":
        self.page.locator(self.STARTING_SERIAL).fill(str(value))
        return self

    def set_quantity(self, value) -> "GeneratorPage":
        self.page.locator(self.QUANTITY).fill(str(value))
        return self

    def set_serial_step(self, value) -> "GeneratorPage":
        self.page.locator(self.INPUT_SERIAL_STEP).fill(str(value))
        return self

    def generate_series(self, wait_for_summary: bool = False) -> "GeneratorPage":
        """Click Generate Series.

        A valid request opens the Generation Summary modal in ~1-2 s; an invalid
        one (empty list, bad qty, bad serial ...) shows an inline error and no
        modal at all.  We therefore never raise when it does not appear - negative
        tests rely on that - and `summary_visible()` does its own short wait.
        """
        self.click_button(self.BTN_GENERATE)
        if wait_for_summary:
            try:
                self.page.locator(self.MODAL).first.wait_for(state="visible", timeout=8000)
            except Exception:                       # pragma: no cover - negative path
                pass
        else:
            self.page.wait_for_timeout(600)
        return self

    # ================================================================== #
    # Generation Summary modal
    # ================================================================== #
    def summary(self) -> Locator:
        return self.page.locator(self.MODAL).first

    def summary_visible(self, timeout: int = 3000) -> bool:
        """True when the Generation Summary modal is on screen.

        Gives the app a moment to open it, so positive tests are not racing the
        1-2 s modal animation, while negative tests still resolve quickly.
        """
        modal = self.page.locator(self.MODAL).first
        try:
            modal.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return modal.is_visible()

    def summary_text(self) -> str:
        modal = self.page.locator(self.MODAL).first
        return modal.inner_text() if modal.count() else ""

    def continue_summary(self) -> "GeneratorPage":
        """Accept the Generation Summary (button id #rfid-confirm-save)."""
        self.page.locator(f"{self.BTN_CONTINUE}:visible").first.click()
        self.page.locator(self.MODAL).first.wait_for(state="hidden", timeout=10000)
        return self

    def cancel_summary(self) -> "GeneratorPage":
        self.page.locator(self.BTN_CANCEL).first.click()
        self.page.locator(self.MODAL).first.wait_for(state="hidden", timeout=5000)
        return self

    def set_mother(self, value: str) -> "GeneratorPage":
        # the mother-mode select has no label; find it by its documented options
        select = self.page.locator(
            "select:has(option[value]), select", has_text="Use existing")
        (select.first if select.count()
         else self.page.get_by_label("Mother", exact=False).first).select_option(label=value)
        return self

    def full_generate(self, codes, serial=0, quantity=16) -> "GeneratorPage":
        """Item code tab -> inputs -> Generate Series -> Continue."""
        return (self.select_tab(self.TAB_ITEM_CODE)
                .enter_item_codes(codes)
                .set_starting_serial(serial)
                .set_quantity(quantity)
                .generate_series()
                .continue_summary())

    # ================================================================== #
    # Generated Series table
    # ================================================================== #
    def rows(self) -> Locator:
        return self.page.locator(f"{self.TABLE} tbody tr:not(.rfid-gen-empty-row)")

    def row_count(self) -> int:
        return self.rows().count()

    def counters(self) -> dict:
        """Read the TOTAL GENERATED / STYLES / MOTHER / CHILD tiles."""
        out = {}
        for label in self.COUNTER_LABELS:
            out[label] = self._read_counter(label)
        return out

    def _read_counter(self, label: str) -> int:
        span = self.page.get_by_text(label, exact=False).first
        if not span.count():
            return -1
        raw = span.locator("xpath=ancestor::*[1]").inner_text()
        m = re.search(r"(\d[\d,]*)\s*$", raw.replace(label, "").strip())
        return int(m.group(1).replace(",", "")) if m else -1

    def set_page_size(self, size: int) -> "GeneratorPage":
        self.page.locator(self.SELECT_PAGE_SIZE).select_option(str(size))
        self.page.wait_for_timeout(400)
        return self

    def show_search(self) -> "GeneratorPage":
        btn = self.page.locator(self.BTN_SHOW_SEARCH)
        if btn.count() and not self.page.locator(self.SEARCH_STYLE).first.is_visible():
            btn.click()
            self.page.wait_for_timeout(300)
        return self

    def search_rows(self, value: str) -> "GeneratorPage":
        self.show_search()
        self.page.locator(self.SEARCH_STYLE).first.fill(value)
        self.page.wait_for_timeout(500)
        return self

    def clear_search(self) -> "GeneratorPage":
        for selector in self.SEARCH_INPUTS:
            box = self.page.locator(selector)
            if box.count():
                box.first.fill("")
        self.page.wait_for_timeout(500)
        return self

    def column_values(self, header: str) -> list[str]:
        """Raw text of one column for every visible series row."""
        idx = self.header_index(header)
        return [r.locator("td").nth(idx).inner_text().strip() for r in self.rows().all()]

    def rfid_values(self) -> list[str]:
        """EPC strings of the RFID column.

        The cell is `<code>EPC</code><small>NO MOTHER</small>` - inner_text()
        would return "EPC\nNO MOTHER", so only the <code> element is read.
        """
        idx = self.header_index("RFID")
        out = []
        for r in self.rows().all():
            cell = r.locator("td").nth(idx)
            code = cell.locator("code")
            raw = (code.first.text_content() if code.count() else cell.inner_text()) or ""
            out.append(raw.strip())
        return out

    def serial_values(self) -> list[str]:
        idx = self.header_index("Serial")
        return [r.locator("td").nth(idx).inner_text().strip() for r in self.rows().all()]

    def rows_for_item_code(self, code: str) -> int:
        """Number of pending series rows belonging to one item code."""
        return sum(1 for v in self.column_values("Item Code") if v == code)

    def header_index(self, header: str) -> int:
        headers = self.page.locator(f"{self.TABLE} thead th")
        for i in range(headers.count()):
            if header.lower() in headers.nth(i).inner_text().lower():
                return i
        raise AssertionError(f"Column '{header}' not found in the Generated Series table")

    def copy_rfid(self, row: int = 0) -> "GeneratorPage":
        # verified: icon-only button, title="Copy RFID", class rfid-row-copy
        self.rows().nth(row).locator("button.rfid-row-copy").first.click()
        return self

    def row_link_states(self) -> list[str]:
        """The <small class="rfid-row-link-state"> badge under each RFID
        ("No Mother" for childless rows - verified in the DOM)."""
        badges = self.page.locator(f"{self.TABLE} tbody tr small.rfid-row-link-state")
        return [badges.nth(i).inner_text().strip() for i in range(badges.count())]

    # ================================================================== #
    # Item Code Status panel
    # ================================================================== #
    def item_code_statuses(self, visible_only: bool = False) -> list[dict]:
        """One dict per entry of #rfid-current-series-code-list.

        {'code': '5057877230509', 'status': 'New'|'Added'|'Duplicate (ignored)',
         'qty': '16', 'added_at': 'Added to current series: 10/9/2026 ...',
         'removed': False}
        The status text is read from textContent (not innerText) because CSS
        uppercases the Added / Duplicate badges when rendered.

        `visible_only=True` skips entries hidden by the Search item code
        filter (also covers a server-side filter that removes them).
        """
        entries = self.page.locator(self.CODE_ENTRY)
        out = []
        for i in range(entries.count()):
            entry = entries.nth(i)
            if visible_only and not entry.is_visible():
                continue
            code_el = entry.locator("code")
            status_el = entry.locator(self.CODE_STATUS)
            qty_el = entry.locator(self.CODE_QTY)
            if not code_el.count():
                continue
            out.append({
                "code": (code_el.text_content() or "").strip(),
                "status": (status_el.text_content() or "").strip() if status_el.count() else "",
                "qty": qty_el.input_value() if qty_el.count() else "",
                "added_at": entry.get_attribute("title") or "",
                # removed codes STAY in the list with class "is-removed" (app design)
                "removed": "is-removed" in (entry.get_attribute("class") or ""),
            })
        return out

    def textarea_codes(self) -> list[str]:
        """Item-code lines currently in #rfid-gtin, 'code: qty' collapsed to code.

        The app writes a per-code quantity override back into the textarea as
        `5057877230509: 6` (verified 2026-10-09); this helper returns only the
        codes so tests can assert which ones the series still tracks.
        """
        raw = self.page.locator(self.ITEM_TEXTAREA).input_value()
        codes = []
        for line in raw.splitlines():
            line = line.strip()
            if line:
                codes.append(line.split(":", 1)[0].strip())
        return codes

    def search_item_code(self, code: str) -> "GeneratorPage":
        self.page.locator(self.SEARCH_ITEM_CODE).first.fill(code)
        self.page.wait_for_timeout(500)
        return self

    def set_item_code_qty(self, code: str, qty) -> "GeneratorPage":
        """Fill the per-code Qty input of one status entry (min=1 max=5000).

        The app only commits the change on BLUR (Tab) - it then rewrites the
        textarea as `code: qty`, shows "Quantity changed" and reveals the
        Update series button (verified 2026-10-09).
        """
        entry = self.page.locator(self.CODE_ENTRY, has_text=code).first
        field = entry.locator(self.CODE_QTY).first
        field.fill(str(qty))
        field.press("Tab")                      # blur commits the change
        self.page.wait_for_timeout(600)         # lets the dirty notice appear
        return self

    def update_series(self) -> "GeneratorPage":
        """Apply a pending per-code Qty change (TC-ICS-003 / TC-TBL-008).

        Current build: while any code has a pending Qty change the main
        Generate Series button morphs into "Update Series"
        (#rfid-generate-series.is-update-series); clicking it opens the
        Generation Summary PREVIEW and #rfid-confirm-save (Continue) applies
        it (verified 2026-10-15).
        Older builds used a dedicated #rfid-current-series-refresh button.
        Returns unchanged when no update control is offered.
        """
        btn = self.page.locator(self.BTN_UPDATE_SERIES)
        if not (btn.count() and btn.first.is_visible()):
            btn = self.page.locator(self.BTN_UPDATE_SERIES_LEGACY)
            if not (btn.count() and btn.first.is_visible()):
                return self
        btn.first.click()
        modal = self.page.locator(self.MODAL).first
        try:
            modal.wait_for(state="visible", timeout=8000)
        except Exception:                       # applies without a preview
            self.page.wait_for_timeout(1000)
            return self
        self.page.locator(f"{self.BTN_CONTINUE}:visible").first.click()
        modal.wait_for(state="hidden", timeout=10000)
        self.page.wait_for_timeout(400)         # rows re-render after apply
        return self

    def remove_item_code(self, code: str) -> "GeneratorPage":
        """Remove one code from the current series (its 'x' button)."""
        entry = self.page.locator(self.CODE_ENTRY, has_text=code)
        target = entry.first.locator(self.CODE_REMOVE) if entry.count() else None
        if target is None or not target.count():
            target = self.page.locator(
                f"button.rfid-current-series-code-remove[aria-label*='{code}']")
        target.first.click()
        self.page.wait_for_timeout(600)
        return self

    # ================================================================== #
    # Save / Clear
    # ================================================================== #
    def save(self) -> str:
        """Save -> Save Summary modal -> Save -> post-save modal -> close it.

        Returns the post-save modal text ("Saved Successfully / N saved rows ...").
        """
        self.click_button(self.BTN_SAVE)
        self.page.locator(self.MODAL).first.wait_for(state="visible", timeout=10000)
        self.page.locator(f"{self.BTN_CONTINUE}:visible").first.click()

        post = self.page.locator(self.POST_SAVE_MODAL)
        post.first.wait_for(state="visible", timeout=15000)
        message = post.first.inner_text()

        close = self.page.locator(self.BTN_CLOSE_AND_CLEAR)
        if close.count():
            close.first.click()
            post.first.wait_for(state="hidden", timeout=5000)
        return message

    def clear_all(self) -> "GeneratorPage":
        self.click_button(self.BTN_CLEAR)
        self.page.wait_for_timeout(400)
        return self
