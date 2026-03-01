"""Tests for circuit breaker state machine."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from circuit_breaker import CircuitBreaker, load_all_health


def _make_cb(tmp_dir, service="test-service", threshold=3, cooldown=300):
    health_file = Path(tmp_dir) / "health.json"
    return CircuitBreaker(service, health_file, threshold, cooldown)


def test_initial_state():
    with tempfile.TemporaryDirectory() as tmp:
        cb = _make_cb(tmp)
        assert cb.state == "healthy"
        assert cb.is_available


def test_stays_healthy_under_threshold():
    with tempfile.TemporaryDirectory() as tmp:
        cb = _make_cb(tmp, threshold=3)
        cb.record_failure("err1")
        assert cb.state == "healthy"
        cb.record_failure("err2")
        assert cb.state == "healthy"
        assert cb.is_available


def test_opens_at_threshold():
    with tempfile.TemporaryDirectory() as tmp:
        cb = _make_cb(tmp, threshold=3)
        cb.record_failure("err1")
        cb.record_failure("err2")
        result = cb.record_failure("err3")
        assert result == "degraded"
        assert cb.state == "degraded"
        assert not cb.is_available


def test_success_resets():
    with tempfile.TemporaryDirectory() as tmp:
        cb = _make_cb(tmp, threshold=3)
        cb.record_failure("err1")
        cb.record_failure("err2")
        cb.record_success()
        assert cb.state == "healthy"
        assert cb.is_available


def test_non_retryable_immediately_opens():
    with tempfile.TemporaryDirectory() as tmp:
        cb = _make_cb(tmp, threshold=3)
        result = cb.record_failure("401 Unauthorized", non_retryable=True)
        assert result == "down"
        assert not cb.is_available


def test_health_file_persistence():
    with tempfile.TemporaryDirectory() as tmp:
        health_file = Path(tmp) / "health.json"
        cb1 = CircuitBreaker("svc-a", health_file, 3, 300)
        cb1.record_success()

        cb2 = CircuitBreaker("svc-b", health_file, 3, 300)
        cb2.record_failure("err")

        data = load_all_health(health_file)
        assert len(data["services"]) == 2
        names = {s["service"] for s in data["services"]}
        assert names == {"svc-a", "svc-b"}


def test_cooldown_expiry():
    with tempfile.TemporaryDirectory() as tmp:
        cb = _make_cb(tmp, threshold=1, cooldown=60)
        cb.record_failure("err")
        assert cb.state == "degraded"
        # Manually expire the cooldown
        cb._state["cooldown_expires_at"] = "2020-01-01T00:00:00"
        cb._save_state()
        assert cb.is_available  # Should transition back to healthy


def test_status_dict():
    with tempfile.TemporaryDirectory() as tmp:
        cb = _make_cb(tmp)
        status = cb.status_dict
        assert status["service"] == "test-service"
        assert status["state"] == "healthy"
        assert status["consecutive_failures"] == 0


if __name__ == "__main__":
    test_initial_state()
    test_stays_healthy_under_threshold()
    test_opens_at_threshold()
    test_success_resets()
    test_non_retryable_immediately_opens()
    test_health_file_persistence()
    test_cooldown_expiry()
    test_status_dict()
    print("All circuit breaker tests passed!")
