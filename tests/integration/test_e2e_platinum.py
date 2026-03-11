from __future__ import annotations

"""End-to-end integration tests for the Platinum tier lifecycle.

Tests the full flow: Needs_Action/gmail/ → claim → draft to Pending_Approval/gmail/
→ move to Approved/ → execute → verify Done/ with correlation_id trail.

These tests use temp directories and mocked actions — no real Gmail or MCP calls.
"""

import json
import os
import sys
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Add src/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


@pytest.fixture
def vault(tmp_path):
    """Create a complete Platinum vault structure for testing."""
    dirs = [
        "Needs_Action/gmail", "Needs_Action/scheduler", "Needs_Action/manual",
        "In_Progress/cloud", "In_Progress/local",
        "Pending_Approval/gmail", "Pending_Approval/social",
        "Approved", "Done", "Rejected",
        "Updates", "Plans", "Logs",
    ]
    for d in dirs:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _create_needs_action_file(vault, domain="gmail", sender="client@example.com",
                               subject="Invoice Payment Overdue",
                               corr_id="corr-2026-03-11-deadbeef"):
    """Helper to create a realistic Needs_Action file."""
    ts = datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
    ts_file = ts.strftime("%Y%m%d-%H%M%S")

    filename = f"email-client-{ts_file}.md"
    filepath = vault / "Needs_Action" / domain / filename

    content = f"""---
title: "email-client-invoice-payment-overdue"
created: "{ts_str}"
tier: platinum
source: gmail-watcher
agent: cloud
priority: "critical"
status: needs_action
gmail_id: "msg123abc"
correlation_id: "{corr_id}"
---

## What happened

New email from `{sender}`: {subject}

## Body Summary

Dear team, the invoice payment is overdue. Please process ASAP.

## Suggested action

Review and respond to this email.
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


def _create_pending_approval_file(vault, domain="gmail", tool="email.send",
                                   corr_id="corr-2026-03-11-deadbeef"):
    """Helper to create a Pending_Approval file."""
    ts = datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
    ts_file = ts.strftime("%Y%m%d-%H%M%S")

    filename = f"pending-email-send-{ts_file}.md"
    filepath = vault / "Pending_Approval" / domain / filename

    content = f"""---
title: "Pending Approval: {tool}"
created: "{ts_str}"
tier: platinum
type: pending-approval
tool: {tool}
status: pending_approval
correlation_id: "{corr_id}"
agent: cloud
---

## Action Requiring Approval

**Tool**: `{tool}`
**Time**: {ts_str}
**Correlation ID**: {corr_id}

## Parameters

```json
{{
  "to": "client@example.com",
  "subject": "Re: Invoice Payment Overdue",
  "body": "Thank you for your email. We will process the payment immediately."
}}
```

## Instructions

To approve this action:
1. Review the parameters above
2. Move this file to `Approved/`
3. Re-trigger the action with `--live` mode
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


class TestClaimByMoveIntegration:
    """Test claim-by-move with real vault structure."""

    def test_cloud_claims_needs_action_file(self, vault):
        """Cloud agent claims a Needs_Action/gmail/ file to In_Progress/cloud/."""
        from claim_move import claim_file

        na_file = _create_needs_action_file(vault)
        assert na_file.exists()

        result = claim_file(na_file, "cloud", vault)
        assert result is not None
        assert result.parent == vault / "In_Progress" / "cloud"
        assert not na_file.exists()

    def test_second_claim_fails(self, vault):
        """Second agent claiming same file gets None."""
        from claim_move import claim_file

        na_file = _create_needs_action_file(vault)
        result1 = claim_file(na_file, "cloud", vault)
        assert result1 is not None

        # Second claim on same path fails (file already moved)
        result2 = claim_file(na_file, "local", vault)
        assert result2 is None

    def test_complete_file_moves_to_done(self, vault):
        """After processing, file moves from In_Progress to Done."""
        from claim_move import claim_file, complete_file

        na_file = _create_needs_action_file(vault)
        in_progress = claim_file(na_file, "local", vault)

        done_file = complete_file(in_progress, "Done", vault, status="completed")
        assert done_file.parent == vault / "Done"
        assert done_file.exists()
        assert not in_progress.exists()


