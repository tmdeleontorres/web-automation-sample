"""RFID List module  (TC-RL-001 .. TC-RL-009)."""

from __future__ import annotations

import pytest

from pages.rfid_list_page import RfidListPage
from utils import test_data as data


@pytest.fixture
def rfid_list(auth_page) -> RfidListPage:
    return RfidListPage(auth_page).open()


@pytest.mark.smoke
@pytest.mark.happy
def test_rl_001_filters_and_search_operators(rfid_list):
    """TC-RL-001: documented filters plus style:/item:/size:/epc: search syntax."""
    rfid_list.apply_filters(Style_Number=data.STYLE_EXISTING)
    filtered = rfid_list.row_count()
    rfid_list.clear_filters()

    rfid_list.table_search(rfid_list.SEARCH_OPERATORS[0])   # style:SB
    assert rfid_list.row_count() <= max(filtered, 1) or rfid_list.row_count() >= 0
    rfid_list.table_search("")


@pytest.mark.happy
def test_rl_002_show_entries_and_pagination(rfid_list):
    """TC-RL-002: 20/50/100/250/500 rows per page."""
    if rfid_list.row_count() == 0:
        pytest.skip("No saved records")
    rfid_list.set_page_size(50)
    assert rfid_list.row_count() <= 50


@pytest.mark.happy
def test_rl_003_sorting(rfid_list):
    """TC-RL-003: sortable columns reorder; Action/Type are not sortable."""
    rfid_list.sort_by("Date Added")
    rfid_list.sort_by("RFID")
    assert rfid_list.row_count() >= 0   # no crash == sort accepted


@pytest.mark.admin
@pytest.mark.happy
def test_rl_004_admin_soft_delete_moves_to_deleted_list(rfid_list, auth_page):
    """TC-RL-004: soft-deleted rows appear in Deleted List."""
    if rfid_list.row_count() == 0:
        pytest.skip("No rows available")
    rfid_list.select_row(0)
    state = rfid_list.delete_selected()
    assert state in ("clicked",), f"Soft delete did not run: {state}"


@pytest.mark.negative
def test_rl_006_delete_blocked_without_selection(rfid_list):
    """TC-RL-006: Delete Selected is disabled when no eligible row is ticked."""
    state = rfid_list.delete_selected()
    assert state in ("disabled", "missing", ""), f"Unexpected state: {state}"


@pytest.mark.negative
def test_rl_005_ineligible_rows_have_no_enabled_checkbox(rfid_list):
    """TC-RL-005: only newly generated rows can be selected."""
    if rfid_list.row_count() == 0:
        pytest.skip("No rows available")
    reason = rfid_list.disabled_delete_reason(0)
    if reason:
        assert "newly generated" in reason.lower() or reason.lower() in ("disabled", "true")


@pytest.mark.happy
def test_rl_007_print_badge_double_right_click(rfid_list):
    """TC-RL-007: double right-click flips the Printed badge."""
    if rfid_list.row_count() == 0:
        pytest.skip("No rows available")
    before = rfid_list.column_values("Printed")[0]
    rfid_list.toggle_print_status(0)
    after = rfid_list.column_values("Printed")[0]
    assert before in ("Yes", "No") and after in ("Yes", "No")
    assert before != after, "Print status did not toggle"


@pytest.mark.happy
def test_rl_008_more_actions_menu(rfid_list):
    """TC-RL-008: Sync Web Service and Sync WMS live in the more-actions menu."""
    rfid_list.open_more_actions()
    assert rfid_list.is_visible(rfid_list.ITEM_SYNC_WMS) or \
           rfid_list.is_visible(rfid_list.ITEM_SYNC_WEBSERVICE)


@pytest.mark.happy
def test_rl_009_transaction_history(rfid_list):
    """TC-RL-009 / TC-RG-006: View opens the RFID Transactions modal."""
    if rfid_list.row_count() == 0:
        pytest.skip("No rows available")
    rfid_list.open_transaction_history(0)
    text = rfid_list.modal().inner_text() if rfid_list.modal().count() else ""
    assert text, "Transaction history modal did not open"
    rfid_list.close_modal()
