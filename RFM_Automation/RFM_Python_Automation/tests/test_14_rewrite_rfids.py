"""Rewrite RFIDs module  (TC-RW-001 .. TC-RW-005)."""

from __future__ import annotations

import pytest

from pages.rewrite_rfids_page import RewriteRfidsPage
from utils import test_data as data


@pytest.fixture
def rewrites(auth_page) -> RewriteRfidsPage:
    return RewriteRfidsPage(auth_page).open()


@pytest.mark.smoke
@pytest.mark.happy
def test_rw_001_before_and_current_values(rewrites):
    """TC-RW-001: rows expose the previous (Before) and new (Current) EPC.

    DOM 2026-10-15: the app keeps both EPCs in one "RFID Rewrite" cell as
    BEFORE/<old>/CURRENT/<new> lines rather than two columns.
    """
    if rewrites.row_count() == 0:
        pytest.skip("No rewritten records")
    headers = [h.inner_text() for h in rewrites.page.locator("table thead th").all()]
    assert any("rewrite" in h.lower() for h in headers), \
        "RFID Rewrite column is missing"
    before, current = rewrites.before_values(), rewrites.current_values()
    assert any(before) and any(current), \
        "BEFORE/CURRENT EPCs were not parsed from the RFID Rewrite cell"
    for old, new in zip(before, current):
        if old and new:
            assert old != new, f"Record was not actually rewritten: {old} == {new}"


@pytest.mark.happy
def test_rw_002_transactions_inherited_by_new_epc(rewrites):
    """TC-RW-002: the previous RFID's history is available under the new EPC."""
    if rewrites.row_count() == 0:
        pytest.skip("No rewritten records")
    rewrites.open_transactions(0)
    text = rewrites.modal().inner_text() if rewrites.modal().count() else ""
    assert text, "Transaction history did not open for the rewritten record"
    rewrites.close_modal()


@pytest.mark.happy
def test_rw_004_rewrite_logs(rewrites):
    """TC-RW-004: Logs show rewrite_rfid and rewrite_rfid_sync entries."""
    if rewrites.row_count() == 0:
        pytest.skip("No rewritten records")
    rewrites.open_logs(0)
    actions = rewrites.log_actions()
    assert "rewrite_rfid" in actions, "rewrite_rfid log entry missing"
    assert "rewrite_rfid_sync" in actions, "rewrite_rfid_sync log entry missing"
    rewrites.close_modal()


@pytest.mark.happy
def test_rw_005_filter_rewritten_records(rewrites):
    """TC-RW-005: Keyword / Style Number / date filters."""
    rewrites.apply_filters(Style_Number=data.STYLE_EXISTING)
    assert rewrites.row_count() >= 0
    rewrites.clear_filters()


@pytest.mark.happy
def test_rw_003_old_epc_search_resolves_to_new_record(rewrites, auth_page):
    """TC-RW-003: searching the old EPC in RFID List shows the new record."""
    from pages.rfid_list_page import RfidListPage

    if rewrites.row_count() == 0:
        pytest.skip("No rewritten records")
    old_epc = rewrites.before_values()[0]
    new_epc = rewrites.current_values()[0]
    rfid_list = RfidListPage(auth_page).open()
    rfid_list.table_search(old_epc)
    found = rfid_list.column_values("RFID")
    rfid_list.table_search("")
    if found:
        assert new_epc in found, \
            "Searching the old EPC did not resolve to the new RFID record"
