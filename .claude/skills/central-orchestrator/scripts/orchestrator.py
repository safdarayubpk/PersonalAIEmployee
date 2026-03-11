"""Central orchestrator for the AI Employee vault (Silver tier).

Scans Needs_Action/ for pending files from all sources, queues by priority,
triages each through risk assessment, and routes to local execution,
action-executor calls, or HITL approval.

Usage:
    python orchestrator.py                          # Process all (batch 10)
    python orchestrator.py --batch-size 5           # Custom batch
    python orchestrator.py --source gmail            # Filter by source
    python orchestrator.py --vault-path /custom/vault

Requirements:
    No external dependencies (stdlib only). Calls other skills via subprocess.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_VAULT_PATH = "/home/safdarayub/Documents/AI_Employee_Vault"
COMPONENT = "central-orchestrator"
BATCH_HARD_CAP = 50
DEFAULT_BATCH_SIZE = 10

# Constitution-canonical priority values (routine|sensitive|critical)
PRIORITY_ORDER = {"critical": 0, "sensitive": 1, "routine": 2}

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT",
                    Path(__file__).resolve().parent.parent.parent.parent.parent))
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from vault_helpers import redact_sensitive, generate_correlation_id
from role_gate import get_fte_role, validate_startup
from claim_move import claim_file, complete_file
from dashboard_merger import write_update

RISK_KEYWORDS_PATH = PROJECT_ROOT / "config" / "risk-keywords.json"

_FALLBACK_HIGH = ["payment", "invoice", "transfer", "bank", "legal", "contract",
                  "delete", "remove", "revoke", "password", "credential", "health",
                  "medical", "NDA", "salary", "terminate"]
_FALLBACK_MEDIUM = ["email", "send", "post", "publish", "reply", "forward",
                    "API", "webhook", "external", "permission", "admin"]


def _load_risk_keywords() -> tuple[list[str], list[str]]:
    """Load risk keywords from shared config, falling back to defaults."""
    if RISK_KEYWORDS_PATH.exists():
        try:
            data = json.loads(RISK_KEYWORDS_PATH.read_text(encoding="utf-8"))
            return data.get("high", _FALLBACK_HIGH), data.get("medium", _FALLBACK_MEDIUM)
        except (json.JSONDecodeError, OSError):
            pass
    return _FALLBACK_HIGH, _FALLBACK_MEDIUM


HIGH_RISK_KEYWORDS, MEDIUM_RISK_KEYWORDS = _load_risk_keywords()

# Source-to-action mapping for routable actions
SOURCE_ACTION_MAP = {
    "gmail-watcher": "email.draft_email",
    "whatsapp-watcher": None,
    "file-drop-watcher": None,
    "daily-scheduler": None,
}


def log_entry(log_file: Path, **fields) -> None:
    entry = {"timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"), **fields}
    entry = redact_sensitive(entry)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content."""
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def scan_needs_action(vault_root: Path, source_filter: str | None) -> list[dict]:
    """Scan Needs_Action/ and Needs_Action/<domain>/ for pending .md files."""
    needs_action = vault_root / "Needs_Action"
    if not needs_action.exists():
        return []

    files = []
    # Scan both root and subdomain folders (Platinum tier)
    for path in sorted(needs_action.glob("**/*.md")):
        if path.name.endswith(".moved"):
            continue

        content = path.read_text(encoding="utf-8")
        fm = parse_frontmatter(content)

        if fm.get("status") == "processing":
            continue

        source = fm.get("source", "unknown")
        if source_filter and source_filter not in source:
            continue

        # Extract or generate correlation_id (T054/T056)
        corr_id = fm.get("correlation_id", "")
        if not corr_id:
            corr_id = generate_correlation_id()
            log_entry(vault_root / "Logs" / "orchestrator.jsonl",
                      component=COMPONENT, action="generate_correlation_id",
                      status="warning", file=path.name,
                      correlation_id=corr_id,
                      detail=f"Missing correlation_id — generated retroactively for {path.name}")

        files.append({
            "path": path,
            "filename": path.name,
            "source": source,
            "priority": fm.get("priority", "routine"),
            "title": fm.get("title", path.stem),
            "created": fm.get("created", ""),
            "type": fm.get("type", ""),
            "content": content,
            "frontmatter": fm,
            "correlation_id": corr_id,
        })

    return files


