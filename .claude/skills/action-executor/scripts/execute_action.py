"""Action executor for the AI Employee vault.

Executes actions as direct Python function calls with HITL gate and
dry-run safety. No HTTP servers needed — just functions behind a gate.

CLI Usage:
    python execute_action.py --action email.send_email --params '{...}'
    python execute_action.py --action email.send_email --params '{...}' --live
    python execute_action.py --list

Module Usage:
    from execute_action import run_action
    result = run_action(action="email.draft_email", params={...})

Requirements:
    No external dependencies (stdlib only).
"""

import argparse
import importlib
import json
import os
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_VAULT_PATH = "/home/safdarayub/Documents/AI_Employee_Vault"
COMPONENT = "action-executor"
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT",
                    Path(__file__).resolve().parent.parent.parent.parent.parent))
REGISTRY_PATH = PROJECT_ROOT / "config" / "actions.json"

# Add src/ to path for action module imports
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from vault_helpers import redact_sensitive

DEFAULT_REGISTRY = {
    "actions": {
        "email.send_email": {
            "description": "Send an email",
            "hitl": True,
            "module": "actions.email",
            "function": "send_email",
        },
        "email.draft_email": {
            "description": "Create an email draft locally",
            "hitl": False,
            "module": "actions.email",
            "function": "draft_email",
        },
        "social.post_social": {
            "description": "Post to social media",
            "hitl": True,
            "module": "actions.social",
            "function": "post_social",
        },
        "calendar.create_event": {
            "description": "Create a calendar event",
            "hitl": True,
            "module": "actions.calendar",
            "function": "create_event",
        },
        "calendar.list_events": {
            "description": "List upcoming calendar events",
            "hitl": False,
            "module": "actions.calendar",
            "function": "list_events",
        },
        "documents.generate_report": {
            "description": "Generate a report document",
            "hitl": False,
            "module": "actions.documents",
            "function": "generate_report",
        },
    }
}


def log_entry(log_file: Path, **fields) -> None:
    """Append a JSON line to the log file (sensitive fields redacted)."""
    entry = {"timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"), **fields}
    entry = redact_sensitive(entry)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def load_registry() -> dict:
    """Load action registry from config/actions.json.

    Returns a dict keyed by action_id with keys: description, hitl_required,
    module, function. Handles both array format (from schema) and legacy dict.
    """
    if not REGISTRY_PATH.exists():
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY_PATH.write_text(json.dumps(DEFAULT_REGISTRY, indent=2), encoding="utf-8")
        print(f"Created default registry: {REGISTRY_PATH}")
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    actions = data.get("actions", data)
    # Handle array format from action-registry-schema.json
    if isinstance(actions, list):
        registry = {}
        for entry in actions:
            aid = entry["action_id"]
            registry[aid] = {
                "description": entry.get("description", ""),
                "hitl_required": entry.get("hitl_required", True),
                "module": entry.get("module", ""),
                "function": entry.get("function", ""),
            }
        return registry
    # Legacy dict format (DEFAULT_REGISTRY): normalize hitl → hitl_required
    normalized = {}
    for aid, config in actions.items():
        normalized[aid] = dict(config)
        if "hitl" in normalized[aid] and "hitl_required" not in normalized[aid]:
            normalized[aid]["hitl_required"] = normalized[aid].pop("hitl")
    return normalized


def check_hitl_gate(action_config: dict, vault_root: Path,
                    approval_ref: str | None) -> dict:
    """Check HITL gate. Returns gate result."""
    requires_hitl = action_config.get("hitl_required", True)

    if not requires_hitl:
        return {"passed": True, "check": "exempt", "reason": "Action is HITL-exempt"}

    if approval_ref:
        approval_path = vault_root / approval_ref
        if approval_path.exists():
            return {"passed": True, "check": "approved",
                    "reason": f"Approval found: {approval_ref}"}
        return {"passed": False, "check": "missing_approval",
                "reason": f"Approval file not found: {approval_ref}"}

    approved_dir = vault_root / "Approved"
    if approved_dir.exists():
        approved_files = list(approved_dir.glob("*.md"))
        if approved_files:
            return {"passed": True, "check": "approved_folder",
                    "reason": f"Found {len(approved_files)} approved plan(s)"}

    return {"passed": False, "check": "no_approval",
            "reason": "HITL required but no approval found"}


