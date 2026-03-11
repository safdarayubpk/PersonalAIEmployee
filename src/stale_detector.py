from __future__ import annotations

"""Stale file detector — flags old Pending_Approval and Rejected files.

Detects:
- Pending_Approval/ files older than 48 hours (FR-033)
- Rejected/ files older than 7 days (FR-035)

Usage:
    from stale_detector import detect_stale_files
    stale = detect_stale_files(vault_root)
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from vault_helpers import log_operation


COMPONENT = "stale-detector"

# Thresholds
PENDING_STALE_HOURS = 48
REJECTED_STALE_DAYS = 7


def detect_stale_files(vault_root: Path) -> dict:
    """Scan Pending_Approval/ and Rejected/ for stale files.

    Returns dict with stale file lists and counts.
    """
    now = datetime.now(timezone.utc)
    stale_pending = []
    stale_rejected = []

    # Scan Pending_Approval/ (including subfolders)
    pending_dir = vault_root / "Pending_Approval"
    if pending_dir.exists():
        for path in pending_dir.glob("**/*.md"):
            age_hours = _file_age_hours(path, now)
            if age_hours is not None and age_hours > PENDING_STALE_HOURS:
                stale_pending.append({
                    "file": str(path.relative_to(vault_root)),
                    "age_hours": round(age_hours, 1),
                })

    # Scan Rejected/
    rejected_dir = vault_root / "Rejected"
    if rejected_dir.exists():
        for path in rejected_dir.glob("*.md"):
            age_hours = _file_age_hours(path, now)
            if age_hours is not None and age_hours > REJECTED_STALE_DAYS * 24:
                stale_rejected.append({
                    "file": str(path.relative_to(vault_root)),
                    "age_hours": round(age_hours, 1),
                })

    # Log if stale files found
    total = len(stale_pending) + len(stale_rejected)
    if total > 0:
        log_file = vault_root / "Logs" / "actions.jsonl"
        log_operation(
            log_file,
            component=COMPONENT,
            action="stale_detection",
            status="warning",
            detail=f"Found {len(stale_pending)} stale pending, {len(stale_rejected)} stale rejected",
            agent=os.environ.get("FTE_ROLE", "unknown"),
        )

    return {
        "stale_pending": stale_pending,
        "stale_rejected": stale_rejected,
        "total_stale": total,
    }


def update_dashboard_stale(vault_root: Path, stale_info: dict) -> None:
    """Update Dashboard.md with a ## Stale Items section (local-only).

    Replaces existing ## Stale Items section or appends a new one.
    """
    dashboard = vault_root / "Dashboard.md"
    if not dashboard.exists():
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    if stale_info["total_stale"] == 0:
        section = f"\n\n## Stale Items (checked {ts})\n\nNo stale items detected.\n"
    else:
        section = f"\n\n## Stale Items (checked {ts})\n\n"
        if stale_info["stale_pending"]:
            section += "### Stale Pending Approval (>48h)\n\n"
            for item in stale_info["stale_pending"]:
                section += f"- `{item['file']}` — {item['age_hours']}h old\n"
            section += "\n"
        if stale_info["stale_rejected"]:
            section += "### Stale Rejected (>7d)\n\n"
            for item in stale_info["stale_rejected"]:
                section += f"- `{item['file']}` — {item['age_hours'] / 24:.1f}d old\n"
            section += "\n"

    content = dashboard.read_text(encoding="utf-8")

    # Replace existing ## Stale Items section or append
    pattern = r"\n\n## Stale Items.*?(?=\n\n## |\Z)"
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, section, content, count=1, flags=re.DOTALL)
    else:
        content += section

    dashboard.write_text(content, encoding="utf-8")


def _file_age_hours(path: Path, now: datetime) -> float | None:
    """Get file age in hours from frontmatter 'created' field."""
    try:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            return None
        for line in text.split("---", 2)[1].splitlines():
            if line.strip().startswith("created:"):
                created_str = line.partition(":")[2].strip().strip('"')
                created = datetime.fromisoformat(created_str).replace(tzinfo=timezone.utc)
                return (now - created).total_seconds() / 3600
    except Exception:
        pass
    return None
