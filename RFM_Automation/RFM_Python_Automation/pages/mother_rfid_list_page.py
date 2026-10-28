"""MotherRfidListPage - "Mother List" (saved mother records + children modal).

Covers TC-ML-001 .. TC-ML-004.
"""

from __future__ import annotations

from config import settings
from pages.list_page import ListPage


class MotherRfidListPage(ListPage):
    path = settings.MODULE_PATHS["mother_list"]
    sidebar_label = settings.NAV["mother_list"]
    heading = "Mother RFID List"

    FILTER_MOTHER_STATUS = "Mother Status"
    MOTHER_ONLY = "Mother Only"
    HAS_MOTHER_ONLY = "Has Mother Only"
    NON_MOTHER_ONLY = "Non Mother Only"

    # ------------------------------------------------------------------ #
    # DOM verified 2026-10-15: View opens #rfid-mother-children-modal, which
    # lists size groups; each group's child rows are behind a
    # .rfid-mother-size-toggle button ("View" -> "Hide").
    SIZE_TOGGLE = ".rfid-mother-size-toggle"

    def open_details(self, row: int = 0) -> "MotherRfidListPage":
        self.click_row_action(row, action="View")
        self.page.wait_for_timeout(600)
        return self

    def expand_first_group(self) -> "MotherRfidListPage":
        """Expand the first size group so the child rows become visible."""
        toggle = self.modal().locator(self.SIZE_TOGGLE).first
        if toggle.count() and toggle.is_visible():
            toggle.click()
            self.page.wait_for_timeout(400)
        return self

    def details_text(self, expand: bool = False) -> str:
        modal = self.modal()
        if not modal.count():
            return ""
        if expand:
            self.expand_first_group()
            modal = self.modal()
        return modal.inner_text()

    def linked_child_count(self) -> int:
        """Row count shown at the top of the Mother RFID Details modal."""
        text = self.details_text()
        digits = "".join(ch if ch.isdigit() or ch == "," else " "
                         for ch in text.split("Child")[-1][:20]).replace(",", "")
        digits = "".join(ch for ch in digits if ch.isdigit())
        return int(digits) if digits else -1

    def has_delete_selected(self) -> bool:
        """Documented: no Delete Selected action exists on this page."""
        return self.page.get_by_role("button", name="Delete Selected").count() > 0

    def collapse_child_group(self, index: int = 0) -> "MotherRfidListPage":
        modal = self.modal()
        modal.get_by_role("button", name="Hide").nth(index).click()
        self.page.wait_for_timeout(300)
        return self
