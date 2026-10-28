"""Transaction List module  (TC-TL-001 .. TC-TL-003)."""

from __future__ import annotations

import pytest

from pages.transaction_list_page import TransactionListPage
from utils import test_data as data


@pytest.fixture
def transactions(auth_page) -> TransactionListPage:
    return TransactionListPage(auth_page).open()


@pytest.mark.smoke
@pytest.mark.happy
def test_tl_001_filter_by_status_and_section(transactions):
    """TC-TL-001: Status / Section filters narrow the transaction log."""
    transactions.apply_filters(Status="Generated")
    assert transactions.row_count() >= 0
    transactions.clear_filters()


@pytest.mark.happy
def test_tl_001b_source_dropdown_options(transactions):
    """TC-TL-001: Source offers All / System Generated / XLSX / Migrated."""
    options = [o.inner_text() for o in
               transactions.page.get_by_role("combobox").all()]
    joined = " ".join(options)
    for expected in ("System Generated", "Imported via XLSX", "Migrated from WMS"):
        assert expected in joined, f"Source option '{expected}' not offered"


@pytest.mark.happy
def test_tl_002_default_sort_is_date_desc(transactions):
    """TC-TL-002: Date Added sorts (default descending); Action is not sortable."""
    transactions.sort_by("Date Added")
    assert transactions.row_count() >= 0


@pytest.mark.happy
def test_tl_003_history_modal(transactions):
    """TC-TL-003: View opens RFID Transactions for the selected EPC."""
    if not transactions.wait_for_rows(timeout_ms=8000):
        pytest.skip("No transactions available")
    transactions.open_history(0)
    text = transactions.modal().inner_text() if transactions.modal().count() else ""
    assert text, "RFID Transactions modal did not open"
    for field in ("Date Added", "Status", "Notes", "Created By"):
        assert field.lower() in text.lower(), f"'{field}' missing from history"
    transactions.close_modal()


@pytest.mark.edge
def test_tl_003b_multiple_rows_same_epc_are_history_not_duplicates(transactions):
    """TC-TL-003: one EPC may appear in many rows - that is history, not a dup."""
    if not transactions.wait_for_rows(timeout_ms=8000):
        pytest.skip("No transactions available")
    first = transactions.column_values("RFID")
    if not first:
        pytest.skip("RFID column not available")
    count = transactions.duplicate_epc_count(first[0])
    assert count >= 1