def queue_by_priority(files: list[dict], batch_size: int) -> tuple[list[dict], int]:
    """Sort by priority then creation time, cap at batch_size."""
    sorted_files = sorted(files, key=lambda f: (
        PRIORITY_ORDER.get(f["priority"], 2),
        f["created"],
    ))
    deferred = max(0, len(sorted_files) - batch_size)
    return sorted_files[:batch_size], deferred


def assess_risk(content: str) -> tuple[str, list[str]]:
    """Inline risk assessment via keyword scan."""
    lower = content.lower()
    matched = []

    for kw in HIGH_RISK_KEYWORDS:
        if kw.lower() in lower:
            matched.append(kw)

    if matched:
        return "high", matched

    for kw in MEDIUM_RISK_KEYWORDS:
        if kw.lower() in lower:
            matched.append(kw)

    if matched:
        return "medium", matched

    return "low", []


def mark_status(path: Path, status: str) -> None:
    """Update frontmatter status field in a file."""
    content = path.read_text(encoding="utf-8")
    updated = re.sub(r'(status:\s*)"?[^"\n]+"?', f'\\1{status}', content)
    path.write_text(updated, encoding="utf-8")


def create_plan(file_info: dict, risk_level: str, vault_root: Path) -> str:
    """Create a plan file in Plans/."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    plan_name = f"plan-{file_info['title'][:40]}-{ts}.md"
    plan_path = vault_root / "Plans" / plan_name

    content = f"""---
title: "{plan_name}"
created: "{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')}"
source: central-orchestrator
risk_level: "{risk_level}"
original_file: "{file_info['filename']}"
---

## Plan: {file_info['title']}

- Source: {file_info['source']}
- Priority: {file_info['priority']}
- Risk: {risk_level}

## Action

