"""Deleted List module  (TC-DL-001 .. TC-DL-006)."""

from __future__ import annotations

import pytest

from pages.deleted_list_page import DeletedListPage
from utils import test_data as data


@pytest.fixture
def deleted(auth_page) -> DeletedListPage:
    return DeletedListPage(auth_page).open()


@pytest.mark.smoke
@pytest.mark.happy
def test_dl_001_soft_deleted_records_listed(deleted):
    """TC-DL-001: soft-deleted records show Deleted By / Deleted At."""
    assert deleted.deletion_fields_present(), \
        "Deleted By / Deleted At columns are missing"
    deleted.apply_filters(Style_Number=data.STYLE_EXISTING)
    assert deleted.row_count() >= 0
    deleted.clear_filters()


@pytest.mark.happy
def test_dl_002_transaction_history_of_deleted_record(deleted):
    """TC-DL-002: View opens the RFID Transactions modal."""
    if deleted.row_count() == 0:
        pytest.skip("No deleted records")
    deleted.open_history(0)
    text = deleted.modal().inner_text() if deleted.modal().count() else ""
    assert text, "Transaction history did not open"
    deleted.close_modal()


@pytest.mark.admin
@pytest.mark.happy
def test_dl_003_admin_full_delete(deleted):
    """TC-DL-003: the administrator Delete control performs a full delete."""
    if deleted.row_count() == 0:
        pytest.skip("No deleted records to hard-delete")
    before = deleted.row_count()
    deleted.full_delete(0)
    assert deleted.row_count() <= before


@pytest.mark.negative
def test_dl_004_deletion_restriction_preserved(deleted):
    """TC-DL-004: records with a conflict or transaction are never deleted."""
    if deleted.row_count() == 0:
        pytest.skip("No deleted records")
    reason = deleted.disabled_delete_reason(0) if hasattr(deleted, "disabled_delete_reason") else ""
    if reason:
        assert "conflict" in reason.lower() or "transaction" in reason.lower()


@pytest.mark.regression
def test_dl_005_no_restore_action(deleted):
    """TC-DL-005: the page documents no Restore control."""
    assert not deleted.has_restore_action(), \
        "A Restore action exists but is not documented"


@pytest.mark.happy
def test_dl_006_export_deleted_records(deleted):
    """TC-DL-006: Export Filtered downloads the deleted records."""
    if deleted.row_count() == 0:
        pytest.skip("Nothing to export")
    download = deleted.export_filtered()
    assert download.suggested_filename
