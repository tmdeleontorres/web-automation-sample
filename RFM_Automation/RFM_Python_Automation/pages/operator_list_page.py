"""OperatorListPage - "Others > Operator List" (operators + Production Lines).

Covers TC-OP-001 .. TC-OP-009 (incl. the documented RFID format).
"""

from __future__ import annotations

from config import settings
from pages.list_page import ListPage
from playwright.sync_api import expect
from utils.helpers import pad_operator_id


class OperatorListPage(ListPage):
    path = settings.MODULE_PATHS["operator_list"]
    sidebar_label = settings.NAV["operator_list"]
    heading = "Operator List"

    # verified 2026-10-09: operator-filter-* ids, rfid-operator-table
    FILTER_IDS = {
        "keyword": "#operator-filter-keyword",
        "first name": "#operator-filter-first-name",
        "last name": "#operator-filter-last-name",
        "user rfid": "#operator-filter-user-rfid",
        "account code": "#operator-filter-account-code",
        "user email": "#operator-filter-user-email",
        "status": "#operator-filter-status",
    }
    ENTRIES_SELECTOR = "select[name=rfid-operator-table_length]"
    TABLE = "#rfid-operator-table"

    BTN_ADD_OPERATORS = "Add Operators"
    BTN_ADD_ROW = "Add Row"
    BTN_SAVE_OPERATORS = "Save Operators"
    BTN_PRODUCTION_LINES = "Production Lines"
    BTN_UPDATE_OPERATOR = "Update Operator"
    LABEL_FIRST_NAME = "First Name"
    LABEL_LAST_NAME = "Last Name"
    LABEL_SECTION = "Section"
    LABEL_USER_EMAIL = "User Email"
    LABEL_LINE_NAME = "Line Name"
    BTN_ADD_LINE = "Add Line"
    # DOM verified 2026-10-15: the batch form has NO "Waiting for name"
    # indicator anymore. Each entry row carries a CHECK cell holding
    # span.operator-exists-indicator; on an empty row it reads
    # "Enter an account code". Entry inputs use operator-entry-* classes.
    # The name inputs enforce maxlength=100; account code maxlength=20.
    ENTRY_FIRST_NAME = ".modal:visible input.operator-entry-first-name"
    ENTRY_LAST_NAME = ".modal:visible input.operator-entry-last-name"
    ENTRY_ACCOUNT_CODE = ".modal:visible input.operator-entry-account-code"
    ENTRY_SECTION = ".modal:visible select.operator-entry-section"
    ENTRY_USER_EMAIL = ".modal:visible select.operator-entry-user-id"
    ENTRY_CHECK = ".modal:visible span.operator-exists-indicator"
    INDICATOR_PENDING = "Enter an account code"
    OPERATOR_RFID_PREFIX = settings.OPERATOR_RFID_PREFIX

    # ------------------------------------------------------------------ #
    def open_add_operators(self) -> "OperatorListPage":
        self._clear_any_modal()
        self.click_button(self.BTN_ADD_OPERATORS)
        self.page.wait_for_timeout(400)
        return self

    def _entry_row(self, index: int = 0):
        return self.page.locator(".modal:visible "
                                 "table.operator-entry-table tbody tr").nth(index)

    def add_operator(self, first: str, last: str, section: str,
                     email: str | None = None,
                     account_code: str | None = None) -> "OperatorListPage":
        self.open_add_operators()
        row = self._entry_row(0)
        row.locator("input.operator-entry-first-name").fill(first)
        row.locator("input.operator-entry-last-name").fill(last)
        row.locator("select.operator-entry-section").select_option(label=section)
        if account_code:                            # flips CHECK to is-available
            row.locator("input.operator-entry-account-code").fill(account_code)
            self.page.wait_for_timeout(600)
        if email:
            row.locator("select.operator-entry-user-id").select_option(label=email)
        self.page.wait_for_timeout(300)
        return self

    def find_operator(self, keyword: str) -> "OperatorListPage":
        """Search the list by keyword (first name), then press Filter."""
        self.page.locator(self.FILTER_IDS["keyword"]).first.fill(keyword)
        self.click_button(self.BTN_FILTER)
        try:
            self.page.wait_for_load_state("networkidle")
        except Exception:
            pass
        self.page.wait_for_timeout(600)
        return self

    def check_indicator(self) -> str:
        """Return the CHECK cell text of the first entry row.

        DOM 2026-10-15: this cell is an ACCOUNT CODE availability gate, not a
        name gate. It reads "Enter an account code" (class is-pending) until a
        code is typed, then "Account code is available." (class is-available)
        or a taken/not-available message. Typing a first/last name alone does
        NOT change it.
        """
        loc = self.page.locator(self.ENTRY_CHECK)
        return loc.first.inner_text().strip() if loc.count() else ""

    def save_operators(self) -> str:
        self.click_button(self.BTN_SAVE_OPERATORS)
        self.page.wait_for_timeout(1000)
        feedback = self.toast_text()
        if feedback:
            return feedback
        modal = self.modal()
        return modal.inner_text().strip() if modal.count() else ""

    def operator_rfid(self, row: int = 0) -> str:
        return self.column_values("User RFID")[row] if self.column_values("User RFID") else ""

    @staticmethod
    def expected_rfid(operator_id: int) -> str:
        """4F50455241544F524944 + 4-digit padded id (documented format)."""
        return pad_operator_id(operator_id)

    def edit_operator(self, row: int = 0) -> "OperatorListPage":
        self.click_row_action(row, action="Edit")
        return self

    def update_operator(self) -> str:
        self.click_button(self.BTN_UPDATE_OPERATOR)
        self.page.wait_for_timeout(900)
        return self.toast_text()

    def soft_delete_operator(self, row: int = 0) -> str:
        self.click_row_action(row, action="Delete")
        self.page.wait_for_timeout(700)
        return self.toast_text()

    # ---- Production Lines --------------------------------------------- #
    def open_production_lines(self) -> "OperatorListPage":
        """Open the Production Lines modal (#production-lines-modal)."""
        self._clear_any_modal()
        self.click_button(self.BTN_PRODUCTION_LINES)
        try:
            expect(self.page.locator("#production-lines-modal")).to_be_visible(
                timeout=4000)
        except Exception:                           # pragma: no cover - defect path
            pass                                    # test asserts visibility itself
        return self

    def production_lines_open(self) -> bool:
        return self.page.locator("#production-lines-modal").is_visible()

    def add_production_line(self, name: str) -> str:
        self.open_production_lines()
        if not self.production_lines_open():
            return ""                               # modal never opened
        self.fill_field(self.LABEL_LINE_NAME, name)
        self.click_button(self.BTN_ADD_LINE)
        self.page.wait_for_timeout(700)
        return self.toast_text()
