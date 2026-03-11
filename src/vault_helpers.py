from __future__ import annotations

"""Shared utilities for the AI Employee vault.

Provides path validation, JSONL logging, frontmatter generation,
and atomic file writes used by setup_vault.py and file_drop_watcher.py.
"""

import json
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path


# Default vault path
DEFAULT_VAULT_PATH = "/home/safdarayub/Documents/AI_Employee_Vault"


class PathViolationError(Exception):
    """Raised when a target path resolves outside the vault root."""


def resolve_vault_path() -> Path:
    """Resolve vault path from VAULT_PATH env var or default.

    Returns an absolute Path. Raises ValueError if the path is not absolute.
    """
    raw = os.environ.get("VAULT_PATH", DEFAULT_VAULT_PATH)
    vault = Path(raw).expanduser()
    if not vault.is_absolute():
        raise ValueError(f"Vault path must be absolute, got: {vault}")
    return vault


def validate_path(target: Path, vault_root: Path) -> Path:
    """Validate that target resolves within vault_root.

    Args:
        target: The path to validate (can be relative to vault_root).
        vault_root: The vault root directory.

    Returns:
        The resolved absolute path.

    Raises:
        PathViolationError: If target resolves outside vault_root.
    """
    if not target.is_absolute():
        resolved = (vault_root / target).resolve()
    else:
        resolved = target.resolve()

    vault_resolved = vault_root.resolve()

    if not (resolved == vault_resolved or str(resolved).startswith(str(vault_resolved) + "/")):
        raise PathViolationError(
            f"Path violation: {target} resolves to {resolved}, "
            f"which is outside vault root {vault_resolved}"
        )
    return resolved


def _get_agent_field():
    """Return the current FTE_ROLE value for log entries, or None if unset.

    Does NOT raise on missing FTE_ROLE — logging should never crash the caller.
    """
    return os.environ.get("FTE_ROLE", "").strip().lower() or None


def log_operation(log_file: Path, component: str, action: str, status: str,
                  detail: str, **extra) -> None:
    """Append one JSON line to a .jsonl log file.

    Args:
        log_file: Absolute path to the .jsonl file.
        component: Source component (e.g., "setup-vault").
        action: What was attempted (e.g., "create_folder").
        status: One of "success", "failure", "skipped".
        detail: Human-readable description.
        **extra: Additional fields merged into the log entry.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "component": component,
        "action": action,
        "status": status,
        "detail": detail,
    }
    # Add agent field for Platinum tier traceability
    agent = extra.pop("agent", None) or _get_agent_field()
    if agent:
        entry["agent"] = agent
    entry.update(extra)

    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def log_error(vault_root: Path, component: str, action: str, detail: str,
              error: Exception, traceback_str: str | None = None) -> None:
    """Append an error entry to Logs/errors.jsonl.

    Args:
        vault_root: The vault root directory.
        component: Source component.
        action: What was attempted.
        detail: Human-readable description.
        error: The exception that occurred.
        traceback_str: Optional traceback string. If None, captures current.
    """
    if traceback_str is None:
        traceback_str = traceback.format_exc()

    log_file = vault_root / "Logs" / "errors.jsonl"
    agent = _get_agent_field()
    log_operation(
        log_file,
        component=component,
        action=action,
        status="failure",
        detail=detail,
        error=type(error).__name__,
        traceback=traceback_str,
        **({"agent": agent} if agent else {}),
    )


def generate_frontmatter(**fields) -> str:
    """Generate YAML frontmatter string from keyword arguments.

    Uses f-string formatting (not PyYAML) per research R4.
    Values containing colons or special characters are quoted.

    Returns:
        A string like:
        ---
        key1: value1
        key2: "value: with colon"
        ---
    """
    lines = ["---"]
    for key, value in fields.items():
        str_val = str(value)
        # Quote values that contain characters that could confuse YAML parsers
        if any(c in str_val for c in (":", "#", "[", "]", "{", "}", ",", "&", "*", "?", "|", "-", "<", ">", "=", "!", "%", "@", "`")):
            str_val = f'"{str_val}"'
        lines.append(f"{key}: {str_val}")
    lines.append("---")
    return "\n".join(lines)


# Keys that trigger redaction (FR-016)
_SENSITIVE_KEY_PATTERNS = ("password", "token", "secret", "api_key", "credential", "auth")


def redact_sensitive(data: dict) -> dict:
    """Return a copy of data with sensitive field values replaced.

    Any key containing one of the sensitive patterns (password, token,
    secret, api_key, credential, auth) has its value replaced with
    ***REDACTED***. Nested dicts are redacted recursively.

    Args:
        data: The dictionary to redact.

    Returns:
        A new dict with sensitive values replaced.
    """
    redacted = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(pat in key_lower for pat in _SENSITIVE_KEY_PATTERNS):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_sensitive(value)
        else:
            redacted[key] = value
    return redacted


def generate_correlation_id() -> str:
    """Generate a unique correlation ID. Delegates to src/correlation.py."""
    from correlation import generate_correlation_id as _gen
    return _gen()


def atomic_write(target_path: Path, content: str) -> None:
    """Write content to target_path atomically via temp file + rename.

    Writes to {target_path}.tmp in the same directory, then renames
    to target_path. This is atomic on POSIX filesystems per research R3.

    Args:
        target_path: The final file path.
        content: The string content to write.
    """
    target_path = Path(target_path)
    tmp_path = target_path.with_suffix(target_path.suffix + ".tmp")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(content, encoding="utf-8")
    os.rename(tmp_path, target_path)
