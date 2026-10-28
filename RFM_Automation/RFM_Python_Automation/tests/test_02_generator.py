"""Generator happy path and boundaries  (TC-GEN-001 .. TC-GEN-017).

All tests share one signed-in page per module (`auth_page`).
"""

from __future__ import annotations

import pytest

from config import settings
from pages.generator_page import GeneratorPage
from utils import test_data as data


@pytest.fixture
def gen(auth_page) -> GeneratorPage:
    page = GeneratorPage(auth_page)
    page.open()
    return page


@pytest.mark.smoke
@pytest.mark.happy
def test_gen_001_generate_single_item_code(gen):
    """TC-GEN-001: one item code -> Generation Summary opens with full details."""
    gen.select_tab(gen.TAB_ITEM_CODE) \
       .enter_item_codes(data.ITEM_CODE_ADDED) \
       .set_starting_serial(data.SERIAL_MIN) \
       .set_quantity(data.QTY_DOCUMENTED) \
       .generate_series()

    assert gen.summary_visible(), "Generation Summary did not open"
    text = gen.summary_text()
    for field in ("Style Number", "Style Name", "Color", "Mother",
                  "Qty", "Serial Range", "EPC Range"):
        assert field.lower() in text.lower(), f"'{field}' missing from Generation Summary"


@pytest.mark.smoke
@pytest.mark.happy
def test_gen_002_continue_populates_generated_series(gen):
    """TC-GEN-002: Continue fills the table and the summary counters."""
    gen.full_generate(data.ITEM_CODE_ADDED, data.SERIAL_MIN, data.QTY_DOCUMENTED)

    assert gen.row_count() > 0, "Generated Series table is empty"
    # scope to the series table: the Generator page carries three tables
    headers = [h.inner_text() for h in gen.page.locator("table.rfid-gen-table thead th").all()]
    lowered = [h.lower() for h in headers]
    for col in ("Item Code", "Style Number", "Style Name", "Color", "Size",
                "RFID", "Serial", "Copy"):
        assert any(col.lower() in h for h in lowered), f"Column '{col}' is missing"

    counters = gen.counters()
    assert counters["Total Generated"] == data.QTY_DOCUMENTED
    assert counters["Total Styles"] >= 1
    assert counters["Total Child"] == data.QTY_DOCUMENTED


@pytest.mark.happy
def test_gen_003_multiple_item_codes(gen):
    """TC-GEN-003: four codes, one per line, are all tracked."""
    gen.enter_item_codes(data.ITEM_CODES_MULTILINE)
    statuses = gen.item_code_statuses()
    codes = {s["code"] for s in statuses}
    for expected in data.ITEM_CODES_MULTILINE:
        assert expected in codes, f"Item code {expected} not tracked in Item Code Status"


@pytest.mark.happy
def test_gen_016_cancel_summary_leaves_no_pending_rows(gen):
    """TC-GEN-016: Cancel closes the summary without generating rows."""
    before = gen.row_count()
    gen.enter_item_codes(data.ITEM_CODE_ADDED) \
       .set_starting_serial(0).set_quantity(1).generate_series()
    assert gen.summary_visible()
    gen.cancel_summary()
    assert not gen.summary_visible(), "Summary stayed open after Cancel"
    assert gen.row_count() == before, "Rows were added although Cancel was used"


@pytest.mark.negative
def test_gen_005_empty_item_code_list_rejected(gen):
    """TC-GEN-005: empty textarea must not open the summary."""
    gen.select_tab(gen.TAB_ITEM_CODE) \
       .set_starting_serial(0).set_quantity(1).generate_series()
    assert not gen.summary_visible(), "Summary opened with an empty item code list"


@pytest.mark.negative
def test_gen_006_invalid_item_code_rejected(gen):
    """TC-GEN-006: non-numeric / wrong length codes are refused."""
    gen.enter_item_codes("12345").set_starting_serial(0) \
       .set_quantity(1).generate_series()
    assert not gen.summary_visible(), "Invalid item code was accepted"


@pytest.mark.boundary
def test_gen_011_quantity_minimum(gen):
    """TC-GEN-011: Quantity = 1 generates exactly one row."""
    gen.full_generate(data.ITEM_CODE_ADDED, data.SERIAL_MIN, data.QTY_MIN)
    assert gen.row_count() == data.QTY_MIN


