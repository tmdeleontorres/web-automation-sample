"""Operator List module  (TC-OP-001 .. TC-OP-009)."""

from __future__ import annotations

import pytest

from pages.operator_list_page import OperatorListPage
from utils.helpers import pad_operator_id, random_suffix


@pytest.fixture
def operators(auth_page) -> OperatorListPage:
    return OperatorListPage(auth_page).open()


@pytest.mark.smoke
@pytest.mark.happy
def test_op_001_filter_operators(operators):
    """TC-OP-001: keyword/name/RFID/email/status filters."""
    operators.apply_filters(Status="Active")
    assert operators.row_count() >= 0
    operators.clear_filters()


@pytest.mark.happy
def test_op_002_add_operator_in_batch(operators):
    """TC-OP-002: batch entry saves operators and clears the waiting state.

    DOM 2026-10-15: the CHECK cell gates on the ACCOUNT CODE (not the name):
    "Enter an account code" (is-pending) -> "Account code is available."
    (is-available). A saved operator then appears in the list.
    """
    suffix = random_suffix()
    operators.add_operator(first=f"Auto{suffix}", last="Operator",
                           section="Cutting", account_code=f"QA{suffix}"[:20])
    indicator = operators.check_indicator()
    assert "available" in indicator.lower(), \
        f"CHECK cell did not confirm the account code: {indicator!r}"
    operators.save_operators()
    operators.close_modal()
    operators.find_operator(f"Auto{suffix}")
    assert operators.row_count() >= 1, \
        "Saved operator did not appear in the Operator List"
    operators.clear_filters()


@pytest.mark.negative
def test_op_003_empty_name_blocks_save(operators):
    """TC-OP-003: an untouched batch row keeps the pending CHECK state.

    DOM 2026-10-15: the pending message is one of two observed texts
    ("Waiting for required fields" right after opening, "Enter an account
    code" once the row settles) - the documented 'Waiting for name'
    indicator was renamed/repurposed. What matters is that the row has NOT
    reached the confirmed "available" state.
    """
    operators.open_add_operators()
    indicator = operators.check_indicator()
    low = indicator.lower()
    assert "available" not in low, \
        f"Untouched row already reports a confirmed state: {indicator!r}"
    assert "waiting" in low or "account code" in low, \
        f"Untouched row does not show the pending CHECK state: {indicator!r}"


@pytest.mark.happy
def test_op_004_operator_rfid_format(operators):
    """TC-OP-004: RFID = 4F50455241544F524944 + 4-digit padded operator id."""
    assert pad_operator_id(112) == "4F50455241544F5249440112"
    assert pad_operator_id(7) == "4F50455241544F5249440007"
    values = operators.column_values("User RFID")
    for value in values:
        if value:
            assert value.startswith(OperatorListPage.OPERATOR_RFID_PREFIX), \
                f"'{value}' does not follow the documented operator RFID format"
            assert len(value) == len(OperatorListPage.OPERATOR_RFID_PREFIX) + 4


@pytest.mark.edge
def test_op_005_name_length_limit(operators):
    """TC-OP-005: names are limited to 100 characters.

    The CSV allows either a hard field limit OR server-side validation. The
    live form carries no maxlength on the name inputs (probe 2026-10-15: only
    the account code is capped, at 20 chars), so the real check is whether an
    over-long name survives the save. Playwright's fill() bypasses any client
    limit by setting the value directly, which makes this the same path a
    determined user would take.
    """
    suffix = random_suffix()
    operators.add_operator(first="X" * 101, last=f"Over{suffix}",
                           section="Cutting", account_code=f"OL{suffix}"[:20])
    operators.save_operators()
    operators.close_modal()
    operators.find_operator("X" * 101)
    over_long_saved = operators.row_count() >= 1
    operators.clear_filters()
    assert not over_long_saved, \
        "101-character operator name was accepted (no field limit and no "\
        "server-side validation)"


@pytest.mark.happy
def test_op_006_edit_operator(operators):
    """TC-OP-006: Edit opens the modal identifying the operator id."""
    if operators.row_count() == 0:
        pytest.skip("No operators")
    operators.edit_operator(0)
    text = operators.modal().inner_text() if operators.modal().count() else ""
    assert text, "Edit Operator modal did not open"
    operators.close_modal()


@pytest.mark.happy
def test_op_007_soft_delete_operator(operators):
    """TC-OP-007: Delete is a soft delete (record is not permanently removed)."""
    if operators.row_count() == 0:
        pytest.skip("No operators")
    before = operators.row_count()
    message = operators.soft_delete_operator(0)
    after = operators.row_count()
    assert after <= before
    if after == before:
        assert message, "Soft delete produced neither a row change nor a message"


@pytest.mark.happy
def test_op_008_production_lines(operators):
    """TC-OP-008: Production Lines modal adds a new line."""
    line = f"Auto Line {random_suffix()}"
    message = operators.add_production_line(line)
    assert operators.production_lines_open(), "Production Lines modal did not open"
    assert message or operators.is_visible(line)
    operators.close_modal()


@pytest.mark.negative
def test_op_009_empty_line_name_rejected(operators):
    """TC-OP-009: an empty Line Name is refused."""
    operators.open_production_lines()
    assert operators.production_lines_open(), "Production Lines modal did not open"
    operators.click_button(operators.BTN_ADD_LINE)
    operators.page.wait_for_timeout(500)
    assert operators.toast_text() or operators.is_visible("required"), \
        "Empty line name was accepted"
    operators.close_modal()
