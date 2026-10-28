"""Shared test data for the RFM suite.

Values marked "documented" come straight from the RFM Documentation .docx and
are the exact figures the application is expected to produce.
"""

# --------------------------------------------------------------------------- #
# Item codes (GTIN / EN13)
# --------------------------------------------------------------------------- #
# *** Verified item code for generating RFIDs - used by every generation test ***
ITEM_CODE = "5057877230509"
ITEM_CODE_ADDED = ITEM_CODE            # primary code used across the suite

# TC-TBL-008 example: second code with a per-code bypass quantity (`code: 5`)
ITEM_CODE_BYPASS = "5057877257490"

# Documented example codes (RFM Documentation .docx) - used for multi-code tests
ITEM_CODE_DOCUMENTED = "5057877223730"  # documented as "Added"
ITEM_CODES_NEW = [                      # documented as "New"
    "5057877289941",
    "5057877098741",
    "5057877288975",
]
ITEM_CODES_MULTILINE = [ITEM_CODE] + ITEM_CODES_NEW      # 4 codes, one per line
INVALID_ITEM_CODES = ["12345", "ABCDEFG", "", "5057877230509X"]

# --------------------------------------------------------------------------- #
# Styles
# --------------------------------------------------------------------------- #
STYLE_EXISTING = "SBB1046G"              # Antibes / pink  (5 RFID rows documented)
STYLE_MOTHER = "SB13984"                 # Avaria / black  (1,050 children documented)

# --------------------------------------------------------------------------- #
# Quantities / serials (documented limits)
# --------------------------------------------------------------------------- #
QTY_DOCUMENTED = 16
QTY_MIN = 1
QTY_MAX = 5000
QTY_ABOVE_MAX = 5001
QTY_BELOW_MIN = 0

SERIAL_MIN = 0
SERIAL_NEGATIVE = -1
SERIAL_DECIMAL = 1.5

SERIAL_STEP_DEFAULT = 1
SERIAL_STEP_INVALID = 0

# Documented continuation example: decoded serials 9006 + 9020 -> next is 9021
CONTINUATION_EXISTING_DECODED = [9006, 9020]
CONTINUATION_EXPECTED_NEXT = 9021
CONTINUATION_IGNORED_RECORD_SERIAL = 9999        # wrong-format record, must be ignored

# Documented collision example: 27DA taken, 27DB free, 27DC/27DD conflict
COLLISION_TAKEN = "27DA"
COLLISION_FREE = "27DB"
COLLISION_CONFLICT = ["27DC", "27DD"]
COLLISION_EXPECTED_NEXT = "27DE"

# --------------------------------------------------------------------------- #
# EPC validation (SGTIN-96, 24 hex characters)
# --------------------------------------------------------------------------- #
EPC_LENGTH = 24
EPC_VALID = "303534334241423230323431"          # 24 hex chars, sample
EPC_TOO_SHORT = "30353433424142323032343"        # 23 chars
EPC_TOO_LONG = "3035343342414232303234311"       # 25 chars
EPC_NON_HEX = "ZZZZ34334241423230323431"         # 24 chars but not hexadecimal

# --------------------------------------------------------------------------- #
# Operator RFID format: 4F50455241544F524944 + operator id zero-padded to 4
# --------------------------------------------------------------------------- #
OPERATOR_RFID_PREFIX = "4F50455241544F524944"
OPERATOR_ID_EXAMPLE = 112
OPERATOR_RFID_EXAMPLE = "4F50455241544F5249440112"

# --------------------------------------------------------------------------- #
# WMS sync - documented batch behaviour
# --------------------------------------------------------------------------- #
WMS_BATCH_SIZE = 500
WMS_TOTAL_ROWS = 1201
WMS_EXPECTED_BATCHES = [500, 500, 201]

# --------------------------------------------------------------------------- #
# Import spreadsheet (documented preview of the 7-row sample file)
# --------------------------------------------------------------------------- #
IMPORT_EXPECTED = {"total": 7, "new": 7, "update": 0, "mother": 0, "child": 7}
IMPORT_SUPPORTED_FORMATS = (".xlsx", ".xls", ".csv")
