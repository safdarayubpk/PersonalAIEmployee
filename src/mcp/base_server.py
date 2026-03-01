"""Shared MCP server utilities for HITL classification, dry-run, and JSONL logging.

All Gold tier MCP servers import from this module for consistent behavior.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

# HITL levels
HITL_ROUTINE = "routine"
HITL_SENSITIVE = "sensitive"
HITL_CRITICAL = "critical"

# Default vault path
DEFAULT_VAULT_PATH = "/home/safdarayub/Documents/AI_Employee_Vault"


def get_vault_path() -> Path:
    """Resolve vault path from env var or default."""
    return Path(os.environ.get("VAULT_PATH", DEFAULT_VAULT_PATH))


def is_dry_run() -> bool:
    """Check if DRY_RUN mode is active (default: True)."""
    return os.environ.get("DRY_RUN", "true").lower() in ("true", "1", "yes")


def is_live_mode() -> bool:
    """Check if live mode is active."""
    return not is_dry_run()


def log_tool_call(domain: str, tool: str, action: str, status: str,
                  detail: str, correlation_id: str | None = None,
                  params: dict | None = None, result: dict | None = None) -> None:
    """Append a JSONL log entry for an MCP tool call.

    Logs to Logs/mcp_{domain}.jsonl with all required fields per data-model Entity 7.
    """
    vault = get_vault_path()
    log_file = vault / "Logs" / f"mcp_{domain}.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "component": f"fte-{domain}",
        "correlation_id": correlation_id or "",
        "tool": tool,
        "action": action,
        "status": status,
        "params": _redact_sensitive(params or {}),
        "detail": detail,
    }
    if result is not None:
        entry["result"] = result

    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def log_critical_action(tool: str, action: str, status: str,
                        detail: str, correlation_id: str | None = None,
                        params: dict | None = None) -> None:
    """Log critical actions to Logs/critical_actions.jsonl."""
    vault = get_vault_path()
    log_file = vault / "Logs" / "critical_actions.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "component": "mcp-critical",
        "correlation_id": correlation_id or "",
        "tool": tool,
        "action": action,
        "status": status,
        "params": _redact_sensitive(params or {}),
        "detail": detail,
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def create_pending_approval(tool: str, params: dict,
                            correlation_id: str | None = None) -> str:
    """Create a Pending_Approval file for HITL-gated actions.

    Returns the path to the created file.
    """
    vault = get_vault_path()
    pending_dir = vault / "Pending_Approval"
    pending_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
    ts_file = ts.strftime("%Y%m%d-%H%M%S")

    slug = tool.replace(".", "-")
    filename = f"pending-{slug}-{ts_file}.md"
    filepath = pending_dir / filename

    content = f"""---
title: "Pending Approval: {tool}"
created: "{ts_str}"
type: pending-approval
tool: {tool}
status: pending_approval
correlation_id: "{correlation_id or ''}"
---

## Action Requiring Approval

**Tool**: `{tool}`
**Time**: {ts_str}
**Correlation ID**: {correlation_id or 'N/A'}

## Parameters

```json
{json.dumps(_redact_sensitive(params), indent=2)}
```

## Instructions

To approve this action:
1. Review the parameters above
2. Move this file to `Approved/`
3. Re-trigger the action with `--live` mode and `--approval-ref` pointing to the approved file
"""

    # Atomic write
    tmp = filepath.with_suffix(filepath.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.rename(tmp, filepath)

    return str(filepath)


def make_response(status: str, tool: str, correlation_id: str | None = None,
                  **extra) -> dict:
    """Build a standard MCP tool response dict."""
    resp = {
        "status": status,
        "tool": tool,
        "correlation_id": correlation_id or "",
    }
    resp.update(extra)
    return resp


# Sensitive field patterns for redaction
_SENSITIVE_PATTERNS = ("password", "token", "secret", "api_key", "credential", "auth")


def get_circuit_breaker(service: str) -> "CircuitBreaker":
    """Get or create a circuit breaker for a service."""
    from circuit_breaker import CircuitBreaker
    vault = get_vault_path()
    health_file = vault / "Logs" / "health.json"
    return CircuitBreaker(service, health_file)


def check_service_available(service: str) -> tuple[bool, dict | None]:
    """Check if a service is available via circuit breaker.

    Returns (True, None) if available, or (False, error_response) if degraded.
    """
    cb = get_circuit_breaker(service)
    if cb.is_available:
        return True, None
    return False, {
        "status": "service_degraded",
        "service": service,
        "state": cb.state,
        "detail": f"Service '{service}' is degraded. Circuit breaker is open.",
    }


def _redact_sensitive(data: dict) -> dict:
    """Return a copy with sensitive field values replaced by ***REDACTED***."""
    redacted = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(pat in key_lower for pat in _SENSITIVE_PATTERNS):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = _redact_sensitive(value)
        else:
            redacted[key] = value
    return redacted
