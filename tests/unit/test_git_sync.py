"""Unit tests for src/git_sync.py — git sync cycle and secrets audit."""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from git_sync import sync_cycle, SyncResult, audit_secrets_on_cloud, _run_git


@pytest.fixture
def vault_dir(tmp_path, monkeypatch):
    """Create a temporary vault structure for testing."""
    monkeypatch.setenv("FTE_ROLE", "cloud")
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    # Create minimal vault structure
    (tmp_path / "Logs").mkdir()
    (tmp_path / "Needs_Action" / "manual").mkdir(parents=True)
    (tmp_path / ".git").mkdir()  # Fake git dir
    return tmp_path


class TestSyncCycle:
    """Tests for sync_cycle()."""

    @patch("git_sync._run_git")
    def test_normal_cycle_no_changes(self, mock_git, vault_dir):
        """Pull succeeds, no changes to commit."""
        mock_git.side_effect = [
            MagicMock(returncode=0, stdout="No local changes to save", stderr=""),  # stash
            MagicMock(returncode=0, stdout="", stderr=""),  # pull
            MagicMock(returncode=0, stdout="", stderr=""),  # add
            MagicMock(returncode=0, stdout="", stderr=""),  # status --porcelain (empty)
        ]
        result = sync_cycle(vault_dir)
        assert result.pulled is True
        assert result.pushed is False
        assert result.files_changed == 0

    @patch("git_sync._run_git")
    def test_normal_cycle_with_push(self, mock_git, vault_dir):
        """Pull succeeds, changes committed and pushed."""
        mock_git.side_effect = [
            MagicMock(returncode=0, stdout="No local changes to save", stderr=""),  # stash
            MagicMock(returncode=0, stdout="", stderr=""),  # pull
            MagicMock(returncode=0, stdout="", stderr=""),  # add
            MagicMock(returncode=0, stdout="M file1.md\nA file2.md", stderr=""),  # status
            MagicMock(returncode=0, stdout="", stderr=""),  # commit
            MagicMock(returncode=0, stdout="", stderr=""),  # push
        ]
        result = sync_cycle(vault_dir)
        assert result.pulled is True
        assert result.pushed is True
        assert result.files_changed == 2
        assert result.success is True

    @patch("git_sync._run_git")
    def test_push_failure_with_retry(self, mock_git, vault_dir):
        """Push fails, retries with pull --rebase, then succeeds."""
        mock_git.side_effect = [
            MagicMock(returncode=0, stdout="No local changes to save", stderr=""),  # stash
            MagicMock(returncode=0, stdout="", stderr=""),  # pull
            MagicMock(returncode=0, stdout="", stderr=""),  # add
            MagicMock(returncode=0, stdout="M file1.md", stderr=""),  # status
            MagicMock(returncode=0, stdout="", stderr=""),  # commit
            MagicMock(returncode=1, stdout="", stderr="rejected"),  # push fail
            MagicMock(returncode=0, stdout="", stderr=""),  # retry pull
            MagicMock(returncode=0, stdout="", stderr=""),  # retry push success
        ]
        result = sync_cycle(vault_dir)
        assert result.pushed is True
        assert result.success is True

    @patch("git_sync._run_git")
    def test_network_offline(self, mock_git, vault_dir):
        """Pull fails due to network — returns error without conflict."""
        mock_git.side_effect = [
            MagicMock(returncode=0, stdout="No local changes to save", stderr=""),  # stash
            MagicMock(returncode=1, stdout="", stderr="Could not resolve host"),  # pull fails
        ]
        result = sync_cycle(vault_dir)
        assert result.error == "network_offline"
        assert result.conflict is False

    @patch("git_sync._run_git")
    def test_rebase_conflict_creates_alert(self, mock_git, vault_dir):
        """Rebase conflict creates Needs_Action/manual/ file."""
        mock_git.side_effect = [
            MagicMock(returncode=0, stdout="No local changes to save", stderr=""),  # stash
            MagicMock(returncode=1, stdout="", stderr="CONFLICT (content): Merge conflict in file.md"),  # pull
            MagicMock(returncode=0, stdout="", stderr=""),  # rebase --abort
        ]
        result = sync_cycle(vault_dir)
        assert result.conflict is True
        # Check alert was created
        alerts = list((vault_dir / "Needs_Action" / "manual").glob("*.md"))
        assert len(alerts) >= 1


class TestAuditSecretsOnCloud:
    """Tests for audit_secrets_on_cloud() — FR-016."""

    def test_no_violations_on_clean_vault(self, vault_dir):
        """Clean vault returns empty list."""
        violations = audit_secrets_on_cloud(vault_dir)
        assert violations == []

    def test_detects_env_file(self, vault_dir):
        """Detects .env file on cloud VM."""
        (vault_dir / ".env").write_text("SECRET=value")
        violations = audit_secrets_on_cloud(vault_dir)
        assert any(".env" in v for v in violations)

    def test_detects_session_file(self, vault_dir):
        """Detects .session file on cloud VM."""
        (vault_dir / "whatsapp.session").write_text("data")
        violations = audit_secrets_on_cloud(vault_dir)
        assert any(".session" in v for v in violations)

    def test_detects_credentials_dir(self, vault_dir):
        """Detects credentials/ directory on cloud VM."""
        (vault_dir / "credentials").mkdir()
        violations = audit_secrets_on_cloud(vault_dir)
        assert any("credentials" in v for v in violations)

    def test_skips_on_local_role(self, vault_dir, monkeypatch):
        """Does not run when FTE_ROLE=local."""
        monkeypatch.setenv("FTE_ROLE", "local")
        (vault_dir / ".env").write_text("SECRET=value")
        violations = audit_secrets_on_cloud(vault_dir)
        assert violations == []

    def test_creates_alert_on_violation(self, vault_dir):
        """Creates Needs_Action/manual/ alert when secrets found."""
        (vault_dir / ".env").write_text("SECRET=value")
        audit_secrets_on_cloud(vault_dir)
        alerts = list((vault_dir / "Needs_Action" / "manual").glob("*.md"))
        assert len(alerts) >= 1
