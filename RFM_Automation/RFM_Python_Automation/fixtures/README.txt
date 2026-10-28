# Drop spreadsheet fixtures here for the RFID Import tests (TC-IMP-*).

Expected files (created from the app's own "Download Template"):

    rfid_import_sample.xlsx          valid 7-row sample -> TC-IMP-002 / 006
    rfid_import_sample.xls           same data, .xls     -> TC-IMP-008
    rfid_import_sample.csv           same data, .csv     -> TC-IMP-008
    rfid_import_invalid_epc.xlsx     malformed epc_hex   -> TC-IMP-005
    rfid_import_warnings.xlsx        empty is_imported / unknown model -> TC-IMP-003
    not_a_spreadsheet.txt            unsupported format  -> TC-IMP-004

Tests that need a missing fixture skip themselves automatically, so the suite
still runs green without them.
