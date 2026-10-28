"""Read the HTML project's localStorage (key rfm_test_cases_v1) straight from
Chrome/Edge leveldb stores and diff it against data.js.

Pure-Python LevelDB table reader (footer -> index -> data blocks) with a
minimal Snappy block decompressor - no native dependencies.

Run:  python scripts/read_html_storage.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

KEY = b"rfm_test_cases_v1"
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_JS = ROOT / "RFM_Test_Cases_HTML" / "data.js"
MAGIC = 0xdb4775248b80fb57

PROFILES = []
local = os.environ.get("LOCALAPPDATA", "")
appdata = os.environ.get("APPDATA", "")
for base, names in [
    (Path(local) / "Google/Chrome/User Data", ["Default", "Profile 1", "Profile 2"]),
    (Path(local) / "Microsoft/Edge/User Data", ["Default", "Profile 1"]),
    (Path(local) / "BraveSoftware/Brave-Browser/User Data", ["Default"]),
]:
    for name in names:
        PROFILES.append(base / name / "Local Storage" / "leveldb")


# --------------------------------------------------------------------------- #
# Snappy block format
# --------------------------------------------------------------------------- #
def _varint(buf: bytes, i: int) -> tuple[int, int]:
    val = shift = 0
    while True:
        b = buf[i]
        i += 1
        val |= (b & 0x7F) << shift
        if not b & 0x80:
            return val, i
        shift += 7


def snappy_decompress(data: bytes) -> bytes:
    out = bytearray()
    _, i = _varint(data, 0)                     # uncompressed length
    end = len(data)
    while i < end:
        tag = data[i]
        i += 1
        kind = tag & 0x03
        if kind == 0:                           # literal
            length = (tag >> 2) + 1
            if length > 60:
                extra = length - 60
                length = int.from_bytes(data[i:i + extra], "little") + 1
                i += extra
            out += data[i:i + length]
            i += length
        else:                                   # copy
            if kind == 1:
                length = 4 + ((tag >> 2) & 0x07)
                offset = ((tag >> 5) << 8) | data[i]
                i += 1
            elif kind == 2:
                length = (tag >> 2) + 1
                offset = int.from_bytes(data[i:i + 2], "little")
                i += 2
            else:
                length = (tag >> 2) + 1
                offset = int.from_bytes(data[i:i + 4], "little")
                i += 4
            if offset == 0 or offset > len(out):
                raise ValueError("bad snappy copy offset")
            for _ in range(length):
                out.append(out[-offset])
    return bytes(out)


# --------------------------------------------------------------------------- #
# LevelDB table (simplified reader)
# --------------------------------------------------------------------------- #
def _read_block(blob: bytes, offset: int, size: int) -> bytes:
    # a block handle's size includes the 5-byte crc/type trailer
    raw = blob[offset:offset + size]
    body = raw[:-5] if len(raw) > 5 else raw
    try:
        return snappy_decompress(body)
    except Exception:
        return body


def _parse_entries(block: bytes) -> list[tuple[bytes, bytes]]:
    entries = []
    key = b""
    i, end = 0, len(block)
    while i < end:
        try:
            shared, i = _varint(block, i)
            non_shared, i = _varint(block, i)
            vlen, i = _varint(block, i)
        except (IndexError, ValueError):
            break
        if non_shared < 0 or vlen < 0 or i + non_shared + vlen > end:
            break
        key = key[:shared] + block[i:i + non_shared]
        i += non_shared
        value = block[i:i + vlen]
        i += vlen
        entries.append((key, value))
    return entries


def _handle(raw: bytes, start: int = 0) -> tuple[int, int, int]:
    offset, i = _varint(raw, start)
    size, j = _varint(raw, i)
    return offset, size, j


def table_values(blob: bytes) -> list[bytes]:
    """All values stored in a LevelDB .ldb table."""
    if len(blob) < 48:
        return []
    footer = blob[-48:]
    if int.from_bytes(footer[40:48], "little") != MAGIC:
        return []
    # footer = metaindex handle, index handle, padding, magic
    _m_off, _m_size, pos = _handle(footer, 0)
    idx_off, idx_size, _ = _handle(footer, pos)
    index = _read_block(blob, idx_off, idx_size)
    values = []
    for _key, handle in _parse_entries(index):
        try:
            off, size, _ = _handle(handle)
            block = _read_block(blob, off, size)
        except Exception:
            continue
        values.extend(v for _k, v in _parse_entries(block))
    return values


def log_values(blob: bytes) -> list[bytes]:
    """All FULL-record values in a LevelDB .log file."""
    values = []
    i, end = 0, len(blob)
    while i + 7 <= end:
        crc = blob[i:i + 4]
        rtype = blob[i + 4]
        length = int.from_bytes(blob[i + 5:i + 7], "little")
        i += 7
        if length > end - i:
            break
        payload = blob[i:i + length]
        i += length
        if rtype == 1:                          # FULL record
            values.append(payload)
    return values


# --------------------------------------------------------------------------- #
# Diff against data.js
# --------------------------------------------------------------------------- #
def load_defaults() -> list[dict]:
    text = DATA_JS.read_text(encoding="utf-8")
    payload = text[text.index("["):]
    return json.loads(payload[: payload.rindex("]") + 1])


def decode_value(v: bytes) -> list[dict] | None:
    """localStorage value = 1 type byte + UTF-8 string (or raw UTF-8)."""
    for cand in (v[1:] if v[:1] in (b"\x00", b"\x01") else v, v):
        try:
            parsed = json.loads(cand.decode("utf-8"))
        except Exception:
            continue
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict) \
                and "TC ID" in parsed[0]:
            return parsed
    return None


def main() -> int:
    best: tuple[str, list[dict]] | None = None
    for prof in PROFILES:
        if not prof.is_dir():
            continue
        for f in sorted(prof.glob("*")):
            if f.suffix.lower() not in (".ldb", ".log"):
                continue
            try:
                blob = f.read_bytes()
            except OSError:
                continue
            if KEY not in blob:
                continue
            vals = table_values(blob) if f.suffix.lower() == ".ldb" else log_values(blob)
            for v in vals:
                cases = decode_value(v)
                if cases and (best is None or len(cases) > len(best[1])):
                    best = (str(f), cases)

    if best is None:
        print("[rfm] localStorage entry not found")
        return 1

    path, cases = best
    print(f"[rfm] localStorage copy: {len(cases)} cases  (from {path})")

    defaults = load_defaults()
    by_id = {c["TC ID"]: c for c in defaults}
    new_cases, changed = [], []
    for c in cases:
        old = by_id.get(c.get("TC ID"))
        if old is None:
            new_cases.append(c)
        elif any(str(c.get(k, "")) != str(old.get(k, "")) for k in c):
            changed.append((old, c))

    print(f"[rfm] defaults in data.js: {len(defaults)} cases")
    print(f"[rfm] NEW cases: {len(new_cases)}   CHANGED cases: {len(changed)}")
    for c in new_cases:
        print("\n===== NEW =====")
        for k, v in c.items():
            print(f"  {k}: {v}")
    for old, new in changed:
        print(f"\n===== CHANGED {new.get('TC ID')} =====")
        for k in new:
            if str(new.get(k, "")) != str(old.get(k, "")):
                print(f"  {k}:")
                print(f"    was: {old.get(k, '')}")
                print(f"    now: {new.get(k, '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
