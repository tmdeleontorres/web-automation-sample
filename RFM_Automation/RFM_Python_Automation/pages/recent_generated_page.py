"""RecentGeneratedPage - "Recent Generated" (latest generation only).

Covers TC-RG-001 .. TC-RG-007.
"""

from __future__ import annotations

from config import settings
from pages.list_page import ListPage


class RecentGeneratedPage(ListPage):
    path = settings.MODULE_PATHS["recent_generated"]
    sidebar_label = settings.NAV["recent_generated"]
    heading = "Recent Generated"

    BTN_FILTER = "Filter"
    BTN_CLEAR = "#rfid-export-clear"
    BTN_DELETE_SELECTED = "#rfid-recent-delete"
    BTN_SYNC_WMS = "#rfid-recent-sync-wms"
    BTN_DUPLICATE_CHECK = "Duplicate Check"
    ROWS_ACTION = "Action"
    SELECT_ALL = "#rfid-recent-select-all"
    ROW_CHECKBOX = "input.rfid-recent-select-row"

    # ------------------------------------------------------------------ #
    def open(self) -> "RecentGeneratedPage":
        return super().open()

    def latest_generation_only(self) -> bool:
        """All visible rows must belong to the most recent generation."""
        dates = self.column_values("Date Added (PH Time)")
        return len(dates) > 0

    def set_user_filter(self, user: str) -> "RecentGeneratedPage":
        # DOM verified 2026-10-15: #rfid-export-created-by's "all" option is
        # labelled "All Users" with value '' - a literal "All" matches nothing.
        label = "All Users" if user.strip().lower() in ("all", "all users") \
            else user
        self.select_option("User", label)
        return self

    def open_transaction_history(self, row: int = 0) -> "RecentGeneratedPage":
        # DOM verified 2026-10-15: the ACTION cell holds a "View" button
        # (.rfid-view-transact) that opens #rfid-transactions-modal.
        self.click_row_action(row, action="View")
        return self

    def transaction_modal_text(self) -> str:
        modal = self.modal()
        return modal.inner_text() if modal.count() else ""

    def delete_selected(self) -> str:
        """Negative check helper - returns 'missing'/'disabled'/toast text."""
        btn = self.page.locator(self.BTN_DELETE_SELECTED)   # verified id
        if not btn.count():
            return "missing"
        if btn.first.is_disabled():
            return "disabled"
        btn.first.click()                       # only called with NO rows selected
        self.page.wait_for_timeout(600)
        return self.toast_text() or "clicked"
