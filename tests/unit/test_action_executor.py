"""Unit tests for execute_action.py."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "skills" / "action-executor" / "scripts"))

from execute_action import run_action, load_registry, check_hitl_gate, execute_function


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault structure."""
    for d in ("Needs_Action", "Pending_Approval", "Approved", "Done", "Plans", "Logs"):
        (tmp_path / d).mkdir()
    (tmp_path / "Dashboard.md").write_text("# Dashboard\n")
    return tmp_path


class TestDryRun:
    def test_dry_run_returns_success(self, temp_vault):
        result = run_action(action="email.draft_email", params={"to": "test@example.com"},
                            live=False, vault_path=str(temp_vault))
        assert result["success"] is True
        assert result["dry_run"] is True
        assert "request_id" in result

    def test_dry_run_no_side_effects(self, temp_vault):
        run_action(action="email.draft_email", params={},
                   live=False, vault_path=str(temp_vault))
        pending = list((temp_vault / "Pending_Approval").glob("*.md"))
        assert len(pending) == 0


class TestUnknownAction:
    def test_unknown_action_returns_error(self, temp_vault):
        result = run_action(action="fake.nonexistent", params={},
                            vault_path=str(temp_vault))
        assert result["success"] is False
        assert "not found" in result["detail"]
        assert "email.draft_email" in result["detail"]


class TestHITLGate:
    def test_hitl_required_creates_pending(self, temp_vault):
        result = run_action(action="email.send_email", params={"to": "test@example.com"},
                            live=True, vault_path=str(temp_vault))
        assert result["success"] is False
        assert result.get("hitl_blocked") is True
        assert "pending_file" in result
        pending = list((temp_vault / "Pending_Approval").glob("*.md"))
        assert len(pending) == 1

    def test_hitl_exempt_skips_gate(self, temp_vault):
        # Use documents.generate_report (hitl_required=false, no Google deps)
        result = run_action(action="documents.generate_report",
                            params={"title": "Test", "content": "Body"},
                            live=True, vault_path=str(temp_vault))
        # Should not be blocked by HITL gate
        assert result.get("hitl_blocked") is not True

    def test_approval_ref_passes_gate(self, temp_vault):
        # Create an approval file
        approval_file = temp_vault / "Approved" / "test-approval.md"
        approval_file.write_text("---\nstatus: approved\n---\nApproved.\n")

        # Use calendar.create_event (hitl_required=true, no Google deps)
        result = run_action(action="calendar.create_event",
                            params={"title": "Test"},
                            live=True, approval_ref="Approved/test-approval.md",
                            vault_path=str(temp_vault))
        # Should pass gate (function called, not blocked)
        assert result.get("hitl_blocked") is not True


class TestCheckHitlGate:
    def test_exempt_action(self, temp_vault):
        config = {"hitl_required": False}
        result = check_hitl_gate(config, temp_vault, None)
        assert result["passed"] is True
        assert result["check"] == "exempt"

    def test_required_no_approval(self, temp_vault):
        config = {"hitl_required": True}
        result = check_hitl_gate(config, temp_vault, None)
        assert result["passed"] is False

    def test_required_with_valid_approval(self, temp_vault):
        approval = temp_vault / "Approved" / "test.md"
        approval.write_text("approved")
        config = {"hitl_required": True}
        result = check_hitl_gate(config, temp_vault, "Approved/test.md")
        assert result["passed"] is True


class TestLoadRegistry:
    def test_loads_actions_json(self):
        registry = load_registry()
        assert "email.send_email" in registry
        assert "email.draft_email" in registry
        assert len(registry) == 6

    def test_hitl_required_field(self):
        registry = load_registry()
        assert registry["email.send_email"]["hitl_required"] is True
        assert registry["email.draft_email"]["hitl_required"] is False
