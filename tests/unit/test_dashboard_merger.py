from __future__ import annotations

"""Unit tests for src/dashboard_merger.py — single-writer Dashboard.md updates."""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


@pytest.fixture
def vault(tmp_path):
    """Create a minimal vault with Updates/ and Dashboard.md."""
    (tmp_path / "Updates").mkdir()
    (tmp_path / "Dashboard.md").write_text("# Dashboard\n\n## Status\n\nAll good.\n")
    return tmp_path


class TestWriteUpdate:
    """Tests for write_update() — cloud-only incremental update creation."""

    def test_creates_update_file(self, vault):
        from dashboard_merger import write_update

        with patch.dict(os.environ, {"FTE_ROLE": "cloud"}):
            path = write_update("Email processed", vault, source="test")

        assert path.exists()
        assert path.parent == vault / "Updates"
        assert path.name.startswith("dashboard-update-")
        content = path.read_text()
        assert "Email processed" in content
        assert "source: test" in content

    def test_includes_correlation_id(self, vault):
        from dashboard_merger import write_update

        with patch.dict(os.environ, {"FTE_ROLE": "cloud"}):
            path = write_update("Task done", vault, correlation_id="corr-2026-03-11-abc12345")

        content = path.read_text()
        assert "corr-2026-03-11-abc12345" in content

    def test_blocks_local_role(self, vault):
        from dashboard_merger import write_update

        with patch.dict(os.environ, {"FTE_ROLE": "local"}):
            with pytest.raises(PermissionError, match="cloud-only"):
                write_update("Should fail", vault)

    def test_allows_missing_fte_role(self, vault):
        """When FTE_ROLE is not set (testing/Gold compat), allow write."""
        from dashboard_merger import write_update

        env = os.environ.copy()
        env.pop("FTE_ROLE", None)
        with patch.dict(os.environ, env, clear=True):
            path = write_update("Testing mode", vault)

        assert path.exists()

    def test_creates_updates_dir_if_missing(self, tmp_path):
        from dashboard_merger import write_update

        with patch.dict(os.environ, {"FTE_ROLE": "cloud"}):
            path = write_update("First update", tmp_path)

        assert (tmp_path / "Updates").is_dir()
        assert path.exists()


class TestMergeUpdates:
    """Tests for merge_updates() — local-only merge into Dashboard.md."""

    def test_single_update_merge(self, vault):
        from dashboard_merger import write_update, merge_updates

        # Create one update
        with patch.dict(os.environ, {"FTE_ROLE": "cloud"}):
            write_update("Cloud processed email-123", vault)

        # Merge as local
        with patch.dict(os.environ, {"FTE_ROLE": "local"}):
            count = merge_updates(vault)

        assert count == 1
        dashboard = (vault / "Dashboard.md").read_text()
        assert "Cloud processed email-123" in dashboard
        assert "## Cloud Updates" in dashboard

        # Update files should be deleted
        remaining = list((vault / "Updates").glob("dashboard-update-*.md"))
        assert len(remaining) == 0

    def test_multiple_chronological_merge(self, vault):
        from dashboard_merger import write_update, merge_updates

        with patch.dict(os.environ, {"FTE_ROLE": "cloud"}):
            write_update("First update", vault)
            write_update("Second update", vault)
            write_update("Third update", vault)

        with patch.dict(os.environ, {"FTE_ROLE": "local"}):
            count = merge_updates(vault)

        assert count == 3
        dashboard = (vault / "Dashboard.md").read_text()
        assert "First update" in dashboard
        assert "Second update" in dashboard
        assert "Third update" in dashboard

        # All processed files deleted
        remaining = list((vault / "Updates").glob("dashboard-update-*.md"))
        assert len(remaining) == 0

    def test_empty_updates_returns_zero(self, vault):
        from dashboard_merger import merge_updates

        with patch.dict(os.environ, {"FTE_ROLE": "local"}):
            count = merge_updates(vault)

        assert count == 0

    def test_no_updates_dir_returns_zero(self, tmp_path):
        from dashboard_merger import merge_updates

        with patch.dict(os.environ, {"FTE_ROLE": "local"}):
            count = merge_updates(tmp_path)

        assert count == 0

    def test_creates_dashboard_if_missing(self, tmp_path):
        from dashboard_merger import write_update, merge_updates

        (tmp_path / "Updates").mkdir()

        with patch.dict(os.environ, {"FTE_ROLE": "cloud"}):
            write_update("Bootstrap update", tmp_path)

        with patch.dict(os.environ, {"FTE_ROLE": "local"}):
            count = merge_updates(tmp_path)

        assert count == 1
        dashboard = tmp_path / "Dashboard.md"
        assert dashboard.exists()
        assert "# Dashboard" in dashboard.read_text()

    def test_blocks_cloud_role(self, vault):
        from dashboard_merger import merge_updates

        with patch.dict(os.environ, {"FTE_ROLE": "cloud"}):
            with pytest.raises(PermissionError, match="local-only"):
                merge_updates(vault)

    def test_preserves_existing_dashboard_content(self, vault):
        from dashboard_merger import write_update, merge_updates

        original = (vault / "Dashboard.md").read_text()

        with patch.dict(os.environ, {"FTE_ROLE": "cloud"}):
            write_update("New info", vault)

        with patch.dict(os.environ, {"FTE_ROLE": "local"}):
            merge_updates(vault)

        dashboard = (vault / "Dashboard.md").read_text()
        assert "All good." in dashboard  # Original content preserved
        assert "New info" in dashboard  # New content added
