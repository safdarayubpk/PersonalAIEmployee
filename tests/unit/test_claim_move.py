"""Unit tests for src/claim_move.py — claim-by-move concurrency control."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from claim_move import claim_file, complete_file, scan_needs_action


@pytest.fixture
def vault_dir(tmp_path, monkeypatch):
    """Create a temporary vault structure for testing."""
    monkeypatch.setenv("FTE_ROLE", "cloud")
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    # Create vault folders
    (tmp_path / "Needs_Action" / "gmail").mkdir(parents=True)
    (tmp_path / "In_Progress" / "cloud").mkdir(parents=True)
    (tmp_path / "In_Progress" / "local").mkdir(parents=True)
    (tmp_path / "Pending_Approval" / "gmail").mkdir(parents=True)
    (tmp_path / "Done").mkdir()
    (tmp_path / "Logs").mkdir()
    return tmp_path


def _create_task_file(vault_dir: Path, domain: str, name: str,
                      created: str = "2026-03-11T10:00:00") -> Path:
    """Create a test task file with frontmatter."""
    folder = vault_dir / "Needs_Action" / domain
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(
        f"---\ntitle: {name.replace('.md', '')}\n"
        f"created: {created}\n"
        f"tier: platinum\nsource: test\n"
        f"priority: routine\nstatus: needs_action\n"
        f"agent: cloud\n"
        f'correlation_id: "corr-2026-03-11-aabbccdd"\n'
        f"---\n\n## Test task\n",
        encoding="utf-8",
    )
    return path


class TestClaimFile:
    """Tests for claim_file()."""

    def test_successful_claim(self, vault_dir):
        """File moves from Needs_Action to In_Progress."""
        task = _create_task_file(vault_dir, "gmail", "test-email.md")
        result = claim_file(task, "cloud", vault_dir)

        assert result is not None
        assert result.parent.name == "cloud"
        assert result.name == "test-email.md"
        assert not task.exists()  # Original removed
        assert result.exists()  # New location exists

    def test_already_claimed_returns_none(self, vault_dir):
        """Returns None when file is already gone (claimed by other agent)."""
        task = _create_task_file(vault_dir, "gmail", "test-email.md")
        # First claim succeeds
        claim_file(task, "cloud", vault_dir)
        # Second claim on same path returns None
        result = claim_file(task, "local", vault_dir)
        assert result is None

    def test_updates_status_frontmatter(self, vault_dir):
        """Claimed file has status=in_progress in frontmatter."""
        task = _create_task_file(vault_dir, "gmail", "test-email.md")
        result = claim_file(task, "cloud", vault_dir)

        content = result.read_text(encoding="utf-8")
        assert "status: in_progress" in content

    def test_updates_agent_frontmatter(self, vault_dir):
        """Claimed file has agent field matching the claiming role."""
        task = _create_task_file(vault_dir, "gmail", "test-email.md")
        result = claim_file(task, "local", vault_dir)

        content = result.read_text(encoding="utf-8")
        assert "agent: local" in content


class TestCompleteFile:
    """Tests for complete_file()."""

    def test_moves_to_done(self, vault_dir):
        """File moves from In_Progress to Done."""
        task = _create_task_file(vault_dir, "gmail", "test-email.md")
        claimed = claim_file(task, "cloud", vault_dir)

        result = complete_file(claimed, "Done", vault_dir, status="done")
        assert result.parent.name == "Done"
        assert result.exists()
        assert not claimed.exists()

    def test_moves_to_pending_approval(self, vault_dir):
        """File moves from In_Progress to Pending_Approval."""
        task = _create_task_file(vault_dir, "gmail", "test-email.md")
        claimed = claim_file(task, "cloud", vault_dir)

        result = complete_file(claimed, "Pending_Approval/gmail", vault_dir,
                               status="pending_approval")
        assert "Pending_Approval" in str(result.parent)
        assert result.exists()

    def test_updates_frontmatter_fields(self, vault_dir):
        """Frontmatter is updated with provided fields."""
        task = _create_task_file(vault_dir, "gmail", "test-email.md")
        claimed = claim_file(task, "cloud", vault_dir)

        result = complete_file(claimed, "Done", vault_dir, status="done")
        content = result.read_text(encoding="utf-8")
        assert "status: done" in content


class TestScanNeedsAction:
    """Tests for scan_needs_action()."""

    def test_returns_files_in_domain(self, vault_dir):
        """Returns all .md files in specified domain."""
        _create_task_file(vault_dir, "gmail", "email-1.md", "2026-03-11T10:00:00")
        _create_task_file(vault_dir, "gmail", "email-2.md", "2026-03-11T11:00:00")

        files = scan_needs_action(vault_dir, domain="gmail")
        assert len(files) == 2

    def test_sorted_by_created_timestamp(self, vault_dir):
        """Files are sorted by creation timestamp (oldest first)."""
        _create_task_file(vault_dir, "gmail", "newer.md", "2026-03-11T12:00:00")
        _create_task_file(vault_dir, "gmail", "older.md", "2026-03-11T08:00:00")

        files = scan_needs_action(vault_dir, domain="gmail")
        assert files[0].name == "older.md"
        assert files[1].name == "newer.md"

    def test_scans_all_domains_when_none(self, vault_dir):
        """Scans all domain subfolders when domain is None."""
        _create_task_file(vault_dir, "gmail", "email.md")
        _create_task_file(vault_dir, "scheduler", "task.md")

        # Create scheduler subfolder
        (vault_dir / "Needs_Action" / "scheduler").mkdir(parents=True, exist_ok=True)

        files = scan_needs_action(vault_dir, domain=None)
        names = {f.name for f in files}
        assert "email.md" in names
        assert "task.md" in names

    def test_empty_domain_returns_empty(self, vault_dir):
        """Empty domain folder returns empty list."""
        files = scan_needs_action(vault_dir, domain="gmail")
        assert files == []
