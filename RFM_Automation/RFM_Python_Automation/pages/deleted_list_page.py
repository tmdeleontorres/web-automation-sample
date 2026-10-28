"""DeletedListPage - "Others > Deleted List" (soft-deleted records, full delete).

Covers TC-DL-001 .. TC-DL-006.
"""

from __future__ import annotations

from config import settings
from pages.list_page import ListPage


class DeletedListPage(ListPage):
    path = settings.MODULE_PATHS["deleted_list"]
    sidebar_label = settings.NAV["deleted_list"]
    heading = "Deleted List"

    BTN_DELETE = "Delete"          # administrator FULL delete
    HAS_RESTORE = False            # documented: no Restore action exists

    # ------------------------------------------------------------------ #
    def has_restore_action(self) -> bool:
        return self.page.get_by_role("button", name="Restore").count() > 0

    def full_delete(self, row: int = 0) -> str:
        """Administrator hard delete of a soft-deleted record."""
        self.click_row_action(row, action=self.BTN_DELETE)
        # a confirmation dialog may appear - accept it if the app shows one
        confirm = self.page.get_by_role("button", name="Yes")
        if confirm.count() and confirm.first.is_visible():
            confirm.first.click()
        self.page.wait_for_timeout(900)
        return self.toast_text()

    def open_history(self, row: int = 0) -> "DeletedListPage":
        self.click_row_action(row, action="View")
        return self

    def deletion_fields_present(self) -> bool:
        """Deleted By / Deleted At columns must be rendered."""
        try:
            self.header_index("Deleted By")
            self.header_index("Deleted At")
            return True
        except AssertionError:
            return False
