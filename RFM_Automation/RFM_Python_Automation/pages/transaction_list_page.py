"""TransactionListPage - "Transaction List" (RFID transaction logs).

Covers TC-TL-001 .. TC-TL-003.
"""

from __future__ import annotations

from config import settings
from pages.list_page import ListPage


class TransactionListPage(ListPage):
    path = settings.MODULE_PATHS["transaction_list"]
    sidebar_label = settings.NAV["transaction_list"]
    heading = "Transaction List"

    # verified 2026-10-09: this module uses rfid-transaction-* filter ids
    FILTER_IDS = {
        "keyword": "#rfid-transaction-keyword",
        "rfid": "#rfid-transaction-rfid",
        "status": "#rfid-transaction-status",
        "section": "#rfid-transaction-section",
        "style number": "#rfid-transaction-style",
        "item code / gtin": "#rfid-transaction-gtin",
        "gtin": "#rfid-transaction-gtin",
        "color": "#rfid-transaction-color",
        "size": "#rfid-transaction-size",
        "serial": "#rfid-transaction-serial",
        "source": "#rfid-transaction-source",
        "mother status": "#rfid-transaction-mother-status",
        "created by": "#rfid-transaction-created-by",
        "date from": "#rfid-transaction-date-from",
        "date to": "#rfid-transaction-date-to",
    }
    ENTRIES_SELECTOR = "select[name=rfid-transaction-table_length]"

    FILTER_STATUS = "Status"
    FILTER_SECTION = "Section"
    FILTER_SOURCE = "Source"
    FILTER_CREATED_BY = "Created By"

    SOURCE_OPTIONS = ["All", "System Generated", "Imported via XLSX", "Migrated from WMS"]
    SECTION_EXAMPLE = "RFID Generator"

    # ------------------------------------------------------------------ #
    def filter_by_source(self, value: str) -> "TransactionListPage":
        self.select_option(self.FILTER_SOURCE, value)
        self.click_button(self.BTN_FILTER)
        self.page.wait_for_load_state("networkidle")
        return self

    def filter_by_section(self, value: str) -> "TransactionListPage":
        self.select_option(self.FILTER_SECTION, value)
        self.click_button(self.BTN_FILTER)
        self.page.wait_for_load_state("networkidle")
        return self

    def open_history(self, row: int = 0) -> "TransactionListPage":
        self.click_row_action(row, action="View")
        return self

    def history_rows(self) -> int:
        modal = self.modal()
        if not modal.count():
            return 0
        return modal.locator("tbody tr").count()

    def duplicate_epc_count(self, epc: str) -> int:
        """Transaction rows sharing one EPC (history - not duplicate records)."""
        return self.page.locator(f"table tbody tr:has-text('{epc}')").count()
