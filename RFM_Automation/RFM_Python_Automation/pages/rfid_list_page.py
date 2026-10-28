"""RfidListPage - "RFID List" (saved records, admin soft delete, exports).

Covers TC-RL-001 .. TC-RL-009.
"""

from __future__ import annotations

import time

from config import settings
from pages.list_page import ListPage


class RfidListPage(ListPage):
    path = settings.MODULE_PATHS["rfid_list"]
    sidebar_label = settings.NAV["rfid_list"]
    heading = "RFID List"

    BTN_DELETE_SELECTED = "#rfid-recent-delete"
    BTN_SYNC_WMS = "#rfid-recent-sync-wms"
    MENU_MORE_ACTIONS = "More actions"
    ITEM_SYNC_WMS = "Sync WMS"
    ITEM_SYNC_WEBSERVICE = "Sync Web Service"
    PLACEHOLDER_HINTS = ("style:SB", "item:Athenea", "size:XS", "epc:3035", "mother")

    # quick-search operator syntax documented in the table Search placeholder
    SEARCH_OPERATORS = ["style:SB", "item:Athenea", "size:XS", "epc:3035", "mother"]

    # ------------------------------------------------------------------ #
    def select_row(self, row: int = 0) -> "RfidListPage":
        box = self.rows().nth(row).locator("input[type=checkbox]")
        box.first.check()
        return self

    def delete_selected(self) -> str:
        """Returns 'missing' / 'disabled' / 'clicked' (+ any toast message)."""
        btn = self.page.locator(self.BTN_DELETE_SELECTED)   # verified id
        if not btn.count():
            return "missing"
        if btn.first.is_disabled():
            return "disabled"
        btn.first.click()
        self.page.wait_for_timeout(800)
        return self.toast_text() or "clicked"

    def disabled_delete_reason(self, row: int) -> str:
        """Tooltip / title of an ineligible row checkbox."""
        box = self.rows().nth(row).locator("input[type=checkbox]")
        return box.first.get_attribute("title") or box.first.get_attribute("disabled") or ""

    def open_more_actions(self) -> "RfidListPage":
        icon = self.find(
            self.page.get_by_role("button", name=self.MENU_MORE_ACTIONS, exact=False),
            self.page.locator(".dropdown-toggle, .btn-more, [title*=More]"),
        )
        icon.click()
        self.page.wait_for_timeout(300)
        return self

    def sync_wms(self) -> str:
        self.open_more_actions()
        self.page.get_by_text(self.ITEM_SYNC_WMS, exact=True).first.click()
        self.page.wait_for_timeout(1500)
        return self.toast_text()

    def toggle_print_status(self, row: int = 0) -> "RfidListPage":
        """Documented shortcut: double right-click on the Printed badge.

        The badge shows the CURRENT value ("Yes" or "No"), so the click must
        target that text - hard-coding "No" made the second consecutive run
        miss (the badge had been flipped to "Yes" by the previous run).
        """
        idx = self.header_index("Printed")
        cell = self.rows().nth(row).locator("td").nth(idx)
        before = cell.inner_text().strip()
        cell.get_by_text(before, exact=True).first.click(
            button="right", click_count=2)
        # The flip is saved asynchronously; poll instead of a fixed sleep.
        deadline = time.time() + 4
        while time.time() < deadline:
            self.page.wait_for_timeout(250)
            if cell.inner_text().strip() != before:
                break
        return self

    def open_transaction_history(self, row: int = 0) -> "RfidListPage":
        self.click_row_action(row, action="View")
        return self
