"""Unit tests for ralph_retry.py."""

import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "skills" / "ralph-retry" / "scripts"))

from ralph_retry import ralph_loop, NonRetryableError, MAX_RETRIES_HARD_CAP


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault structure."""
    (tmp_path / "Logs").mkdir()
    (tmp_path / "Dashboard.md").write_text("# Dashboard\n")
    return tmp_path


class TestExponentialBackoff:
    def test_backoff_timing(self, temp_vault):
        attempts = []

        def flaky():
            attempts.append(time.monotonic())
            if len(attempts) < 3:
                raise RuntimeError("not yet")
            return "ok"

        result = ralph_loop(task=flaky, task_description="Backoff test",
                            max_retries=5, backoff_base=1,
                            vault_path=str(temp_vault))
        assert result["success"] is True
        assert result["attempts"] == 3

    def test_base_configurable(self, temp_vault):
        call_count = [0]

        def fail_once():
            call_count[0] += 1
            if call_count[0] < 2:
                raise RuntimeError("fail")
            return "done"

        start = time.monotonic()
        result = ralph_loop(task=fail_once, task_description="Base test",
                            max_retries=3, backoff_base=1,
                            vault_path=str(temp_vault))
        elapsed = time.monotonic() - start
        assert result["success"] is True
        assert elapsed >= 0.9  # base=1, first backoff ~1s


class TestHardCap:
    def test_clamp_to_20(self, temp_vault):
        call_count = [0]

        def always_fail():
            call_count[0] += 1
            raise RuntimeError("fail")

        result = ralph_loop(task=always_fail, task_description="Cap test",
                            max_retries=25, backoff_base=1,
                            vault_path=str(temp_vault))
        assert result["success"] is False
        assert result["attempts"] == MAX_RETRIES_HARD_CAP  # 20, not 25


class TestNonRetryable:
    def test_non_retryable_aborts(self, temp_vault):
        call_count = [0]

        def non_retryable():
            call_count[0] += 1
            raise NonRetryableError("abort now")

        result = ralph_loop(task=non_retryable, task_description="Abort test",
                            max_retries=5, backoff_base=1,
                            vault_path=str(temp_vault))
        assert result["success"] is False
        assert result["attempts"] == 1  # Only one attempt before abort
        assert result.get("aborted") is True


class TestSuccessOnNthAttempt:
    def test_success_on_third(self, temp_vault):
        call_count = [0]

        def succeed_on_3():
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError(f"fail {call_count[0]}")
            return {"status": "ok"}

        result = ralph_loop(task=succeed_on_3, task_description="N-attempt test",
                            max_retries=5, backoff_base=1,
                            vault_path=str(temp_vault))
        assert result["success"] is True
        assert result["attempts"] == 3
        assert result["result"] == {"status": "ok"}

    def test_logs_all_attempts(self, temp_vault):
        call_count = [0]

        def succeed_on_2():
            call_count[0] += 1
            if call_count[0] < 2:
                raise RuntimeError("fail")
            return "ok"

        ralph_loop(task=succeed_on_2, task_description="Log test",
                   max_retries=3, backoff_base=1,
                   vault_path=str(temp_vault))

        log_file = temp_vault / "Logs" / "retry.jsonl"
        assert log_file.exists()
        lines = log_file.read_text().strip().split("\n")
        # start + failure + success = 3 log entries minimum
        assert len(lines) >= 3


class TestExhaustedRetries:
    def test_returns_failure(self, temp_vault):
        def always_fail():
            raise RuntimeError("persistent error")

        result = ralph_loop(task=always_fail, task_description="Exhaust test",
                            max_retries=3, backoff_base=1,
                            vault_path=str(temp_vault))
        assert result["success"] is False
        assert result["attempts"] == 3
        assert result["error"] == "persistent error"
