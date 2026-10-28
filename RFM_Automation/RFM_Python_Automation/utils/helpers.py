"""Generic helpers shared by the tests (no Playwright dependency)."""

from __future__ import annotations

import csv
import random
import string
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER_CSV = ROOT.parent / "RFM_Test_Cases.csv"


def load_master_cases(path: Path | None = None) -> list[dict]:
    """Read the 134-case master CSV so tests can cross-check coverage."""
    target = Path(path) if path else MASTER_CSV
    if not target.exists():
        return []
    with target.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def random_suffix(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def epc_with_suffix(suffix: str, length: int = 24) -> str:
    """Build a 24-char hex EPC that ends with the given suffix."""
    head = "30" * max(length - len(suffix), 0)
    return (head + suffix).upper()[:length]


def pad_operator_id(operator_id: int) -> str:
    """4F50455241544F524944 + operator id zero-padded to 4 digits."""
    return f"4F50455241544F524944{operator_id:04d}"


def wms_batches(total: int, size: int = 500) -> list[int]:
    """Expected WMS batch split: e.g. 1201 -> [500, 500, 201]."""
    batches = []
    remaining = total
    while remaining > 0:
        batch = min(size, remaining)
        batches.append(batch)
        remaining -= batch
    return batches