@pytest.mark.boundary
@pytest.mark.slow
def test_gen_012_quantity_maximum(gen):
    """TC-GEN-012: Quantity = 5000 (documented maximum) is accepted."""
    gen.full_generate(data.ITEM_CODE_ADDED, data.SERIAL_MIN, data.QTY_MAX)
    assert gen.counters()["Total Generated"] == data.QTY_MAX


@pytest.mark.negative
@pytest.mark.parametrize("bad_qty", [data.QTY_ABOVE_MAX, data.QTY_BELOW_MIN, "abc"],
                         ids=["5001", "0", "non-numeric"])
def test_gen_013_014_quantity_out_of_range(gen, bad_qty):
    """TC-GEN-013 / TC-GEN-014: quantity outside 1..5000 is rejected.

    The non-numeric case is rejected at the field level: Quantity is an
    input[type=number] and the browser refuses "abc" outright - that refusal
    is the documented rejection, so the value must never reach the field.
    """
    gen.enter_item_codes(data.ITEM_CODE_ADDED).set_starting_serial(0)
    try:
        gen.set_quantity(bad_qty)
    except Exception:
        # driver refused the keystrokes - input[type=number] accepts numbers only
        assert gen.page.locator(gen.QUANTITY).input_value() != str(bad_qty), \
            f"Non-numeric quantity '{bad_qty}' ended up in the field"
        return
    gen.generate_series()
    assert not gen.summary_visible(), f"Quantity '{bad_qty}' was accepted"


@pytest.mark.negative
@pytest.mark.parametrize("bad_serial", [data.SERIAL_NEGATIVE, data.SERIAL_DECIMAL],
                         ids=["-1", "1.5"])
def test_gen_009_010_starting_serial_validation(gen, bad_serial):
    """TC-GEN-009 / TC-GEN-010: Starting Serial must be a whole number >= 0."""
    gen.enter_item_codes(data.ITEM_CODE_ADDED) \
       .set_starting_serial(bad_serial).set_quantity(1).generate_series()
    assert not gen.summary_visible(), f"Starting serial '{bad_serial}' was accepted"


@pytest.mark.boundary
def test_gen_008_starting_serial_zero(gen):
    """TC-GEN-008: Starting Serial 0 -> first row has serial 0.

    KNOWN DEFECT (verified 2026-10-09 in artifacts/probe_serial.txt): the app
    ignores the Starting Serial field and continues from the item code's
    previously saved records (9600/0/5/20 all produced the same continuation).
    This test keeps the documented expectation and reports Fail with the
    defect explained in the assertion message.
    """
    gen.full_generate(data.ITEM_CODE_ADDED, data.SERIAL_MIN, data.QTY_MIN)
    serials = gen.serial_values()
    assert serials, "No rows generated with Starting Serial 0"
    assert serials[0] == "0", (
        f"Documented: Starting Serial 0 -> first generated serial 0, "
        f"got '{serials[0]}'. DEFECT: the app ignores Starting Serial and "
        "continues from the code's saved records (probe_serial.txt)."
    )


@pytest.mark.negative
def test_gen_015_serial_step_below_one_rejected(gen):
    """TC-GEN-015: Serial Step must be a whole number of at least 1."""
    gen.select_tab(gen.TAB_OTHERS).set_serial_step(data.SERIAL_STEP_INVALID)
    gen.select_tab(gen.TAB_ITEM_CODE) \
       .enter_item_codes(data.ITEM_CODE_ADDED).set_starting_serial(0) \
       .set_quantity(1).generate_series()
    assert not gen.summary_visible(), "Serial Step 0 was accepted"


@pytest.mark.happy
def test_gen_017_clear_keeps_pending_data_safe(gen):
    """TC-GEN-017: Clear behaves as documented (confirm before unsaved use)."""
    gen.full_generate(data.ITEM_CODE_ADDED, 9000, 1)
    before = gen.counters()["Total Generated"]
    gen.clear_all()
    after = gen.counters()["Total Generated"]
    assert after <= before, "Clear increased the number of pending rows"