def create_pending_action(action_id: str, params: dict,
                          vault_root: Path, request_id: str) -> str:
    """Create a Pending_Approval file for an unapproved action."""
    ts = datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
    ts_filename = ts.strftime("%Y%m%d-%H%M%S")

    action_slug = action_id.replace(".", "-")
    filename = f"pending-{action_slug}-{request_id}-{ts_filename}.md"
    filepath = vault_root / "Pending_Approval" / filename

    params_formatted = json.dumps(params, indent=2)

    content = f"""---
title: "pending-{action_slug}"
created: "{ts_str}"
type: pending-action
action_id: "{action_id}"
request_id: "{request_id}"
status: pending_approval
---

## Action Pending Approval

Action requires human approval before execution.

## Details

- Action: {action_id}
- Request ID: {request_id}

## Parameters

```json
{params_formatted}
```

## To Approve

Move this file to `Approved/` folder, then re-run:

```bash
python .claude/skills/action-executor/scripts/execute_action.py \\
  --action {action_id} \\
  --params '{json.dumps(params)}' \\
  --approval-ref "Approved/{filename}" --live
```
"""

    tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(content, encoding="utf-8")
    os.rename(tmp_path, filepath)

    return filename


def execute_function(action_config: dict, params: dict) -> dict:
    """Dynamically import and call the action function."""
    module_path = action_config["module"]
    function_name = action_config["function"]

    try:
        mod = importlib.import_module(module_path)
    except ModuleNotFoundError:
        return {"success": False, "error": f"Module not found: {module_path}. "
                f"Create it at src/{module_path.replace('.', '/')}.py"}

    func = getattr(mod, function_name, None)
    if func is None:
        return {"success": False,
                "error": f"Function '{function_name}' not found in {module_path}"}

    if not callable(func):
        return {"success": False,
                "error": f"'{function_name}' in {module_path} is not callable"}

    try:
        result = func(**params)
        return {"success": True, "result": result}
    except Exception as e:
        tb = traceback.format_exc()
        tb_truncated = tb[-500:] if len(tb) > 500 else tb
        return {"success": False, "error": str(e),
                "error_class": type(e).__name__,
                "traceback": tb_truncated}


def run_action(action: str, params: dict | None = None, live: bool = False,
               approval_ref: str | None = None,
               vault_path: str | None = None) -> dict:
    """Execute an action with HITL gate and dry-run safety.

    Args:
        action: Action ID (e.g. "email.send_email").
        params: Parameters to pass to the action function.
        live: If True, execute for real. Default False (dry-run).
        approval_ref: Path to approval file in vault (relative).
        vault_path: Override vault root path.

    Returns:
        Dict with success, dry_run, detail, and optional result/error.
    """
    params = params or {}
    vault_root = Path(vault_path or os.environ.get("VAULT_PATH", DEFAULT_VAULT_PATH))
    log_file = vault_root / "Logs" / "actions.jsonl"
    request_id = uuid.uuid4().hex[:8]

    # Validate
    registry = load_registry()
    if action not in registry:
        available = ", ".join(sorted(registry.keys()))
        return {"success": False, "dry_run": not live,
                "detail": f"Action '{action}' not found. Available: {available}"}

    action_config = registry[action]

    # HITL gate
    gate = check_hitl_gate(action_config, vault_root, approval_ref)

    if not gate["passed"]:
        pending_file = create_pending_action(action, params, vault_root, request_id)
        log_entry(log_file, component=COMPONENT, action="hitl_block", status="blocked",
                  action_id=action, params=redact_sensitive(params), dry_run=not live,
                  hitl_check=gate["check"], request_id=request_id,
                  detail=f"HITL blocked: {gate['reason']}")
        return {"success": False, "dry_run": not live, "hitl_blocked": True,
                "pending_file": f"Pending_Approval/{pending_file}",
                "detail": f"HITL blocked: {gate['reason']}"}

    # Dry-run
    if not live:
        log_entry(log_file, component=COMPONENT, action="execute", status="dry_run",
                  action_id=action, params=redact_sensitive(params), dry_run=True,
                  hitl_check=gate["check"], request_id=request_id,
                  detail=f"DRY RUN: Would call {action}")
        return {"success": True, "dry_run": True, "request_id": request_id,
                "detail": f"DRY RUN: Would call {action} with params {params}"}

    # Live execution
    result = execute_function(action_config, params)

    status = "success" if result["success"] else "failure"
    log_entry(log_file, component=COMPONENT, action="execute", status=status,
              action_id=action, params=redact_sensitive(params), dry_run=False,
              hitl_check=gate["check"], approval_ref=approval_ref,
              request_id=request_id,
              detail=f"{'Success' if result['success'] else 'Failed'}: {action}",
              error=result.get("error"),
              traceback=result.get("traceback"))

    # Critical action logging (T026b): hitl_required=true actions log to critical_actions.jsonl
    if action_config.get("hitl_required", False):
        critical_log = vault_root / "Logs" / "critical_actions.jsonl"
        log_entry(critical_log, component=COMPONENT, action="critical_action",
                  status=status, action_id=action, request_id=request_id,
                  approval_ref=approval_ref,
                  result=str(result.get("result", ""))[:200],
                  acknowledgment_required=True,
                  detail=f"Critical action executed: {action}")

    return {"success": result["success"], "dry_run": False, "request_id": request_id,
            "result": result.get("result"), "error": result.get("error"),
            "detail": f"{'Success' if result['success'] else 'Failed'}: {action}"}


