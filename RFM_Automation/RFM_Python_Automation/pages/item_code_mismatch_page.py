"""ItemCodeMismatchPage - "Others > Item Code Mismatch" (Meiki data diffs).

Covers TC-ICM-001 .. TC-ICM-003.
"""

from __future__ import annotations

from config import settings
from pages.list_page import ListPage


class ItemCodeMismatchPage(ListPage):
    path = settings.MODULE_PATHS["item_code_mismatch"]
    sidebar_label = settings.NAV["item_code_mismatch"]
    heading = "Item Code Mismatch"

    # ------------------------------------------------------------------ #
    def summary_row(self, item_code: str) -> dict:
        """{'syncs': str, 'rfid_modified': str, 'last_updated': str}."""
        row = self.page.locator("table tbody tr", has_text=item_code).first
        cells = row.locator("td")
        texts = [cells.nth(i).inner_text().strip() for i in range(cells.count())]
        return {
            "item_code": item_code,
            "raw": texts,
            "syncs": texts[1] if len(texts) > 1 else "",
            "rfid_modified": texts[2] if len(texts) > 2 else "",
            "last_updated": texts[3] if len(texts) > 3 else "",
        }

    def open_modified_rows(self, item_code: str) -> "ItemCodeMismatchPage":
        row = self.page.locator("table tbody tr", has_text=item_code).first
        row.locator("td a, td button").first.click()
        self.page.wait_for_timeout(600)
        return self

    def modal_text(self) -> str:
        modal = self.modal()
        return modal.inner_text() if modal.count() else ""

    def changed_fields(self) -> list[str]:
        text = self.modal_text()
        known = ["item_name", "unit_name", "color_name", "size_name", "item_code"]
        return [f for f in known if f in text]

    def search_modified_rows(self, value: str) -> "ItemCodeMismatchPage":
        box = self.find(
            self.page.get_by_placeholder("Search Modified RFID Rows", exact=False),
            self.page.get_by_role("searchbox"),
        )
        box.fill(value)
        self.page.wait_for_timeout(400)
        return self
