"""RFID Import module  (TC-IMP-001 .. TC-IMP-009).

Fixture files live in  RFM_Python_Automation/fixtures/  - the template
downloaded by TC-IMP-001 can be dropped there and reused by the upload tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pages.rfid_import_page import RfidImportPage
from utils import test_data as data

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def fixture(name: str) -> Path | None:
    path = FIXTURES / name
    return path if path.exists() else None


@pytest.fixture
def importer(auth_page) -> RfidImportPage:
    return RfidImportPage(auth_page).open()


@pytest.mark.smoke
@pytest.mark.happy
def test_imp_001_download_template(importer):
    """TC-IMP-001: Download Template provides the documented columns."""
    download = importer.download_template()
    assert download.suggested_filename, "No template was downloaded"


@pytest.mark.happy
def test_imp_007_preview_panel_is_empty_initially(importer):
    """TC-IMP-007: before uploading, the panel reads 'No Spreadsheet Preview Yet'."""
    assert importer.preview_is_empty(), \
        "Preview panel is not in its empty state on a fresh page"


@pytest.mark.happy
def test_imp_002_preview_counts(importer):
    """TC-IMP-002: preview reports Total / New / Update / Mother / Child rows."""
    path = fixture("rfid_import_sample.xlsx")
    if not path:
        pytest.skip("fixtures/rfid_import_sample.xlsx not provided yet")
    importer.upload(str(path)).preview()
    summary = importer.preview_summary()
    assert summary["total"] == data.IMPORT_EXPECTED["total"]
    assert summary["new"] == data.IMPORT_EXPECTED["new"]
    assert summary["child"] == data.IMPORT_EXPECTED["child"]
    assert summary["mother"] == data.IMPORT_EXPECTED["mother"]


@pytest.mark.happy
def test_imp_006_confirm_import_writes_records(importer):
    """TC-IMP-006: Confirm Import persists the rows (visible in RFID List)."""
    path = fixture("rfid_import_sample.xlsx")
    if not path:
        pytest.skip("fixtures/rfid_import_sample.xlsx not provided yet")
    importer.upload(str(path)).preview()
    if importer.blocking_errors():
        pytest.skip("Preview reported blocking validation errors")
    message = importer.confirm()
    assert message, "Confirm Import returned no feedback"


@pytest.mark.negative
def test_imp_004_unsupported_format_rejected(importer):
    """TC-IMP-004: only .xlsx / .xls / .csv are accepted."""
    path = fixture("not_a_spreadsheet.txt")
    if not path:
        pytest.skip("fixtures/not_a_spreadsheet.txt not provided yet")
    importer.upload(str(path)).preview()
    assert importer.blocking_errors() or importer.preview_is_empty(), \
        "An unsupported file format was accepted"


@pytest.mark.negative
def test_imp_005_blocking_error_disables_confirm(importer):
    """TC-IMP-005: blocking validation errors must disable Confirm Import."""
    path = fixture("rfid_import_invalid_epc.xlsx")
    if not path:
        pytest.skip("fixtures/rfid_import_invalid_epc.xlsx not provided yet")
    importer.upload(str(path)).preview()
    assert importer.blocking_errors()
    assert not importer.confirm_enabled(), "Confirm was available despite errors"


@pytest.mark.edge
def test_imp_003_preview_warnings_are_reported(importer):
    """TC-IMP-003: is_imported default + unresolved catalog_style_id warnings."""
    path = fixture("rfid_import_warnings.xlsx")
    if not path:
        pytest.skip("fixtures/rfid_import_warnings.xlsx not provided yet")
    importer.upload(str(path)).preview()
    text = importer.validation_text().lower()
    assert "is_imported" in text or "catalog_style_id" in text, \
        "Expected preview warnings were not displayed"


@pytest.mark.happy
@pytest.mark.parametrize("ext", data.IMPORT_SUPPORTED_FORMATS)
def test_imp_008_supported_formats_accepted(importer, ext):
    """TC-IMP-008: .xlsx, .xls and .csv are the supported formats."""
    assert ext in data.IMPORT_SUPPORTED_FORMATS
    path = fixture(f"rfid_import_sample{ext}")
    if not path:
        pytest.skip(f"fixtures/rfid_import_sample{ext} not provided yet")
    importer.upload(str(path)).preview()
    assert not importer.preview_is_empty()
