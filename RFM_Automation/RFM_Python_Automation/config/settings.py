"""Central configuration for the RFM (RFID Master Generator) automation suite.

Every value can be overridden with an environment variable so the same code
runs locally, in CI, or against another environment (dev/stage/prod).
"""

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Environment
# --------------------------------------------------------------------------- #
BASE_URL = os.getenv("RFM_BASE_URL", "https://dev.master.bwrfm.com")
LOGIN_PATH = "/en/login"

# Real module URLs (verified against the live sidebar - every module lives on
# the rfid_generator controller except Import, which has its own controller).
GENERATOR_PATH = "/en/rfid_generator/?act=view"
MODULE_PATHS = {
    "generator": "/en/rfid_generator/?act=view",
    "recent_generated": "/en/rfid_generator/?act=export&mode=recent",
    "rfid_list": "/en/rfid_generator/?act=export",
    "style_number_list": "/en/rfid_generator/?act=export&mode=style_number",
    "mother_list": "/en/rfid_generator/?act=export&mode=mother",
    "transaction_list": "/en/rfid_generator/?act=transactions",
    "all_users": "/en/rfid_generator/?act=users",
    "operator_list": "/en/rfid_generator/?act=operators",
    "warehouses": "/en/rfid_generator/?act=warehouses",
    "deleted_list": "/en/rfid_generator/?act=export&mode=deleted",
    "rewrite_rfids": "/en/rfid_generator/?act=export&mode=rewrite",
    "import": "/en/rfid_import/",
    "item_code_mismatch": "/en/rfid_generator/?act=item_code_mismatch",
    "generation_history": "/en/rfid_generator/?act=generation_history",
    "logout": "/en/login/?act=logout",
}

# Credentials (override in CI - never hardcode secrets in a public repo)
LOGIN_EMAIL = os.getenv("RFM_EMAIL", "")
LOGIN_PASSWORD = os.getenv("RFM_PASSWORD", "")

# --------------------------------------------------------------------------- #
# Browser / timeouts
# --------------------------------------------------------------------------- #
BROWSER = os.getenv("RFM_BROWSER", "chromium")          # chromium | firefox | webkit
HEADLESS = os.getenv("RFM_HEADLESS", "true").lower() in ("1", "true", "yes")
SLOWMO_MS = int(os.getenv("RFM_SLOWMO_MS", "0"))
TIMEOUT_MS = int(os.getenv("RFM_TIMEOUT_MS", "15000"))
NAVIGATION_TIMEOUT_MS = int(os.getenv("RFM_NAV_TIMEOUT_MS", "30000"))
VIEWPORT = {"width": 1600, "height": 1000}
LOCALE = "en-PH"
TIMEZONE = "Asia/Manila"          # app displays Philippine time

# --------------------------------------------------------------------------- #
# Output folders (created on demand)
# --------------------------------------------------------------------------- #
ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
REPORTS_DIR = ARTIFACTS_DIR / "reports"

for _dir in (SCREENSHOTS_DIR, REPORTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# HTML test-case project (RFM_Test_Cases_HTML) - automation writes here so the
# Status column in the HTML sheet updates while the suite runs.
# --------------------------------------------------------------------------- #
HTML_PROJECT_DIR = Path(os.getenv("RFM_HTML_PROJECT", ROOT_DIR.parent / "RFM_Test_Cases_HTML"))
HTML_RESULTS_JSON = HTML_PROJECT_DIR / "test_results.json"   # machine readable
HTML_RESULTS_JS = HTML_PROJECT_DIR / "results.js"            # loaded by index.html
WRITE_HTML_RESULTS = os.getenv("RFM_WRITE_HTML_RESULTS", "true").lower() in ("1", "true", "yes")

# --------------------------------------------------------------------------- #
# Sidebar labels (as rendered in the app's left navigation)
# --------------------------------------------------------------------------- #
NAV = {
    "generator": "Generator",
    "recent_generated": "Recent Generated",
    "rfid_list": "RFID List",
    "style_number_list": "Style Number List",
    "mother_list": "Mother List",
    "transaction_list": "Transaction List",
    "all_users": "All Users",
    "operator_list": "Operator List",
    "deleted_list": "Deleted List",
    "rewrite_rfids": "Rewrite RFIDs",
    "item_code_mismatch": "Item Code Mismatch",
    "import": "Import",
}

# Documented limits used by boundary tests
QTY_MIN = 1
QTY_MAX = 5000
SERIAL_MIN = 0
WMS_BATCH_SIZE = 500
OPERATOR_RFID_PREFIX = "4F50455241544F524944"

