"""StyleNumberListPage - "Style Number List" (styles grouped + details modal).

Covers TC-SL-001 .. TC-SL-005.
"""

from __future__ import annotations

import time

from config import settings
from pages.list_page import ListPage


class StyleNumberListPage(ListPage):
    path = settings.MODULE_PATHS["style_number_list"]
    sidebar_label = settings.NAV["style_number_list"]
    heading = "Style Number List"

    FILTER_WEBSERVICE_SYNC = "WebService Sync"
    FILTER_MOTHER_STATUS = "Mother Status"
    BTN_EXPORT = "Export"          # verified: this list exposes a single Export button

    WEBSERVICE_SYNCED = "WebService Synced"
    WEBSERVICE_NOT_SYNCED = "WebService Not Synced"

    # ------------------------------------------------------------------ #
    # DOM verified 2026-10-15: #rfid-style-sync-summary holds two chips,
    # span.rfid-style-sync-chip.is-synced "Synced 1887" and
    # span.rfid-style-sync-chip.is-not-synced "Not Synced 1".
    SYNC_SUMMARY = "#rfid-style-sync-summary"
    CHIP_SYNCED = ".rfid-style-sync-chip.is-synced"
    CHIP_NOT_SYNCED = ".rfid-style-sync-chip.is-not-synced"

    @staticmethod
    def _digits(text: str) -> int:
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else -1

    def sync_counters(self) -> dict:
        """{'synced': int, 'not_synced': int} from the counter chips."""
        out = {}
        for key, sel in (("synced", self.CHIP_SYNCED),
                         ("not_synced", self.CHIP_NOT_SYNCED)):
            loc = self.page.locator(sel)
            out[key] = self._digits(loc.inner_text()) if loc.count() else -1
        if out["synced"] == -1 and out["not_synced"] == -1:
            # Fallback: read the whole summary block and split on the labels.
            summary = self.page.locator(self.SYNC_SUMMARY)
            if summary.count():
                text = summary.inner_text()
                for key, label in (("synced", "Synced"),
                                   ("not_synced", "Not Synced")):
                    if label in text:
                        out[key] = self._digits(text.split(label)[-1])
        return out

    def apply_webservice_filter(self, value: str) -> "StyleNumberListPage":
        self.select_option(self.FILTER_WEBSERVICE_SYNC, value)
        self.click_button(self.BTN_FILTER)
        self.page.wait_for_load_state("networkidle")
        return self

    def open_details(self, row: int = 0) -> "StyleNumberListPage":
        self.click_row_action(row, action="View")
        return self

    def details_text(self) -> str:
        modal = self.modal()
        return modal.inner_text() if modal.count() else ""

    def collapse_group(self, index: int = 0) -> "StyleNumberListPage":
        """Collapse a size group in the details modal.

        The size-group toggle is `button.rfid-mother-size-toggle` ("View"
        collapsed -> "Hide" + `is-open` expanded; probe_mod_p 2026-10-19,
        the same widget as the Mother List children modal).  Look it up
        across ALL open modals - `modal()` takes the LAST visible modal,
        which can be a different dialog than the details modal when more
        than one matches, and then the toggle is never found.  The app can
        also render rows before its click handlers bind, so poll for the
        "Hide" flip and retry once.
        """
        toggle = self.page.locator(
            ".modal.in .rfid-mother-size-toggle, "
            ".modal.show .rfid-mother-size-toggle")
        deadline = time.time() + 5               # wait for the toggle itself
        while time.time() < deadline and not toggle.count():
            self.page.wait_for_timeout(250)
        if not toggle.count():
            raise AssertionError(
                "Details modal has no size-group toggle (.rfid-mother-size-toggle)")
        for attempt in range(2):
            if toggle.nth(index).inner_text().strip() == "Hide":
                break
            toggle.nth(index).click()
            flip = time.time() + 6               # measured <1.2 s when healthy
            while time.time() < flip and \
                    toggle.nth(index).inner_text().strip() != "Hide":
                self.page.wait_for_timeout(250)
            if toggle.nth(index).inner_text().strip() == "Hide":
                break
            self.page.wait_for_timeout(500)      # handlers may still be binding
        if toggle.nth(index).inner_text().strip() != "Hide":
            raise AssertionError(
                "Size-group toggle never became 'Hide': the details modal "
                "group could not be expanded")
        toggle.nth(index).click()
        self.page.wait_for_timeout(300)
        return self

    def export(self):
        with self.page.expect_download() as dl:
            self.click_button(self.BTN_EXPORT)
        return dl.value
