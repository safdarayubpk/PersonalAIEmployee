"""Unit tests for src/role_gate.py — FTE_ROLE validation and enforcement."""

import os
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from role_gate import (
    get_fte_role,
    is_cloud,
    is_local,
    enforce_role_gate,
    validate_startup,
    RoleViolationError,
)


class TestGetFteRole:
    """Tests for get_fte_role()."""

    def test_returns_cloud_when_set(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "cloud")
        assert get_fte_role() == "cloud"

    def test_returns_local_when_set(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "local")
        assert get_fte_role() == "local"

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "CLOUD")
        assert get_fte_role() == "cloud"

    def test_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "  local  ")
        assert get_fte_role() == "local"

    def test_missing_role_exits(self, monkeypatch):
        monkeypatch.delenv("FTE_ROLE", raising=False)
        with pytest.raises(SystemExit):
            get_fte_role()

    def test_invalid_role_exits(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "hybrid")
        with pytest.raises(SystemExit):
            get_fte_role()

    def test_empty_role_exits(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "")
        with pytest.raises(SystemExit):
            get_fte_role()


class TestIsCloudIsLocal:
    """Tests for is_cloud() and is_local()."""

    def test_is_cloud_true(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "cloud")
        assert is_cloud() is True
        assert is_local() is False

    def test_is_local_true(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "local")
        assert is_local() is True
        assert is_cloud() is False


class TestEnforceRoleGate:
    """Tests for enforce_role_gate()."""

    def test_cloud_blocks_sensitive(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "cloud")
        with pytest.raises(RoleViolationError, match="email_send"):
            enforce_role_gate("email_send", "sensitive")

    def test_cloud_blocks_critical(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "cloud")
        with pytest.raises(RoleViolationError, match="odoo_create_invoice"):
            enforce_role_gate("odoo_create_invoice", "critical")

    def test_cloud_allows_routine(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "cloud")
        # Should not raise
        enforce_role_gate("read_vault_file", "routine")

    def test_local_allows_sensitive(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "local")
        # Should not raise
        enforce_role_gate("email_send", "sensitive")

    def test_local_allows_critical(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "local")
        # Should not raise
        enforce_role_gate("odoo_register_payment", "critical")

    def test_local_allows_routine(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "local")
        # Should not raise
        enforce_role_gate("read_file", "routine")


class TestValidateStartup:
    """Tests for validate_startup()."""

    def test_returns_role_string(self, monkeypatch):
        monkeypatch.setenv("FTE_ROLE", "cloud")
        assert validate_startup() == "cloud"

    def test_exits_on_missing_role(self, monkeypatch):
        monkeypatch.delenv("FTE_ROLE", raising=False)
        with pytest.raises(SystemExit):
            validate_startup()
