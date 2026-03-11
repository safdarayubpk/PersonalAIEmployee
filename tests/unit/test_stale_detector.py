from __future__ import annotations

"""Unit tests for src/stale_detector.py — stale file detection and dashboard updates."""

import os
import sys
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


@pytest.fixture
def vault(tmp_path):
    """Create a vault with Pending_Approval/ and Rejected/ directories."""
    for d in ["Pending_Approval/gmail", "Pending_Approval/social", "Rejected", "Logs"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / "Dashboard.md").write_text("# Dashboard\n\n## Status\n\nAll good.\n")
    return tmp_path


def _create_file(vault, folder, name, hours_ago):
    """Create a markdown file with frontmatter 'created' set to hours_ago."""
    ts = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%S")
    content = f"""---
title: "{name}"
created: "{ts}"
status: pending_approval
correlation_id: "corr-test-{name}"
---

## Test file

Content for {name}.
"""
    filepath = vault / folder / f"{name}.md"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    return filepath


class TestDetectStaleFiles:
    """Tests for detect_stale_files()."""

    def test_fresh_files_not_flagged(self, vault):
        from stale_detector import detect_stale_files

        _create_file(vault, "Pending_Approval/gmail", "fresh-email", 1)
        _create_file(vault, "Rejected", "fresh-rejected", 24)

        result = detect_stale_files(vault)
        assert result["total_stale"] == 0
        assert len(result["stale_pending"]) == 0
        assert len(result["stale_rejected"]) == 0

    def test_49h_pending_flagged(self, vault):
        from stale_detector import detect_stale_files

        _create_file(vault, "Pending_Approval/gmail", "old-email", 49)

        result = detect_stale_files(vault)
        assert result["total_stale"] == 1
        assert len(result["stale_pending"]) == 1
        assert result["stale_pending"][0]["age_hours"] > 48

    def test_8d_rejected_flagged(self, vault):
        from stale_detector import detect_stale_files

        _create_file(vault, "Rejected", "old-rejected", 8 * 24)

        result = detect_stale_files(vault)
        assert result["total_stale"] == 1
        assert len(result["stale_rejected"]) == 1
        assert result["stale_rejected"][0]["age_hours"] > 7 * 24

    def test_47h_pending_not_flagged(self, vault):
        from stale_detector import detect_stale_files

        _create_file(vault, "Pending_Approval/gmail", "not-yet-stale", 47)

        result = detect_stale_files(vault)
        assert result["total_stale"] == 0

    def test_6d_rejected_not_flagged(self, vault):
        from stale_detector import detect_stale_files

        _create_file(vault, "Rejected", "not-yet-stale", 6 * 24)

        result = detect_stale_files(vault)
        assert result["total_stale"] == 0

    def test_empty_dirs_return_zero(self, vault):
        from stale_detector import detect_stale_files

        result = detect_stale_files(vault)
        assert result["total_stale"] == 0

    def test_scans_pending_subfolders(self, vault):
        from stale_detector import detect_stale_files

        _create_file(vault, "Pending_Approval/gmail", "stale-gmail", 72)
        _create_file(vault, "Pending_Approval/social", "stale-social", 60)

        result = detect_stale_files(vault)
        assert result["total_stale"] == 2
        assert len(result["stale_pending"]) == 2


class TestUpdateDashboardStale:
    """Tests for update_dashboard_stale()."""

    def test_stale_section_added_to_dashboard(self, vault):
        from stale_detector import detect_stale_files, update_dashboard_stale

        _create_file(vault, "Pending_Approval/gmail", "stale-item", 72)
        stale_info = detect_stale_files(vault)
        update_dashboard_stale(vault, stale_info)

        dashboard = (vault / "Dashboard.md").read_text()
        assert "## Stale Items" in dashboard
        assert "stale-item" in dashboard
        assert ">48h" in dashboard or "Stale Pending" in dashboard

    def test_no_stale_shows_clean(self, vault):
        from stale_detector import detect_stale_files, update_dashboard_stale

        stale_info = detect_stale_files(vault)
        update_dashboard_stale(vault, stale_info)

        dashboard = (vault / "Dashboard.md").read_text()
        assert "No stale items detected" in dashboard

    def test_preserves_existing_dashboard(self, vault):
        from stale_detector import detect_stale_files, update_dashboard_stale

        stale_info = detect_stale_files(vault)
        update_dashboard_stale(vault, stale_info)

        dashboard = (vault / "Dashboard.md").read_text()
        assert "All good." in dashboard  # Original content preserved
