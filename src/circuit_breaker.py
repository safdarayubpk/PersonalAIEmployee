"""Circuit breaker pattern for external service resilience.

States: closed (healthy) → open (degraded) → half-open (probing) → closed
Persists state to Logs/health.json for cross-component visibility.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


class CircuitBreaker:
    """Per-service circuit breaker with file-based state persistence.

    Args:
        service: Service name (e.g., 'odoo', 'twitter', 'facebook')
        health_file: Path to Logs/health.json
        failure_threshold: Consecutive failures before opening circuit (default: 3)
        cooldown_seconds: Seconds to wait before probing (default: 300)
    """

    def __init__(self, service: str, health_file: Path,
                 failure_threshold: int = 3, cooldown_seconds: int = 300):
        self.service = service
        self.health_file = Path(health_file)
        self.failure_threshold = max(1, failure_threshold)
        self.cooldown_seconds = max(60, min(3600, cooldown_seconds))
        self._load_state()

    def _load_state(self) -> None:
        """Load state from health.json or initialize defaults."""
        self._state = {
            "service": self.service,
            "state": "healthy",
            "consecutive_failures": 0,
            "failure_threshold": self.failure_threshold,
            "cooldown_seconds": self.cooldown_seconds,
            "cooldown_expires_at": None,
            "last_success": None,
            "last_failure": None,
            "last_error": None,
        }
        if self.health_file.exists():
            try:
                all_services = json.loads(self.health_file.read_text())
                for svc in all_services.get("services", []):
                    if svc.get("service") == self.service:
                        self._state.update(svc)
                        break
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_state(self) -> None:
        """Persist current state to health.json (atomic write)."""
        self.health_file.parent.mkdir(parents=True, exist_ok=True)

        all_services = {"services": [], "updated": _now_iso()}
        if self.health_file.exists():
            try:
                all_services = json.loads(self.health_file.read_text())
            except (json.JSONDecodeError, KeyError):
                all_services = {"services": [], "updated": _now_iso()}

        # Update or add this service
        services = all_services.get("services", [])
        found = False
        for i, svc in enumerate(services):
            if svc.get("service") == self.service:
                services[i] = dict(self._state)
                found = True
                break
        if not found:
            services.append(dict(self._state))

        all_services["services"] = services
        all_services["updated"] = _now_iso()

        tmp = self.health_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(all_services, indent=2))
        os.rename(tmp, self.health_file)

    @property
    def is_available(self) -> bool:
        """Check if the service is available for calls.

        Returns True if circuit is closed (healthy) or half-open (probing).
        Returns False if circuit is open and cooldown hasn't expired.
        """
        state = self._state["state"]
        if state == "healthy":
            return True
        if state in ("degraded", "down"):
            expires = self._state.get("cooldown_expires_at")
            if expires and _now_iso() >= expires:
                # Cooldown expired, transition to half-open
                self._state["state"] = "healthy"
                self._save_state()
                return True
            return False
        return True

    def record_success(self) -> None:
        """Record a successful call. Resets failure count, closes circuit."""
        self._state["consecutive_failures"] = 0
        self._state["state"] = "healthy"
        self._state["last_success"] = _now_iso()
        self._state["cooldown_expires_at"] = None
        self._state["last_error"] = None
        self._save_state()

    def record_failure(self, error_message: str = "",
                       non_retryable: bool = False) -> str:
        """Record a failed call. May open the circuit.

        Args:
            error_message: Description of the failure
            non_retryable: If True, immediately open circuit (e.g., 401 auth failure)

        Returns:
            New state after recording: 'healthy', 'degraded', or 'down'
        """
        self._state["consecutive_failures"] += 1
        self._state["last_failure"] = _now_iso()
        self._state["last_error"] = error_message[:200] if error_message else None

        if non_retryable or self._state["consecutive_failures"] >= self.failure_threshold:
            new_state = "down" if non_retryable else "degraded"
            self._state["state"] = new_state
            expires = datetime.now(timezone.utc).timestamp() + self.cooldown_seconds
            self._state["cooldown_expires_at"] = datetime.fromtimestamp(
                expires, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S")

        self._save_state()
        return self._state["state"]

    @property
    def state(self) -> str:
        """Current state: 'healthy', 'degraded', or 'down'."""
        return self._state["state"]

    @property
    def status_dict(self) -> dict:
        """Return full status as a dict for reporting."""
        return dict(self._state)


def load_all_health(health_file: Path) -> dict:
    """Load all service health states from health.json.

    Returns dict with 'services' list and 'updated' timestamp.
    """
    if not health_file.exists():
        return {"services": [], "updated": None}
    try:
        return json.loads(health_file.read_text())
    except (json.JSONDecodeError, KeyError):
        return {"services": [], "updated": None}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
