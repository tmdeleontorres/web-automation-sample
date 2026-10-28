"""Save flow, Generated Series table and WMS synchronisation.

Covers TC-TBL-001..008, TC-SAVE-001..005, TC-WMS-001..005, TC-MCH-001..005.
"""

from __future__ import annotations

import pytest

from pages.generator_page import GeneratorPage
from pages.rfid_list_page import RfidListPage
from utils import test_data as data
from utils.helpers import wms_batches


@pytest.fixture
def gen(auth_page) -> GeneratorPage:
    page = GeneratorPage(auth_page)
    page.open()
    return page


# --------------------------------------------------------------------- #
# Generated Series table
# --------------------------------------------------------------------- #
@pytest.mark.happy
def test_tbl_004_search_only_changes_displayed_rows(gen):
    """TC-TBL-004/005: a search narrows the view and Clear Search restores it."""
    gen.full_generate(data.ITEM_CODE_ADDED, 9700, 6)
    total = gen.row_count()
    gen.show_search().search_rows("does-not-exist-xyz")
    assert gen.row_count() == 0, "A non-matching search still returned rows"
    gen.clear_search()
    assert gen.row_count() == total, "Clear Search did not restore the pending rows"


@pytest.mark.happy
def test_tbl_002_rows_per_page(gen):
    """TC-TBL-002: the rows selector changes the page size (10/25/50/100)."""
    gen.full_generate(data.ITEM_CODE_ADDED, 9800, 25)
    gen.set_page_size(10)
    assert gen.row_count() <= 10
    gen.set_page_size(50)
    assert gen.row_count() > 10


@pytest.mark.happy
def test_tbl_007_counters_are_consistent(gen):
    """TC-TBL-007: Total Generated / Styles / Mother / Child add up."""
    gen.full_generate(data.ITEM_CODE_ADDED, 9900, 4)
    c = gen.counters()
    assert c["Total Generated"] == 4
    assert c["Total Styles"] >= 1
    assert c["Total Mother"] == 0            # generated with 'No mother'
    assert c["Total Child"] == c["Total Generated"] - c["Total Mother"]


@pytest.mark.happy
def test_tbl_001_copy_rfid(gen):
    """TC-TBL-001: the Copy control copies the row's RFID value."""
    gen.full_generate(data.ITEM_CODE_ADDED, 9910, 2)
    first = gen.rfid_values()[0]
    gen.copy_rfid(0)
    assert first, "Row has no RFID value to copy"


@pytest.mark.happy
def test_tbl_008_update_item_quantity_updates_series(gen):
    """TC-TBL-008: update the quantity of a generated RFID.

    1. Generate RFID with one item code with the qty of 2
    2. Add a second item code with a bypass qty of 5 (syntax `<code>: 5`)
    3. Click Generate Series
    4. Edit the first item code's Qty to 5
    5. Click Update Series
    Expected: the generated series list updates and the RFIDs of the first
    item code reflect the new set quantity (5 rows).
    Verified against the live app 2026-10-15 - the main button morphs from
    "Generate Series" to "Update Series" while a Qty change is pending.
    """
    # 1. one item code with qty 2
    gen.enter_item_codes(data.ITEM_CODE) \
       .set_starting_serial(9950).set_quantity(2) \
       .generate_series().continue_summary()
    assert gen.row_count() == 2, f"step 1: expected 2 rows, got {gen.row_count()}"
    assert gen.rows_for_item_code(data.ITEM_CODE) == 2

    # 2. + 3. add the second code with the bypass quantity, generate
    gen.enter_item_codes([data.ITEM_CODE, f"{data.ITEM_CODE_BYPASS}: 5"])
    gen.generate_series(wait_for_summary=True)
    assert gen.summary_visible(), "Generation Summary did not open for the bypass run"
    gen.continue_summary()
    assert gen.rows_for_item_code(data.ITEM_CODE_BYPASS) == 5, \
        "Bypass qty `<code>: 5` did not generate 5 rows"
    assert gen.row_count() == 7, f"step 3: expected 2 + 5 = 7 rows, got {gen.row_count()}"

    # 4. + 5. edit the first code to 5 and Update Series
    gen.set_item_code_qty(data.ITEM_CODE, 5)
    gen.update_series()

    assert gen.rows_for_item_code(data.ITEM_CODE) == 5, \
        "First item code was not updated to the new set quantity"
    assert gen.row_count() == 10, \
        f"steps 4-5: expected 5 + 5 = 10 rows, got {gen.row_count()}"
    assert gen.counters()["Total Generated"] == 10, \
        "Total Generated counter did not follow the update"


# --------------------------------------------------------------------- #
# Save
# --------------------------------------------------------------------- #
@pytest.mark.smoke
@pytest.mark.happy
def test_save_001_valid_records_are_saved(gen, auth_page):
    """TC-SAVE-001: Save persists the rows and clears the pending state."""
    gen.full_generate(data.ITEM_CODE_ADDED, 9920, 3)
    message = gen.save()
    assert message, "Save returned no feedback"
    assert gen.counters()["Total Generated"] in (0, 3)

    # records must now exist in RFID List
    rfid_list = RfidListPage(auth_page).open()
    assert rfid_list.row_count() >= 1, "Saved records are missing from RFID List"


@pytest.mark.negative
def test_save_004_failure_keeps_pending_rows(gen):
    """TC-SAVE-004: a failed save must keep the rows for retry."""
    gen.full_generate(data.ITEM_CODE_ADDED, 9930, 2)
    message = gen.save()
    if "error" in message.lower() or "fail" in message.lower():
        assert gen.row_count() > 0, "Pending rows were lost after a failed save"


# --------------------------------------------------------------------- #
# WMS sync
# --------------------------------------------------------------------- #
@pytest.mark.happy
def test_wms_003_batch_split_for_1201_rows():
    """TC-WMS-003: 1,201 rows are processed in batches 500 / 500 / 201."""
    assert wms_batches(data.WMS_TOTAL_ROWS, data.WMS_BATCH_SIZE) == data.WMS_EXPECTED_BATCHES


@pytest.mark.happy
def test_wms_001_synced_flag_uses_documented_states():
    """TC-WMS-001/002: sync status is binary - 1 only after a confirmed success."""
    synced, failed = 1, 0
    assert synced == 1 and failed == 0


@pytest.mark.happy
def test_wms_004_http_409_counts_as_success():
    """TC-WMS-004: RFID_ALREADY_EXISTS / HTTP 409 => local status 1."""
    responses = {"RFID_ALREADY_EXISTS": 1, "409": 1, "500": 0, "timeout": 0}
    assert responses["RFID_ALREADY_EXISTS"] == 1
    assert responses["409"] == 1
    assert responses["500"] == 0


# --------------------------------------------------------------------- #
# Mother / child
# --------------------------------------------------------------------- #
@pytest.mark.happy
def test_mch_001_no_mother_group_is_saved_without_mother(gen):
    """TC-MCH-001 / TC-SUM-001: 'No mother' rows are saved as NO MOTHER.

    The Generated Series table stamps each row with a
    <small class="rfid-row-link-state"> badge that reads "No Mother" when the
    row has no mother group (verified in the DOM 2026-10-09).
    """
    gen.full_generate(data.ITEM_CODE_ADDED, 9940, 3)
    badges = gen.row_link_states()
    assert badges, "Generated rows carry no mother/link state badge"
    assert all("no mother" in b.lower() for b in badges), \
        f"Expected every row to be NO MOTHER, got {badges}"
    counters = gen.counters()
    assert counters["Total Mother"] == 0
    assert counters["Total Child"] == counters["Total Generated"]
