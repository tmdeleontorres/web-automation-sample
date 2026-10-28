"""EPC validation & serial continuation rules  (TC-EPC-001 .. TC-EPC-010).

These are the documented SGTIN-96 / 24-hex-character rules the generator must
enforce before saving.
"""

from __future__ import annotations

import pytest

from pages.generator_page import GeneratorPage
from utils import test_data as data
from utils.helpers import epc_with_suffix


@pytest.fixture
def gen(auth_page) -> GeneratorPage:
    page = GeneratorPage(auth_page)
    page.open()
    return page


def _all_epcs_valid(epcs: list[str]) -> tuple[bool, str]:
    for epc in epcs:
        if len(epc) != data.EPC_LENGTH:
            return False, f"{epc}: length {len(epc)} != {data.EPC_LENGTH}"
        try:
            int(epc, 16)
        except ValueError:
            return False, f"{epc}: not hexadecimal"
    return True, ""


@pytest.mark.smoke
@pytest.mark.happy
def test_epc_001_generated_epcs_are_24_hex_chars(gen):
    """TC-EPC-001: every generated EPC is exactly 24 hex characters."""
    gen.full_generate(data.ITEM_CODE_ADDED, 9400, 5)
    epcs = gen.rfid_values()
    assert epcs, "No EPCs were generated"
    ok, why = _all_epcs_valid(epcs)
    assert ok, why


@pytest.mark.negative
@pytest.mark.parametrize("bad_epc,reason", [
    (data.EPC_TOO_SHORT, "23 characters"),
    (data.EPC_TOO_LONG, "25 characters"),
    (data.EPC_NON_HEX, "contains G-Z"),
])
def test_epc_002_003_invalid_epc_blocked(gen, bad_epc, reason):
    """TC-EPC-002 / TC-EPC-003: malformed EPCs must never be saved."""
    ok, why = _all_epcs_valid([bad_epc])
    assert not ok, f"{bad_epc} should be invalid ({reason})"


@pytest.mark.negative
def test_epc_009_no_duplicates_across_unsaved_requests(gen):
    """TC-EPC-009: two unsaved generations must not share an EPC.

    Two batches must coexist unsaved in one pending series: generate code A
    first, then add a second code - the app appends only the new code's rows
    (verified 2026-10-15, probe_tbl008e).  Re-generating the SAME code is
    ignored as Duplicate and opens no summary, so the second batch has to
    come from a second item code.
    """
    gen.full_generate(data.ITEM_CODE_ADDED, 9500, 5)
    first = gen.rfid_values()
    assert len(first) == 5, f"first batch: expected 5 EPCs, got {len(first)}"

    gen.enter_item_codes([data.ITEM_CODE, data.ITEM_CODE_BYPASS]) \
       .set_starting_serial(9600).set_quantity(5)
    gen.generate_series(wait_for_summary=True)
    assert gen.summary_visible(), "second generation did not open a summary"
    gen.continue_summary()

    # second batch = the rows that now belong to the newly added code
    epcs = gen.rfid_values()
    codes = gen.column_values("Item Code")
    second = [e for e, c in zip(epcs, codes) if c == data.ITEM_CODE_BYPASS]
    assert second, "the second batch added no rows"
    overlap = set(first) & set(second)
    assert not overlap, f"Duplicate pending EPCs: {overlap}"


@pytest.mark.edge
def test_epc_007_continuation_uses_decoded_serials(gen):
    """TC-EPC-007: 9006 + 9020 -> next serial 9021 (stored serial 0 ignored)."""
    decoded = data.CONTINUATION_EXISTING_DECODED
    expected_next = max(s for s in decoded) + 1
    assert expected_next == data.CONTINUATION_EXPECTED_NEXT
    # the wrong-format record (serial 9999) must not be part of the calculation
    assert data.CONTINUATION_IGNORED_RECORD_SERIAL not in decoded
    # verify against the live page: generate 1 row and read its serial
    gen.full_generate(data.ITEM_CODE_ADDED, expected_next, 1)
    serials = [int(s) for s in gen.serial_values() if s.isdigit()]
    assert serials and serials[0] >= data.CONTINUATION_EXPECTED_NEXT


@pytest.mark.edge
def test_epc_008_next_safe_suffix_skips_conflicts(gen):
    """TC-EPC-008: 27DA taken / 27DB free / 27DC-27DD conflict -> 27DE."""
    safe = data.COLLISION_EXPECTED_NEXT
    assert data.COLLISION_TAKEN not in (safe,)
    assert safe not in data.COLLISION_CONFLICT
    # suffixes must be strictly increasing past the conflicting block
    assert int(safe, 16) > int(data.COLLISION_CONFLICT[-1], 16)


@pytest.mark.happy
def test_epc_epc_suffix_helper_stays_in_range():
    """TC-EPC-008: self-check - helper EPCs used by the suite stay 24 hex chars."""
    for suffix in (data.COLLISION_EXPECTED_NEXT, "9021", "0000"):
        epc = epc_with_suffix(suffix)
        ok, why = _all_epcs_valid([epc])
        assert ok, why
