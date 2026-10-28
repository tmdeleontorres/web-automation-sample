"""Item Code Status panel  (TC-ICS-001 .. TC-ICS-005).

Item codes
----------
`data.ITEM_CODE` (5057877230509) is the verified code used for generating
RFIDs.  Per the CSV preconditions the status-panel tests generate a series
first - the panel's controls are 0x0 (hidden) until a series exists, and the
documented expectations ("rows update", "remove drops rows") only apply to a
generated series.

Verified behaviour (2026-10-09 / 2026-10-15):
  * qty changes commit on BLUR (Tab); the textarea becomes `code: qty`
  * Update series opens a Generation Summary PREVIEW; Continue applies it
  * out-of-range qty (0 / 5001) is silently reverted, no update button
  * a removed code STAYS in the list with class `is-removed` but its rows
    and its textarea line are dropped
"""

from __future__ import annotations

import pytest

from pages.generator_page import GeneratorPage
from utils import test_data as data


@pytest.fixture
def gen(auth_page) -> GeneratorPage:
    """Fresh Generator page (the fixture navigates, so state never leaks)."""
    page = GeneratorPage(auth_page)
    page.open()
    page.select_tab(page.TAB_ITEM_CODE)
    return page


@pytest.mark.happy
def test_ics_001_added_and_new_labels(gen):
    """TC-ICS-001: generated code -> Added, ungenerated codes -> New."""
    gen.enter_item_codes(data.ITEM_CODE) \
       .set_starting_serial(9100).set_quantity(data.QTY_DOCUMENTED) \
       .generate_series().continue_summary()

    statuses = {s["code"]: s["status"] for s in gen.item_code_statuses()}
    assert statuses.get(data.ITEM_CODE) == "Added", \
        f"{data.ITEM_CODE} should be Added after generating"

    # add the documented codes without generating -> they must show as New
    gen.enter_item_codes(data.ITEM_CODES_MULTILINE)
    statuses = {s["code"]: s["status"] for s in gen.item_code_statuses()}
    for code in data.ITEM_CODES_NEW:
        assert statuses.get(code) == "New", f"{code} should be New (not generated yet)"


@pytest.mark.happy
def test_ics_001_count_is_item_codes_not_rows(gen):
    """TC-ICS-001: a count of 4 means four item codes, not four RFID rows."""
    gen.enter_item_codes(data.ITEM_CODES_MULTILINE) \
       .set_starting_serial(9400).set_quantity(2) \
       .generate_series().continue_summary()

    statuses = gen.item_code_statuses()
    assert len(statuses) == len(data.ITEM_CODES_MULTILINE), \
        f"Item Code Status should track {len(data.ITEM_CODES_MULTILINE)} codes"
    # 4 codes x qty 2 = 8 RFID rows - the counters are independent
    assert gen.row_count() == 8, \
        f"expected 4 codes x 2 rows = 8 generated rows, got {gen.row_count()}"
    assert len(statuses) != gen.row_count(), \
        "Status count must not equal the generated row count"


@pytest.mark.happy
def test_ics_002_search_item_code(gen):
    """TC-ICS-002: 'Search item code' filters; clearing restores all entries."""
    gen.enter_item_codes(data.ITEM_CODES_MULTILINE) \
       .set_starting_serial(9410).set_quantity(1) \
       .generate_series().continue_summary()

    target = data.ITEM_CODES_NEW[0]
    gen.search_item_code(target)
    visible = {s["code"] for s in gen.item_code_statuses(visible_only=True)}
    assert visible and visible <= {target}, \
        f"Search returned {visible} instead of only {target}"

    # clearing the search must bring every entry back
    gen.search_item_code("")
    restored = {s["code"] for s in gen.item_code_statuses(visible_only=True)}
    assert restored == set(data.ITEM_CODES_MULTILINE), \
        f"Clearing the search returned {restored}"


@pytest.mark.happy
def test_ics_003_update_series_applies_quantity(gen):
    """TC-ICS-003: changing Qty then Update series refreshes the series."""
    gen.enter_item_codes(data.ITEM_CODE) \
       .set_starting_serial(9200).set_quantity(4) \
       .generate_series().continue_summary()

    gen.set_item_code_qty(data.ITEM_CODE, 6)
    gen.update_series()
    assert gen.counters()["Total Generated"] == 6, \
        "Counters did not update to the new quantity"
    assert gen.row_count() == 6, "Generated rows did not update to the new quantity"
    # Save is still a separate step - nothing has been saved by the update
    assert gen.item_code_statuses()[0]["qty"] == "6"


@pytest.mark.negative
def test_ics_004_item_quantity_out_of_range(gen):
    """TC-ICS-004: per-item quantity must stay within 1..5000.

    Verified 2026-10-09: the input reverts to its previous value on blur and
    no update is offered - the series stays unchanged.
    """
    gen.enter_item_codes(data.ITEM_CODE) \
       .set_starting_serial(9300).set_quantity(data.QTY_MIN) \
       .generate_series().continue_summary()

    gen.set_item_code_qty(data.ITEM_CODE, data.QTY_ABOVE_MAX)
    gen.update_series()                     # button never appears -> no-op

    entry = {s["code"]: s for s in gen.item_code_statuses()}[data.ITEM_CODE]
    assert entry["qty"] == str(data.QTY_MIN), \
        f"Out-of-range Qty {data.QTY_ABOVE_MAX} must revert, input shows {entry['qty']}"
    assert gen.counters()["Total Generated"] == data.QTY_MIN, \
        "Series changed although the quantity was rejected"
    assert gen.row_count() == data.QTY_MIN, "Rows changed although qty was rejected"


@pytest.mark.happy
def test_ics_005_remove_item_code(gen):
    """TC-ICS-005: removing a code drops its rows; other codes stay intact.

    The entry itself REMAINS in the list flagged `is-removed` (app design) -
    what must disappear are its pending rows and its textarea line.
    """
    gen.enter_item_codes(data.ITEM_CODES_MULTILINE) \
       .set_starting_serial(9420).set_quantity(1) \
       .generate_series().continue_summary()
    assert gen.row_count() == len(data.ITEM_CODES_MULTILINE), \
        "Setup failed: expected one row per item code"

    target = data.ITEM_CODES_NEW[0]
    gen.remove_item_code(target)

    # entry stays visible with the removed flag
    statuses = {s["code"]: s for s in gen.item_code_statuses()}
    assert statuses[target]["removed"], \
        f"{target} should remain in the list with the is-removed flag"

    # its line and rows are gone, the other codes are untouched
    assert target not in gen.textarea_codes(), \
        f"{target} still present in the item-code textarea: {gen.textarea_codes()}"
    assert gen.row_count() == len(data.ITEM_CODES_MULTILINE) - 1, \
        f"Removing {target} left {gen.row_count()} rows"
    for code in data.ITEM_CODES_MULTILINE:
        if code == target:
            continue
        assert code in gen.textarea_codes(), f"{code} was dropped together with {target}"
        assert not statuses[code]["removed"], f"{code} must stay active"
        assert gen.rows_for_item_code(code) == 1, f"{code} lost its rows"