def list_actions(registry: dict) -> None:
    """List all registered actions."""
    print(f"\n{'Action':<30} {'HITL':<6} {'Module':<25} Description")
    print("-" * 95)
    for action_id, config in sorted(registry.items()):
        hitl = "Yes" if config.get("hitl_required", True) else "No"
        module = config.get("module", "—")
        desc = config.get("description", "")
        print(f"{action_id:<30} {hitl:<6} {module:<25} {desc}")
    print(f"\nTotal: {len(registry)} action(s)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute actions with HITL gate and dry-run")
    parser.add_argument("--action", default=None, help="Action ID (e.g. email.send_email)")
    parser.add_argument("--params", default="{}", help="JSON parameters for the action")
    parser.add_argument("--live", action="store_true", help="Execute for real (default: dry-run)")
    parser.add_argument("--approval-ref", default=None,
                        help="Path to approval file in vault (relative to vault root)")
    parser.add_argument("--vault-path", default=None, help="Vault root path override")
    parser.add_argument("--list", action="store_true", help="List all registered actions")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.list:
        registry = load_registry()
        list_actions(registry)
        return

    if not args.action:
        print("Error: --action is required. Use --list to see available actions.")
        sys.exit(1)

    vault_path = args.vault_path or os.environ.get("VAULT_PATH", DEFAULT_VAULT_PATH)

    if not Path(vault_path).exists():
        print(f"Error: Vault not found at {vault_path}")
        sys.exit(1)

    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON params: {e}")
        sys.exit(1)

    mode = "live" if args.live else "dry-run"
    print(f"Action Executor [{mode}] — {args.action}")

    result = run_action(
        action=args.action,
        params=params,
        live=args.live,
        approval_ref=args.approval_ref,
        vault_path=vault_path,
    )

    if result.get("hitl_blocked"):
        print(f"BLOCKED: {result['detail']}")
        print(f"Created: {result['pending_file']}")
        print("Move to Approved/ folder and re-run with --live to execute.")
    elif result["dry_run"]:
        print(f"DRY RUN: Would call {args.action}")
        print(f"Params: {json.dumps(params, indent=2)}")
        print("Add --live to execute for real.")
    elif result["success"]:
        print(f"SUCCESS: {args.action}")
        if result.get("result"):
            print(f"Result: {json.dumps(result['result'], indent=2, default=str)}")
    else:
        print(f"FAILED: {args.action}")
        print(f"Error: {result.get('error')}")

    print(json.dumps(result, indent=2, default=str))
    if result.get("hitl_blocked"):
        sys.exit(2)
    sys.exit(0 if result.get("success", False) else 1)


if __name__ == "__main__":
    main()
