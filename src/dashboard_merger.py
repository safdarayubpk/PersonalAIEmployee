from __future__ import annotations

"""Dashboard Merger — single-writer pattern for Dashboard.md updates.

Cloud agent writes incremental updates to Updates/ folder.
Local agent merges Updates/ into Dashboard.md and deletes processed files.
Prevents merge conflicts on Dashboard.md (FR-012, FR-013).
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from role_gate import get_fte_role, is_cloud, is_local


def write_update(summary: str, vault_root: Path,
                 source: str = "cloud-agent",
                 correlation_id: str = "") -> Path:
    """Write an incremental update file to Updates/ (cloud-only).

    Args:
        summary: Human-readable summary of what happened.
        vault_root: Vault root path.
        source: Component that generated the update.
        correlation_id: Optional correlation ID.

    Returns:
        Path to the created update file.

    Raises:
        PermissionError: If called from local agent.
    """
    try:
        role = get_fte_role()
        if role == "local":
            raise PermissionError("write_update() is cloud-only (FR-012)")
    except SystemExit:
        pass  # FTE_ROLE not set — allow (testing)

    updates_dir = vault_root / "Updates"
    updates_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
    ts_file = ts.strftime("%Y%m%d-%H%M%S") + f"-{ts.microsecond:06d}"

    filename = f"dashboard-update-{ts_file}.md"
    filepath = updates_dir / filename

    content = f"""---
created: "{ts_str}"
source: {source}
correlation_id: "{correlation_id}"
type: dashboard-update
---

{summary}
"""

    tmp = filepath.with_suffix(filepath.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.rename(tmp, filepath)

    return filepath


def merge_updates(vault_root: Path) -> int:
    """Merge Updates/*.md into Dashboard.md chronologically (local-only).

    Reads all update files, appends their content under a
    '## Cloud Updates' section in Dashboard.md, then deletes processed files.

    Args:
        vault_root: Vault root path.

    Returns:
        Number of update files merged.

    Raises:
        PermissionError: If called from cloud agent.
    """
    try:
        role = get_fte_role()
        if role == "cloud":
            raise PermissionError("merge_updates() is local-only (FR-013)")
    except SystemExit:
        pass  # FTE_ROLE not set — allow (testing)

    updates_dir = vault_root / "Updates"
    dashboard = vault_root / "Dashboard.md"

    if not updates_dir.exists():
        return 0

    update_files = sorted(updates_dir.glob("dashboard-update-*.md"))
    if not update_files:
        return 0

    # Read and parse each update
    entries = []
    for uf in update_files:
        text = uf.read_text(encoding="utf-8")
        # Strip frontmatter
        if text.startswith("---"):
            parts = text.split("---", 2)
            body = parts[2].strip() if len(parts) >= 3 else ""
        else:
            body = text.strip()

        # Extract created timestamp from frontmatter
        created = ""
        if text.startswith("---"):
            for line in text.split("---", 2)[1].splitlines():
                if line.strip().startswith("created:"):
                    created = line.partition(":")[2].strip().strip('"')
                    break

        entries.append({"created": created, "body": body, "file": uf})

    # Build merged content
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    merged = f"\n\n## Cloud Updates (merged {ts})\n\n"
    for entry in entries:
        merged += f"### {entry['created']}\n\n{entry['body']}\n\n"

    # Append to Dashboard.md
    if dashboard.exists():
        with open(dashboard, "a", encoding="utf-8") as f:
            f.write(merged)
    else:
        dashboard.write_text(f"# Dashboard\n{merged}", encoding="utf-8")

    # Delete processed update files
    for entry in entries:
        entry["file"].unlink()

    return len(entries)
