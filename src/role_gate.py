"""FTE_ROLE detection, validation, and enforcement for Platinum tier.

Centralized role gating module. Every component that can trigger external
effects MUST call enforce_role_gate() before execution (FR-008).

Valid roles: 'cloud' (draft-only), 'local' (full Gold-tier capabilities).
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

VALID_ROLES = ("cloud", "local")

# Risk levels that cloud agents are NOT permitted to execute
CLOUD_BLOCKED_RISK_LEVELS = ("sensitive", "critical")


class RoleViolationError(Exception):
    """Raised when an action is attempted that the current role forbids."""


def get_fte_role() -> str:
    """Read FTE_ROLE from environment.

    Returns:
        'cloud' or 'local'.

    Raises:
        SystemExit: If FTE_ROLE is missing or invalid.
    """
    role = os.environ.get("FTE_ROLE", "").strip().lower()
    if role not in VALID_ROLES:
        print(
            f"FATAL: FTE_ROLE must be set to 'cloud' or 'local', got: '{role}'"
            if role
            else "FATAL: FTE_ROLE environment variable is not set. "
            "Set FTE_ROLE=cloud on the VM or FTE_ROLE=local on the laptop.",
            file=sys.stderr,
        )
        sys.exit(1)
    return role


def is_cloud() -> bool:
    """Return True if FTE_ROLE is 'cloud'."""
    return get_fte_role() == "cloud"


def is_local() -> bool:
    """Return True if FTE_ROLE is 'local'."""
    return get_fte_role() == "local"


def enforce_role_gate(action_name: str, risk_level: str) -> None:
    """Check if the current role permits the action at the given risk level.

    When FTE_ROLE=cloud and risk is sensitive or critical, raises
    RoleViolationError. Logs the refusal.

    When FTE_ROLE=local, all risk levels are permitted (HITL gate
    handles approval separately).

    Args:
        action_name: Name of the action being attempted (e.g., 'email_send').
        risk_level: One of 'routine', 'sensitive', 'critical'.

    Raises:
        RoleViolationError: If the action is blocked for the current role.
    """
    role = get_fte_role()
    if role == "cloud" and risk_level in CLOUD_BLOCKED_RISK_LEVELS:
        msg = (
            f"BLOCKED: Action '{action_name}' (risk={risk_level}) "
            f"is not permitted when FTE_ROLE=cloud. Draft to Pending_Approval/ instead."
        )
        logger.warning(msg)
        raise RoleViolationError(msg)


def validate_startup() -> str:
    """Validate FTE_ROLE at process startup.

    Call this at the top of every daemon's main() to fail fast on
    misconfiguration.

    Returns:
        The validated role string ('cloud' or 'local').
    """
    role = get_fte_role()
    logger.info(f"FTE_ROLE validated: {role}")
    return role
