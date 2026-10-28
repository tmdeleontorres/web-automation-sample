"""Regenerate RFM_Test_Cases_HTML/data.js from the master CSV.

The 10-column RFM_Test_Cases.csv is the single source of truth for the HTML
test-case project; data.js is a plain mirror of it consumed by index.html
(a script tag works under file://, unlike fetch()).

Run:  python scripts/sync_html_data.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent   # .../RFM_Automation
CSV_PATH = ROOT / "RFM_Test_Cases.csv"
DATA_JS = ROOT / "RFM_Test_Cases_HTML" / "data.js"


def main() -> int:
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    payload = json.dumps(rows, ensure_ascii=True,
                         separators=(",", ":"))       # matches the existing data.js
    text = (f"// Auto-generated from RFM_Test_Cases.csv ({len(rows)} test cases)\n"
            f"window.DEFAULT_TEST_CASES = {payload};\n")
    DATA_JS.write_text(text, encoding="utf-8")
    print(f"[rfm] {len(rows)} test cases -> {DATA_JS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
