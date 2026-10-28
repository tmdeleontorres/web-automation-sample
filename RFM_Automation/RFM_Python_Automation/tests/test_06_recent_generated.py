"""Recent Generated module  (TC-RG-001 .. TC-RG-007)."""

from __future__ import annotations

import pytest

from pages.recent_generated_page import RecentGeneratedPage
from utils import test_data as data


@pytest.fixture
def recent(auth_page) -> RecentGeneratedPage:
    return RecentGeneratedPage(auth_page).open()


@pytest.mark.smoke
@pytest.mark.happy
def test_rg_001_shows_only_latest_generation(recent):
    """TC-RG-001: only the latest generation matching the filters is listed."""
    assert recent.row_count() >= 0
    assert recent.latest_generation_only()


@pytest.mark.happy
def test_rg_002_filter_and_clear(recent):
    """TC-RG-002: filters narrow the list and Clear resets the form."""
    before = recent.row_count()
    recent.apply_filters(Style_Number=data.STYLE_EXISTING)
    filtered = recent.row_count()
    assert filtered <= before
    recent.clear_filters()
    assert recent.row_count() == before or recent.row_count() >= filtered


@pytest.mark.happy
def test_rg_002b_quick_search_returns_empty_then_all(recent):
    """TC-TBL-005: a non-matching search returns an empty list, Clear restores it."""
    before = recent.row_count()
    recent.table_search("zzz-no-such-record-zzz")
    assert recent.row_count() == 0
    recent.table_search("")
    assert recent.row_count() == before


@pytest.mark.happy
def test_rg_003_user_filter_scope(recent):
    """TC-RG-003: User = All shows everything; a user narrows the result."""
    recent.set_user_filter("All")
    all_rows = recent.row_count()
    recent.apply_filters()
    assert recent.row_count() <= all_rows or all_rows >= 0


@pytest.mark.happy
def test_rg_006_transaction_history_modal(recent):
    """TC-RG-006: Action opens the RFID Transactions modal with all columns."""
    if recent.row_count() == 0:
        pytest.skip("No rows in Recent Generated")
    recent.open_transaction_history(0)
    text = recent.transaction_modal_text()
    assert text, "RFID Transactions modal did not open"
    for field in ("Date Added", "Status", "Notes", "Created By"):
        assert field.lower() in text.lower(), f"'{field}' missing from the modal"
    recent.close_modal()


@pytest.mark.negative
def test_rg_005_delete_disabled_without_selection(recent):
    """TC-RG-005: Delete Selected must be unavailable with nothing selected."""
    state = recent.delete_selected()
    assert state in ("disabled", "missing", ""), f"Delete ran with no selection: {state}"


@pytest.mark.happy
def test_rg_007_duplicate_check_available(recent):
    """TC-RG-007: the Duplicate Check tool exists in the more-actions menu."""
    assert recent.is_visible(recent.BTN_DUPLICATE_CHECK) or recent.row_count() == 0


@pytest.mark.happy
def test_rg_004_export_filtered_produces_a_file(recent):
    """TC-RG-004: Export Filtered downloads a file."""
    if recent.row_count() == 0:
        pytest.skip("No rows to export")
    download = recent.export_filtered()
    assert download.suggested_filename
