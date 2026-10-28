"""RewriteRfidsPage - "Others > Rewrite RFIDs" (before/after EPC, logs).

Covers TC-RW-001 .. TC-RW-005.
"""

from __future__ import annotations

from config import settings
from pages.list_page import ListPage


class RewriteRfidsPage(ListPage):
    path = settings.MODULE_PATHS["rewrite_rfids"]
    sidebar_label = settings.NAV["rewrite_rfids"]
    heading = "Rewrite RFIDs"

    # DOM verified 2026-10-15: there is NO separate "Before"/"Current"
    # column. Both EPCs live in the single "RFID REWRITE" cell as two lines:
    # "BEFORE" + <old EPC> + "CURRENT" + <new EPC>.
    REWRITE_HEADER = "RFID Rewrite"

    def _rewrite_pairs(self) -> list[tuple[str, str]]:
        out = []
        for raw in self.column_values(self.REWRITE_HEADER):
            tokens = [t.strip() for t in raw.splitlines() if t.strip()]
            before = current = ""
            for i, tok in enumerate(tokens):
                up = tok.upper()
                if up == "BEFORE" and i + 1 < len(tokens):
                    before = tokens[i + 1]
                elif up == "CURRENT" and i + 1 < len(tokens):
                    current = tokens[i + 1]
            out.append((before, current))
        return out

    def before_values(self) -> list[str]:
        return [b for b, _ in self._rewrite_pairs()]

    def current_values(self) -> list[str]:
        return [c for _, c in self._rewrite_pairs()]

    def open_transactions(self, row: int = 0) -> "RewriteRfidsPage":
        self.click_row_action(row, action="View")
        return self

    def open_logs(self, row: int = 0) -> "RewriteRfidsPage":
        self.click_row_action(row, action="Logs")
        return self

    def log_actions(self) -> list[str]:
        """The Rewrite RFID event types present in the open Logs modal.

        The CSV documents these as ``rewrite_rfid`` / ``rewrite_rfid_sync``,
        but the app renders them human-readable: the EVENT cell reads
        "Rewrite RFID" / "Rewrite RFID Sync" with "Generator Api" beneath
        (probe 2026-10-15). We return the documented snake_case tokens after
        normalising whitespace, so callers match the spec wording.
        """
        modal = self.modal()
        if not modal.count():
            return []
        # Normalise: "Rewrite RFID Sync" -> "rewrite_rfid_sync"
        norm = modal.inner_text().lower().replace(" ", "_")
        return [a for a in ("rewrite_rfid_sync", "rewrite_rfid") if a in norm]

    def has_details_button(self, index: int = 0) -> bool:
        modal = self.modal()
        return modal.count() and modal.get_by_role("button", name="Details").count() > index