class TestRoleGateIntegration:
    """Test role-based action gating in realistic scenarios."""

    def test_cloud_role_creates_draft_via_role_gated_action(self, vault):
        """Cloud agent calling role_gated_action for sensitive action creates draft."""
        from mcp.base_server import role_gated_action

        with patch.dict(os.environ, {"FTE_ROLE": "cloud", "VAULT_PATH": str(vault)}):
            result = role_gated_action(
                "email.send", "sensitive",
                {"to": "test@test.com", "subject": "Test"},
                lambda p: {"status": "success"},
                correlation_id="corr-2026-03-11-aabbccdd",
                domain="gmail",
            )

        assert result["status"] == "draft_created"
        assert "pending_approval_path" in result

        # Verify file was created
        approval_path = Path(result["pending_approval_path"])
        assert approval_path.exists()
        content = approval_path.read_text()
        assert "email.send" in content
        assert "corr-2026-03-11-aabbccdd" in content

    def test_local_role_executes_normally(self, vault):
        """Local agent calling role_gated_action for sensitive action executes normally."""
        from mcp.base_server import role_gated_action

        executed = {"called": False}

        def mock_execute(params):
            executed["called"] = True
            return {"status": "success", "detail": "Email sent"}

        with patch.dict(os.environ, {"FTE_ROLE": "local", "VAULT_PATH": str(vault)}):
            result = role_gated_action(
                "email.send", "sensitive",
                {"to": "test@test.com"},
                mock_execute,
                correlation_id="corr-2026-03-11-11223344",
                domain="gmail",
            )

        assert executed["called"]
        assert result["status"] == "success"


class TestApprovalWatcherIntegration:
    """Test the full approval → execution → Done lifecycle."""

    def test_refuses_on_cloud(self, vault):
        """Approval watcher refuses to run on cloud agent."""
        from approval_watcher import process_approved

        with patch.dict(os.environ, {"FTE_ROLE": "cloud", "VAULT_PATH": str(vault)}):
            result = process_approved(vault)

        assert result["status"] == "refused"

    def test_processes_approved_file_dry_run(self, vault):
        """Dry-run mode lists approved files without executing."""
        from approval_watcher import process_approved

        # Create an approved file by moving from Pending_Approval to Approved
        pending = _create_pending_approval_file(vault)
        approved_path = vault / "Approved" / pending.name
        shutil.move(str(pending), str(approved_path))

        with patch.dict(os.environ, {"FTE_ROLE": "local", "VAULT_PATH": str(vault)}):
            result = process_approved(vault, dry_run=True)

        assert result["processed"] == 1
        assert result["results"][0]["status"] == "dry_run"
        assert result["results"][0]["tool"] == "email.send"

    def test_empty_approved_returns_zero(self, vault):
        """No approved files returns success with 0 processed."""
        from approval_watcher import process_approved

        with patch.dict(os.environ, {"FTE_ROLE": "local", "VAULT_PATH": str(vault)}):
            result = process_approved(vault)

        assert result["processed"] == 0


