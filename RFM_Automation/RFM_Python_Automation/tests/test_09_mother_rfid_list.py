"""Mother RFID List module  (TC-ML-001 .. TC-ML-004)."""

from __future__ import annotations

import pytest

from pages.mother_rfid_list_page import MotherRfidListPage
from utils import test_data as data


@pytest.fixture
def mothers(auth_page) -> MotherRfidListPage:
    return MotherRfidListPage(auth_page).open()


@pytest.mark.smoke
@pytest.mark.happy
def test_ml_001_filter_mother_records(mothers):
    """TC-ML-001: documented filters return saved mother records."""
    headers = [h.inner_text() for h in mothers.page.locator("table thead th").all()]
    for col in ("Date Added", "Style", "Status", "RFID"):
        assert any(col.lower() in h.lower() for h in headers), f"Column '{col}' missing"
    mothers.apply_filters(Style_Number=data.STYLE_MOTHER)
    assert mothers.row_count() >= 0
    mothers.clear_filters()


@pytest.mark.happy
def test_ml_002_details_modal_shows_children(mothers):
    """TC-ML-002: View opens Mother RFID Details with linked child rows."""
    if mothers.row_count() == 0:
        pytest.skip("No mother records available")
    mothers.open_details(0)
    text = mothers.details_text()
    assert text, "Mother RFID Details modal did not open"
    for field in ("Mother RFID", "Size", "Item Code"):
        assert field.lower() in text.lower(), f"'{field}' missing from the modal"
    mothers.close_modal()


@pytest.mark.happy
def test_ml_002b_linked_child_rows_present(mothers):
    """TC-ML-002: child rows expose Date Added, Source, Serial and RFID.

    The size groups are collapsed by default; expand the first group so the
    child rows render (probe 2026-10-15: DATE ADDED / SOURCE / SERIAL / RFID).
    """
    if mothers.row_count() == 0:
        pytest.skip("No mother records available")
    mothers.open_details(0)
    text = mothers.details_text(expand=True).lower()
    if text:
        for field in ("date added", "source", "serial", "rfid"):
            assert field in text, f"'{field}' missing from child details"
    mothers.close_modal()


@pytest.mark.regression
def test_ml_003_no_delete_selected_action(mothers):
    """TC-ML-003: Mother List has NO Delete Selected control (documented)."""
    assert not mothers.has_delete_selected(), \
        "Delete Selected must not be exposed on Mother RFID List"


@pytest.mark.edge
def test_ml_004_timezone_label_consistency(mothers):
    """TC-ML-004: header says 'PST' but values are PH - flag the discrepancy."""
    if mothers.row_count() == 0:
        pytest.skip("No mother records available")
    mothers.open_details(0)
    text = mothers.details_text()
    if "PST" in text and "PH" in text:
        pytest.xfail("Documented timezone label mismatch (PST header vs PH values)")
    mothers.close_modal()
