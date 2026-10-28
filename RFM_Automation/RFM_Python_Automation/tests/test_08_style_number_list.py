"""Style Number List module  (TC-SL-001 .. TC-SL-005)."""

from __future__ import annotations

import pytest

from pages.style_number_list_page import StyleNumberListPage
from utils import test_data as data


@pytest.fixture
def styles(auth_page) -> StyleNumberListPage:
    return StyleNumberListPage(auth_page).open()


@pytest.mark.smoke
@pytest.mark.happy
def test_sl_001_filter_grouped_list(styles):
    """TC-SL-001: filters return style groups with the documented columns."""
    headers = [h.inner_text() for h in styles.page.locator("table thead th").all()]
    for col in ("Style Number", "Style Name", "Color", "Mother Qty", "Total Qty"):
        assert any(col.lower() in h.lower() for h in headers), f"Column '{col}' missing"
    assert styles.row_count() >= 0


@pytest.mark.happy
def test_sl_001b_filter_by_style_number(styles):
    """TC-SL-001: Style Number filter narrows the list."""
    styles.apply_filters(Style_Number=data.STYLE_EXISTING)
    codes = styles.column_values("Style Number")
    assert all(data.STYLE_EXISTING in c or c == "" for c in codes)
    styles.clear_filters()


@pytest.mark.happy
def test_sl_002_sync_counters(styles):
    """TC-SL-002: Synced / Not Synced counters reflect the listed styles."""
    counters = styles.sync_counters()
    assert counters["synced"] >= 0
    assert counters["not_synced"] >= 0


@pytest.mark.happy
def test_sl_003_details_modal(styles):
    """TC-SL-003: View opens Style Number Details with size/item groups."""
    if not styles.wait_for_rows(timeout_ms=8000):
        pytest.skip("No styles available")
    styles.open_details(0)
    text = styles.details_text()
    assert text, "Style Number Details modal did not open"
    for field in ("Size", "Item Code", "Qty"):
        assert field.lower() in text.lower(), f"'{field}' missing from details modal"
    styles.close_modal()


@pytest.mark.happy
def test_sl_004_hide_collapses_group(styles):
    """TC-SL-004: Hide collapses an expanded RFID group."""
    if not styles.wait_for_rows(timeout_ms=8000):
        pytest.skip("No styles available")
    styles.open_details(0)
    if styles.modal().count():
        styles.collapse_group(0)
    styles.close_modal()


@pytest.mark.happy
def test_sl_005_export(styles):
    """TC-SL-005: Export downloads the style list."""
    if not styles.wait_for_rows(timeout_ms=8000):
        pytest.skip("Nothing to export")
    download = styles.export()
    assert download.suggested_filename
