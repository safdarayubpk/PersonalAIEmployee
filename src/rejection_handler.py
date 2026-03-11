from __future__ import annotations

"""Rejection handler — manages rejected drafts and re-draft escalation.

Local-only: reject_file() moves from Pending_Approval/ to Rejected/.
Cloud-only: process_rejections() scans Rejected/ and escalates to Needs_Action/manual/.

FR-031, FR-032.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from role_gate import get_fte_role
from vault_helpers import log_operation, atomic_write


COMPONENT = "rejection-handler"


def reject_file(filepath: Path, vault_root: Path, reason: str = "") -> Path:
    """Move a file from Pending_Approval/ to Rejected/ (local-only).

    Updates frontmatter with status=rejected and rejection_reason.

    Returns:
        New path in Rejected/.
    """
    try:
        role = get_fte_role()
        if role == "cloud":
            raise PermissionError("reject_file() is local-only (FR-031)")
    except SystemExit:
        pass  # FTE_ROLE not set — allow (testing)

    rejected_dir = vault_root / "Rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)
    dest = rejected_dir / filepath.name

    # Read content and update frontmatter
    content = filepath.read_text(encoding="utf-8")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2]

            # Update/add fields
            lines = fm_text.strip().split("\n")
            updates = {"status": "rejected", "rejected_at": f'"{ts}"',
                       "rejection_reason": f'"{reason}"'}
            for key, val in updates.items():
                found = False
                for i, line in enumerate(lines):
                    if line.startswith(f"{key}:"):
                        lines[i] = f"{key}: {val}"
                        found = True
                        break
                if not found:
                    lines.append(f"{key}: {val}")

            content = "---\n" + "\n".join(lines) + "\n---" + body

    atomic_write(dest, content)
    filepath.unlink()

    # Extract correlation_id for logging
    corr_id = ""
    for line in content.split("\n"):
        if line.strip().startswith("correlation_id:"):
            corr_id = line.partition(":")[2].strip().strip('"')
            break

    log_file = vault_root / "Logs" / "actions.jsonl"
    log_operation(
        log_file,
        component=COMPONENT,
        action="reject",
        status="success",
        detail=f"Rejected: {filepath.name} — {reason}",
        correlation_id=corr_id,
        agent="local",
    )

    return dest


def process_rejections(vault_root: Path) -> dict:
    """Scan Rejected/ and escalate actionable items to Needs_Action/manual/ (cloud-only).

    Returns summary dict.
    """
    try:
        role = get_fte_role()
        if role == "local":
            return {"status": "skipped", "detail": "process_rejections is cloud-only (FR-032)",
                    "processed": 0}
    except SystemExit:
        pass  # FTE_ROLE not set — allow (testing)

    rejected_dir = vault_root / "Rejected"
    manual_dir = vault_root / "Needs_Action" / "manual"

    if not rejected_dir.exists():
        return {"status": "success", "processed": 0}

    rejected_files = sorted(rejected_dir.glob("*.md"))
    if not rejected_files:
        return {"status": "success", "processed": 0}

    escalated = 0
    for filepath in rejected_files:
        content = filepath.read_text(encoding="utf-8")

        # Escalate to manual review
        manual_dir.mkdir(parents=True, exist_ok=True)
        dest = manual_dir / filepath.name
        atomic_write(dest, content)
        filepath.unlink()
        escalated += 1

    log_file = vault_root / "Logs" / "actions.jsonl"
    log_operation(
        log_file,
        component=COMPONENT,
        action="escalate_rejections",
        status="success",
        detail=f"Escalated {escalated} rejected file(s) to Needs_Action/manual/",
        agent="cloud",
    )

    return {"status": "success", "processed": escalated}
