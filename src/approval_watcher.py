from __future__ import annotations

"""Approval Watcher — scans Approved/ folder and executes approved actions.

Local-only module (FR-027, FR-028). Refuses to run on cloud agent.
Reads approved .md files, dispatches to correct action handler,
moves to Done/ on success or Needs_Action/manual/ on failure.

Usage:
    python approval_watcher.py                     # Process all approved files
    python approval_watcher.py --vault-path /x     # Custom vault path
    python approval_watcher.py --dry-run            # Preview without executing
"""

import importlib
import json
import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from role_gate import get_fte_role, is_cloud, RoleViolationError
from vault_helpers import generate_correlation_id
from correlation import is_valid_correlation_id

DEFAULT_VAULT_PATH = "/home/safdarayub/Documents/AI_Employee_Vault"
COMPONENT = "approval-watcher"


def _log(vault_root: Path, action: str, detail: str, **extra) -> None:
    """Append a JSONL log entry for approval watcher."""
    log_file = vault_root / "Logs" / "approval_watcher.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "component": COMPONENT,
        "action": action,
        "detail": detail,
    }
    entry.update(extra)
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

# Map tool names from pending approval files to action handlers
ACTION_DISPATCH = {
    "email.send": {"module": "actions.email", "function": "send_email"},
    "social.post_facebook": {"module": "actions.social", "function": "post_social", "extra": {"platform": "facebook"}},
    "social.post_instagram": {"module": "actions.social", "function": "post_social", "extra": {"platform": "instagram"}},
    "social.post_twitter": {"module": "actions.social", "function": "post_social", "extra": {"platform": "twitter"}},
    "odoo.create_invoice": {"module": "actions.documents", "function": "generate_report"},
    "odoo.register_payment": {"module": "actions.documents", "function": "generate_report"},
}


def _parse_frontmatter(filepath: Path) -> dict:
    """Parse YAML frontmatter from a markdown file."""
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}

    frontmatter = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            value = value.strip().strip('"').strip("'")
            frontmatter[key.strip()] = value

    return frontmatter


def _parse_params_from_file(filepath: Path) -> dict:
    """Extract action parameters from the JSON block in an approved file."""
    text = filepath.read_text(encoding="utf-8")
    # Find the ```json ... ``` block
    start = text.find("```json")
    if start == -1:
        return {}
    start = text.index("\n", start) + 1
    end = text.find("```", start)
    if end == -1:
        return {}

    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return {}


def _move_file(source: Path, dest_dir: Path, **frontmatter_updates) -> Path:
    """Move a file to a destination directory, updating frontmatter fields."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / source.name

    text = source.read_text(encoding="utf-8")

    # Update frontmatter fields
    for key, value in frontmatter_updates.items():
        if f"{key}:" in text:
            import re
            text = re.sub(
                rf'^{key}:.*$',
                f'{key}: "{value}"' if isinstance(value, str) else f'{key}: {value}',
                text,
                count=1,
                flags=re.MULTILINE,
            )
        elif text.startswith("---"):
            # Add field to frontmatter
            text = text.replace("---\n", f"---\n{key}: \"{value}\"\n", 1)

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.rename(tmp, dest)
    source.unlink()

    return dest


def process_approved(vault_root: Path, dry_run: bool = False) -> dict:
    """Scan Approved/ for approved action files and execute them.

    Returns summary dict with counts and details.
    """
    # Guard: refuse to run on cloud agent
    try:
        role = get_fte_role()
        if role == "cloud":
            return {
                "status": "refused",
                "detail": "approval_watcher refuses to run on FTE_ROLE=cloud",
                "processed": 0,
            }
    except SystemExit:
        pass  # FTE_ROLE not set — Gold backward compat, allow

    approved_dir = vault_root / "Approved"
    done_dir = vault_root / "Done"
    manual_dir = vault_root / "Needs_Action" / "manual"

    if not approved_dir.exists():
        return {"status": "success", "processed": 0, "detail": "No Approved/ directory"}

    approved_files = sorted(approved_dir.glob("**/*.md"))
    if not approved_files:
        return {"status": "success", "processed": 0, "detail": "No approved files found"}

    results = []
    success_count = 0
    failure_count = 0

    for filepath in approved_files:
        frontmatter = _parse_frontmatter(filepath)
        tool = frontmatter.get("tool", "")
        corr_id = frontmatter.get("correlation_id", "")

        if not tool:
            # Unknown file format, move to manual
            _move_file(filepath, manual_dir, status="manual_review",
                       detail="No tool field in frontmatter")
            failure_count += 1
            results.append({"file": filepath.name, "status": "no_tool", "tool": ""})
            continue

        params = _parse_params_from_file(filepath)

        if dry_run:
            results.append({
                "file": filepath.name,
                "status": "dry_run",
                "tool": tool,
                "params_keys": list(params.keys()),
            })
            continue

        # Dispatch to action handler
        handler = ACTION_DISPATCH.get(tool)
        if not handler:
            _move_file(filepath, manual_dir, status="manual_review",
                       detail=f"No handler registered for tool: {tool}")
            failure_count += 1
            _log(vault_root, "no_handler", f"No handler for tool: {tool}",
                 file=filepath.name, tool=tool)
            results.append({"file": filepath.name, "status": "no_handler", "tool": tool})
            continue

        try:
            # Import and call the action handler
            mod = importlib.import_module(handler["module"])
            func = getattr(mod, handler["function"])

            # Merge extra params (e.g. platform for social)
            call_params = {**params}
            if "extra" in handler:
                call_params.update(handler["extra"])

            result = func(**call_params)

            # Move to Done/ on success
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            _move_file(filepath, done_dir, status="completed",
                       completed_at=ts, executed_by="local")

            _log(vault_root, "executed", f"Executed approved action: {tool}",
                 correlation_id=corr_id, tool=tool)

            success_count += 1
            results.append({
                "file": filepath.name,
                "status": "executed",
                "tool": tool,
                "result": result,
            })

        except Exception as e:
            # Move to Needs_Action/manual/ on failure (FR-028)
            _move_file(filepath, manual_dir, status="execution_failed",
                       error=str(e))
            failure_count += 1
            _log(vault_root, "execution_failed", f"Execution failed for {tool}: {e}",
                 file=filepath.name, tool=tool)
            results.append({
                "file": filepath.name,
                "status": "failed",
                "tool": tool,
                "error": str(e),
            })

    return {
        "status": "success",
        "processed": len(approved_files),
        "succeeded": success_count,
        "failed": failure_count,
        "dry_run": dry_run,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Process approved action files")
    parser.add_argument("--vault-path", default=None, help="Vault root path")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    args = parser.parse_args()

    vault_path = args.vault_path or os.environ.get("VAULT_PATH", DEFAULT_VAULT_PATH)
    vault_root = Path(vault_path)

    if not vault_root.exists():
        print(f"Error: Vault not found at {vault_root}")
        sys.exit(1)

    result = process_approved(vault_root, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