class TestCorrelationIdTracing:
    """Test that correlation ID propagates through the full lifecycle."""

    def test_correlation_id_preserved_through_claim(self, vault):
        """Correlation ID in frontmatter survives claim-by-move."""
        from claim_move import claim_file

        corr_id = "corr-2026-03-11-cafebabe"
        na_file = _create_needs_action_file(vault, corr_id=corr_id)

        result = claim_file(na_file, "cloud", vault)
        content = result.read_text()
        assert corr_id in content

    def test_correlation_id_in_pending_approval(self, vault):
        """Correlation ID appears in Pending_Approval file created by role gate."""
        from mcp.base_server import role_gated_action

        corr_id = "corr-2026-03-11-feedf00d"
        with patch.dict(os.environ, {"FTE_ROLE": "cloud", "VAULT_PATH": str(vault)}):
            result = role_gated_action(
                "email.send", "sensitive",
                {"to": "test@test.com"},
                lambda p: {"status": "success"},
                correlation_id=corr_id,
                domain="gmail",
            )

        approval_path = Path(result["pending_approval_path"])
        content = approval_path.read_text()
        assert corr_id in content


    def test_correlation_id_in_claim_log(self, vault):
        """Correlation ID appears in JSONL log entries when claiming files (T040)."""
        from claim_move import claim_file

        corr_id = "corr-2026-03-11-logcheck1"
        na_file = _create_needs_action_file(vault, corr_id=corr_id)

        claim_file(na_file, "cloud", vault)

        # Check actions.jsonl for correlation_id
        log_file = vault / "Logs" / "actions.jsonl"
        assert log_file.exists()
        log_content = log_file.read_text()
        assert corr_id in log_content

    def test_correlation_id_in_complete_log(self, vault):
        """Correlation ID appears in log entries when completing files (T040)."""
        from claim_move import claim_file, complete_file

        corr_id = "corr-2026-03-11-logcheck2"
        na_file = _create_needs_action_file(vault, corr_id=corr_id)

        claimed = claim_file(na_file, "local", vault)
        complete_file(claimed, "Done", vault, status="completed")

        log_file = vault / "Logs" / "actions.jsonl"
        log_lines = log_file.read_text().strip().split("\n")
        # Both claim and complete should have correlation_id
        corr_count = sum(1 for line in log_lines if corr_id in line)
        assert corr_count >= 2, f"Expected correlation_id in at least 2 log entries, found {corr_count}"


class TestFullLifecycle:
    """Test the complete end-to-end Platinum demo flow."""

    def test_email_triage_full_lifecycle(self, vault):
        """Full lifecycle: email detected → claimed → drafted → approved → executed → done."""
        from claim_move import claim_file, complete_file
        from mcp.base_server import role_gated_action

        corr_id = "corr-2026-03-11-e2e12345"

        # Step 1: Gmail watcher creates Needs_Action/gmail/ file (cloud)
        na_file = _create_needs_action_file(vault, corr_id=corr_id)
        assert na_file.exists()
        assert na_file.parent.name == "gmail"

        # Step 2: Cloud agent claims the file
        with patch.dict(os.environ, {"FTE_ROLE": "cloud"}):
            claimed = claim_file(na_file, "cloud", vault)
        assert claimed is not None
        assert claimed.parent == vault / "In_Progress" / "cloud"

        # Step 3: Cloud agent processes and creates draft via role_gated_action
        with patch.dict(os.environ, {"FTE_ROLE": "cloud", "VAULT_PATH": str(vault)}):
            draft_result = role_gated_action(
                "email.send", "sensitive",
                {"to": "client@example.com", "subject": "Re: Invoice",
                 "body": "Payment processed."},
                lambda p: {"status": "success"},
                correlation_id=corr_id,
                domain="gmail",
            )
        assert draft_result["status"] == "draft_created"
        approval_path = Path(draft_result["pending_approval_path"])
        assert approval_path.exists()

        # Step 4: Cloud moves claimed file to Pending_Approval
        complete_file(claimed, "Pending_Approval/gmail", vault, status="drafted")

        # Step 5: User reviews and moves to Approved/ (simulated)
        approved_dest = vault / "Approved" / approval_path.name
        shutil.move(str(approval_path), str(approved_dest))
        assert approved_dest.exists()

        # Step 6: Local agent picks up and executes (mocked)
        from approval_watcher import process_approved

        with patch.dict(os.environ, {"FTE_ROLE": "local", "VAULT_PATH": str(vault)}):
            with patch("approval_watcher.importlib") as mock_importlib:
                # Mock the action module
                mock_mod = MagicMock()
                mock_mod.send_email.return_value = {"status": "sent", "message_id": "msg456"}
                mock_importlib.import_module.return_value = mock_mod

                exec_result = process_approved(vault)

        # Step 7: Verify file is in Done/
        done_files = list((vault / "Done").glob("*.md"))
        assert len(done_files) >= 1

        # Step 8: Verify correlation ID is traceable
        if done_files:
            done_content = done_files[0].read_text()
            assert corr_id in done_content or "email.send" in done_content
