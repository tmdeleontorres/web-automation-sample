"""Item Code Mismatch module  (TC-ICM-001 .. TC-ICM-003)."""

from __future__ import annotations

import pytest

from pages.item_code_mismatch_page import ItemCodeMismatchPage
from utils import test_data as data


@pytest.fixture
def mismatch(auth_page) -> ItemCodeMismatchPage:
    return ItemCodeMismatchPage(auth_page).open()


@pytest.mark.smoke
@pytest.mark.happy
def test_icm_001_mismatch_summary_columns(mismatch):
    """TC-ICM-001: summary shows Item Code, Syncs, RFID Modified, Last Updated."""
    headers = [h.inner_text() for h in mismatch.page.locator("table thead th").all()]
    joined = " ".join(headers).lower()
    for col in ("item code", "syncs", "rfid modified", "last updated"):
        assert col in joined, f"Column '{col}' missing from Item Code Mismatch"
    assert mismatch.row_count() >= 0


@pytest.mark.happy
def test_icm_002_modified_rows_show_old_vs_meiki(mismatch):
    """TC-ICM-002: the modal compares Old Data with Meiki Data."""
    if mismatch.row_count() == 0:
        pytest.skip("No mismatched item codes")
    codes = mismatch.column_values("Item Code")
    mismatch.open_modified_rows(codes[0])
    text = mismatch.modal_text()
    assert text, "Modified RFID Rows modal did not open"
    for field in ("RFID", "Serial", "Changed Fields", "Old Data", "Meiki Data"):
        assert field.lower() in text.lower(), f"'{field}' missing from the modal"
    mismatch.close_modal()


@pytest.mark.happy
def test_icm_002b_changed_fields_identified(mismatch):
    """TC-ICM-002: changed field names (item_name / unit_name / color_name)."""
    if mismatch.row_count() == 0:
        pytest.skip("No mismatched item codes")
    codes = mismatch.column_values("Item Code")
    mismatch.open_modified_rows(codes[0])
    fields = mismatch.changed_fields()
    assert fields, "No changed field names were reported in the modal"
    mismatch.close_modal()


@pytest.mark.happy
def test_icm_003_search_modified_rows(mismatch):
    """TC-ICM-003: search inside the Modified RFID Rows modal."""
    if mismatch.row_count() == 0:
        pytest.skip("No mismatched item codes")
    codes = mismatch.column_values("Item Code")
    mismatch.open_modified_rows(codes[0])
    mismatch.search_modified_rows(data.ITEM_CODE_ADDED)
    assert mismatch.modal_text()
    mismatch.close_modal()


@pytest.mark.happy
def test_icm_001b_no_manual_update_button(mismatch):
    """TC-ICM-004: the screen is review-only - updates happen during generation."""
    assert not mismatch.is_visible("Update Now"), \
        "A manual Update control exists but is not documented"
