"""Tests for correlation ID generation and validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from correlation import (
    generate_correlation_id,
    is_valid_correlation_id,
    ensure_correlation_id,
    extract_correlation_id,
)


def test_generate_format():
    """Generated ID matches corr-YYYYMMDD-HHMMSS-XXXX format."""
    cid = generate_correlation_id()
    assert cid.startswith("corr-")
    assert len(cid) == 25  # corr-YYYYMMDD-HHMMSS-XXXX
    assert is_valid_correlation_id(cid)


def test_uniqueness():
    """Consecutive IDs are mostly unique (allowing for 4-hex-char collisions)."""
    ids = {generate_correlation_id() for _ in range(10)}
    assert len(ids) == 10


def test_valid_id():
    assert is_valid_correlation_id("corr-20260301-120000-ab3f")


def test_invalid_ids():
    assert not is_valid_correlation_id("")
    assert not is_valid_correlation_id("not-a-correlation-id")
    assert not is_valid_correlation_id("corr-2026-120000-ab3f")
    assert not is_valid_correlation_id("corr-20260301-120000-xyz!")


def test_extract_from_frontmatter():
    fm = {"title": "test", "correlation_id": "corr-20260301-120000-ab3f"}
    assert extract_correlation_id(fm) == "corr-20260301-120000-ab3f"


def test_extract_missing():
    assert extract_correlation_id({"title": "test"}) is None


def test_ensure_existing():
    fm = {"correlation_id": "corr-20260301-120000-ab3f"}
    cid, generated = ensure_correlation_id(fm)
    assert cid == "corr-20260301-120000-ab3f"
    assert not generated


def test_ensure_missing():
    fm = {"title": "test"}
    cid, generated = ensure_correlation_id(fm)
    assert is_valid_correlation_id(cid)
    assert generated
    assert fm["correlation_id"] == cid


if __name__ == "__main__":
    test_generate_format()
    test_uniqueness()
    test_valid_id()
    test_invalid_ids()
    test_extract_from_frontmatter()
    test_extract_missing()
    test_ensure_existing()
    test_ensure_missing()
    print("All correlation tests passed!")