Process according to Company_Handbook.md rules.
"""

    tmp = plan_path.with_suffix(plan_path.suffix + ".tmp")
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(content, encoding="utf-8")
    os.rename(tmp, plan_path)
    return plan_name


def route_to_done(file_info: dict, vault_root: Path) -> None:
    """Move file to Done/ with .moved rename in Needs_Action/."""
    src = file_info["path"]
    done_path = vault_root / "Done" / file_info["filename"]

    # Copy content to Done/
    tmp = done_path.with_suffix(done_path.suffix + ".tmp")
    done_path.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(file_info["content"], encoding="utf-8")
    os.rename(tmp, done_path)

    # Rename original to .moved
    moved_path = src.with_suffix(src.suffix + ".moved")
    os.rename(src, moved_path)


def route_to_pending(file_info: dict, risk_level: str, matched_keywords: list[str],
                     vault_root: Path) -> None:
    """Move file to Pending_Approval/."""
    src = file_info["path"]
    pending_path = vault_root / "Pending_Approval" / file_info["filename"]

    # Copy to Pending_Approval/
    tmp = pending_path.with_suffix(pending_path.suffix + ".tmp")
    pending_path.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(file_info["content"], encoding="utf-8")
    os.rename(tmp, pending_path)

    # Rename original to .moved
    moved_path = src.with_suffix(src.suffix + ".moved")
    os.rename(src, moved_path)


def attempt_action(file_info: dict, vault_root: Path) -> dict:
    """Attempt a dry-run action call for the file's source type."""
    action_id = SOURCE_ACTION_MAP.get(file_info["source"])
    if not action_id:
        return {"attempted": False, "reason": "No action mapping for source"}

    script = Path(__file__).resolve().parent.parent.parent / "action-executor" / "scripts" / "execute_action.py"
    if not script.exists():
        return {"attempted": False, "reason": "action-executor script not found"}

    cmd = [
        sys.executable, str(script),
        "--action", action_id,
        "--params", json.dumps({"source_file": file_info["filename"]}),
        "--vault-path", str(vault_root),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return {
            "attempted": True,
            "dry_run": True,
            "action": action_id,
            "exit_code": result.returncode,
            "output": result.stdout[:200],
        }
    except Exception as e:
        return {"attempted": True, "dry_run": True, "error": str(e)}


def check_stale_approvals(vault_root: Path, log_file: Path, max_age_hours: int = 48) -> int:
    """Warn about Pending_Approval files older than max_age_hours."""
    pending_dir = vault_root / "Pending_Approval"
    if not pending_dir.exists():
        return 0

    stale_count = 0
    now = datetime.now(timezone.utc)
    for path in pending_dir.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        fm = parse_frontmatter(content)
        created = fm.get("created", "")
        if created:
            try:
                created_dt = datetime.fromisoformat(created).replace(tzinfo=timezone.utc)
                age_hours = (now - created_dt).total_seconds() / 3600
                if age_hours > max_age_hours:
                    stale_count += 1
                    log_entry(log_file, component=COMPONENT, action="stale_approval",
                              status="warning", file=path.name,
                              age_hours=round(age_hours, 1),
                              detail=f"Stale Pending_Approval: {path.name} ({age_hours:.0f}h old)")
            except (ValueError, TypeError):
                pass
    return stale_count


def update_dashboard(vault_root: Path, stats: dict) -> None:
    """Append orchestrator summary to Dashboard.md."""
    dashboard = vault_root / "Dashboard.md"
    if not dashboard.exists():
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    run_id = stats.get("run_id", "unknown")

    entry = f"\n### Orchestrator Run — {ts} ({run_id})\n\n"
    entry += "| Metric | Count |\n|--------|-------|\n"
    entry += f"| Files scanned | {stats['scanned']} |\n"
    entry += f"| Processed (Done) | {stats['processed']} |\n"
    entry += f"| Action calls (dry-run) | {stats['action_calls']} |\n"
    entry += f"| Pending approval | {stats['pending_approval']} |\n"
    entry += f"| Deferred to next run | {stats['deferred']} |\n"
    entry += f"| Errors | {stats['errors']} |\n"

    if stats.get("by_source"):
        entry += "\n| Source | Count |\n|--------|-------|\n"
        for src, cnt in stats["by_source"].items():
            entry += f"| {src} | {cnt} |\n"

    with open(dashboard, "a") as f:
        f.write(entry)


def process_file(file_info: dict, vault_root: Path, log_file: Path) -> dict:
    """Triage and route a single Needs_Action file with claim-by-move."""
    # Determine current agent role
    try:
        role = get_fte_role()
    except SystemExit:
        role = "local"  # Gold backward compat

    # Claim-by-move: atomically claim file before processing (T027/T028)
    claimed_path = claim_file(file_info["path"], role, vault_root)
    if claimed_path is None:
        log_entry(log_file, component=COMPONENT, action="claim_failed", status="skipped",
                  file=file_info["filename"],
                  detail=f"File already claimed by another agent, skipping")
        return {"route": "skipped", "risk_level": "unknown", "mcp": None}

    # Update file_info path to claimed location
    file_info["path"] = claimed_path

    risk_level, matched = assess_risk(file_info["content"])

    create_plan(file_info, risk_level, vault_root)

    route = "done"
    mcp_result = None

    if risk_level == "high":
        route = "pending_approval"
        # Use complete_file to move from In_Progress to Pending_Approval (T029)
        complete_file(claimed_path, "Pending_Approval", vault_root, status="pending_approval")

    elif risk_level == "medium":
        mcp_result = attempt_action(file_info, vault_root)
        complete_file(claimed_path, "Pending_Approval", vault_root, status="pending_approval")
        if mcp_result.get("attempted"):
            route = "pending_approval_with_action"
        else:
            route = "pending_approval"

    else:
        mcp_result = attempt_action(file_info, vault_root)
        complete_file(claimed_path, "Done", vault_root, status="completed")
        if mcp_result.get("attempted"):
            route = "done_with_action"
        else:
            route = "done"

    log_entry(log_file, component=COMPONENT, action="route_task", status="success",
              file=file_info["filename"], source=file_info["source"],
              priority=file_info["priority"], risk_level=risk_level,
              route=route, matched_keywords=matched,
              mcp=mcp_result, agent=role,
              correlation_id=file_info.get("correlation_id", ""),
              detail=f"Routed {file_info['filename']} to {route}")

    # T031: Cloud agent writes incremental dashboard update after processing (FR-012)
    if role == "cloud":
        try:
            summary = (f"Processed `{file_info['filename']}` — "
                       f"route: {route}, risk: {risk_level}, source: {file_info['source']}")
            write_update(summary, vault_root, source=COMPONENT,
                         correlation_id=file_info.get("correlation_id", ""))
        except Exception:
            pass  # Non-critical — don't fail processing on dashboard update error

    return {"route": route, "risk_level": risk_level, "mcp": mcp_result}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Central orchestrator for AI Employee vault")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help=f"Max files per run (default: {DEFAULT_BATCH_SIZE}, cap: {BATCH_HARD_CAP})")
    parser.add_argument("--source", default=None,
                        help="Filter by source (filesystem, gmail, whatsapp, scheduler)")
    parser.add_argument("--vault-path", default=None, help="Vault root path override")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    vault_path = args.vault_path or os.environ.get("VAULT_PATH", DEFAULT_VAULT_PATH)
    vault_root = Path(vault_path)
    log_file = vault_root / "Logs" / "orchestrator.jsonl"
    batch_size = min(max(args.batch_size, 1), BATCH_HARD_CAP)

    if not vault_root.exists():
        print(f"Error: Vault not found at {vault_root}")
        sys.exit(1)

    run_id = f"orch-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    print(f"Central Orchestrator [{run_id}] — batch size {batch_size}")

    # Step 1: Scan
    all_files = scan_needs_action(vault_root, args.source)
    print(f"Scanned: {len(all_files)} pending file(s)")

    if not all_files:
        log_entry(log_file, component=COMPONENT, action="scan", status="success",
                  run_id=run_id, detail="No pending files in Needs_Action/")
        print("No pending files. Done.")
        result = {"status": "processed", "run_id": run_id, "scanned": 0,
                  "processed": 0, "action_calls": 0, "pending_approval": 0,
                  "deferred": 0, "errors": 0, "by_source": {}, "next_action": "none"}
        print(json.dumps(result, indent=2))
        return

    # Step 2: Queue
    queued, deferred = queue_by_priority(all_files, batch_size)
    if deferred > 0:
        print(f"Queued: {len(queued)}, Deferred: {deferred}")
        log_entry(log_file, component=COMPONENT, action="queue", status="success",
                  run_id=run_id, queued=len(queued), deferred=deferred,
                  detail=f"Deferred {deferred} file(s) to next run")

    # Step 3-4: Triage and Route
    stats = {"scanned": len(all_files), "processed": 0, "action_calls": 0,
             "pending_approval": 0, "deferred": deferred, "errors": 0, "by_source": {}}

    for file_info in queued:
        source_key = file_info["source"].replace("-watcher", "").replace("-", "_")
        stats["by_source"][source_key] = stats["by_source"].get(source_key, 0) + 1

        try:
            result = process_file(file_info, vault_root, log_file)

            if result["route"] in ("done", "done_with_action"):
                stats["processed"] += 1
            elif result["route"] in ("pending_approval", "pending_approval_with_action"):
                stats["pending_approval"] += 1
            if result.get("mcp", {}).get("attempted"):
                stats["action_calls"] += 1

            print(f"  [{file_info['priority'].upper()}] {file_info['filename']} "
                  f"→ {result['route']} (risk: {result['risk_level']})")

        except Exception as e:
            stats["errors"] += 1
            # Reset status on error
            try:
                mark_status(file_info["path"], "needs_action")
            except Exception:
                pass
            log_entry(log_file, component=COMPONENT, action="process_error", status="failure",
                      run_id=run_id, file=file_info["filename"], error=str(e),
                      detail=f"Error processing {file_info['filename']}: {e}")
            print(f"  [ERROR] {file_info['filename']}: {e}")

    # Step 5: Stale Pending_Approval detection (T048)
    stale = check_stale_approvals(vault_root, log_file)
    if stale > 0:
        print(f"  Warning: {stale} stale Pending_Approval file(s) older than 48 hours")

    # Step 6: Update Dashboard
    stats["run_id"] = run_id
    update_dashboard(vault_root, stats)

    # Determine next action
    if stats["pending_approval"] > 0:
        next_action = "hitl"
    elif stats["action_calls"] > 0:
        next_action = "mcp"
    else:
        next_action = "none"

    status = "processed"
    if stats["pending_approval"] > 0 or stats["action_calls"] > 0:
        status = "routed"
    if stats["deferred"] > 0:
        status = "queued"

    output = {
        "status": status,
        "run_id": run_id,
        "scanned": stats["scanned"],
        "processed": stats["processed"],
        "action_calls": stats["action_calls"],
        "pending_approval": stats["pending_approval"],
        "deferred": stats["deferred"],
        "errors": stats["errors"],
        "by_source": stats["by_source"],
        "next_action": next_action,
    }

    log_output = {k: v for k, v in output.items() if k != "status"}
    log_entry(log_file, component=COMPONENT, action="run_complete", status="success",
              run_id=run_id, **log_output,
              detail=f"Orchestrator run complete: {stats['processed']} processed, "
                     f"{stats['pending_approval']} pending, {stats['deferred']} deferred")

    print(f"\nDone: {stats['processed']} processed, {stats['action_calls']} MCP, "
          f"{stats['pending_approval']} pending, {stats['deferred']} deferred, "
          f"{stats['errors']} errors")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
