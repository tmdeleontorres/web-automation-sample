"""RfidImportPage - "Others > Import" (spreadsheet upload, preview, confirm).

Covers TC-IMP-001 .. TC-IMP-009.
"""

from __future__ import annotations

import re

from config import settings
from pages.base_page import BasePage


class RfidImportPage(BasePage):
    path = settings.MODULE_PATHS["import"]
    sidebar_label = settings.NAV["import"]
    heading = "RFID Import"

    BTN_DOWNLOAD_TEMPLATE = "Download Template"
    BTN_CHOOSE_FILE = "Choose File"
    BTN_PREVIEW = "Preview Import"
    BTN_CONFIRM = "Confirm Import"
    BTN_RFID_LIST = "RFID List"
    EMPTY_PREVIEW = "No Spreadsheet Preview Yet"

    SUPPORTED_FORMATS = (".xlsx", ".xls", ".csv")

    # ------------------------------------------------------------------ #
    def download_template(self):
        with self.page.expect_download() as dl:
            self.click_button(self.BTN_DOWNLOAD_TEMPLATE)
        return dl.value

    def upload(self, file_path: str) -> "RfidImportPage":
        chooser = self.page.expect_file_chooser()
        self.click_button(self.BTN_CHOOSE_FILE)
        chooser.value.set_files(file_path)
        return self

    def preview(self) -> "RfidImportPage":
        self.click_button(self.BTN_PREVIEW)
        self.page.wait_for_timeout(1500)
        return self

    def preview_summary(self) -> dict:
        """{'total': n, 'new': n, 'update': n, 'mother': n, 'child': n}."""
        text = self.page.inner_text("body")
        out = {}
        for key, label in (("total", "Total Rows"), ("new", "New Rows"),
                           ("update", "Update Rows"), ("mother", "Mother Rows"),
                           ("child", "Child Rows")):
            m = re.search(label + r"\D{0,20}(\d+)", text, re.IGNORECASE)
            out[key] = int(m.group(1)) if m else -1
        return out

    def preview_is_empty(self) -> bool:
        return self.page.get_by_text(self.EMPTY_PREVIEW, exact=False).count() > 0

    def validation_text(self) -> str:
        for selector in (".validation", "[data-testid=validation]", ".alert"):
            loc = self.page.locator(selector)
            if loc.count():
                return loc.first.inner_text().strip()
        return ""

    def blocking_errors(self) -> bool:
        return bool(re.search(r"(invalid|error|failed)", self.validation_text(), re.I))

    def confirm_enabled(self) -> bool:
        btn = self.page.get_by_role("button", name=self.BTN_CONFIRM, exact=False)
        if not btn.count():
            return False
        return not btn.first.is_disabled()

    def confirm(self) -> str:
        self.click_button(self.BTN_CONFIRM)
        self.page.wait_for_timeout(2000)
        return self.toast_text()

    def open_rfid_list(self) -> "RfidImportPage":
        self.click_button(self.BTN_RFID_LIST)
        self.page.wait_for_load_state("domcontentloaded")
        return self
