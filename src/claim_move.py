from __future__ import annotations

"""Claim-by-move concurrency control for Platinum tier.

Prevents duplicate processing when both cloud and local agents are active.
Uses os.rename() for atomic file moves on POSIX (FR-009, FR-010, FR-011).
"""

import logging
import os
from pathlib import Path

import yaml

from vault_helpers import log_operation, atomic_write

logger = logging.getLogger(__name__)


def claim_file(source_path: Path, role: str, vault_path: Path) -> Path | None:
    """Atomically claim a file by moving it to In_Progress/<role>/.

    Uses os.rename() which is atomic on POSIX when source and destination
    are on the same filesystem (FR-009).

    Args:
        source_path: Path to the file in Needs_Action/<domain>/.
        role: Current agent role ('cloud' or 'local').
        vault_path: Root path of the vault.

    Returns:
        New path in In_Progress/<role>/ on success, None if already claimed.
    """
    dest_dir = vault_path / "In_Progress" / role
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / source_path.name

    # Read correlation_id from frontmatter before move (T038, FR-019)
    corr_id = ""
    try:
        fm = _read_frontmatter(source_path)
        corr_id = fm.get("correlation_id", "")
    except Exception:
        pass

    try:
        os.rename(source_path, dest_path)
    except FileNotFoundError:
        # File already claimed by another agent (FR-010)
        log_file = vault_path / "Logs" / "actions.jsonl"
        log_operation(
            log_file,
            component="claim-move",
            action="claim",
            status="skipped",
            detail=f"File already claimed, skipping: {source_path.name}",
            agent=role,
            correlation_id=corr_id,
        )
        logger.info(f"File already claimed, skipping: {source_path.name}")
        return None
    except OSError as e:
        logger.error(f"Failed to claim {source_path.name}: {e}")
        return None

    # Update frontmatter status to in_progress
    _update_frontmatter_field(dest_path, "status", "in_progress")
    _update_frontmatter_field(dest_path, "agent", role)

    log_file = vault_path / "Logs" / "actions.jsonl"
    log_operation(
        log_file,
        component="claim-move",
        action="claim",
        status="success",
        detail=f"Claimed: {source_path.name} → In_Progress/{role}/",
        agent=role,
        correlation_id=corr_id,
    )
    logger.info(f"Claimed: {source_path.name} → In_Progress/{role}/")
    return dest_path


def complete_file(in_progress_path: Path, destination_folder: str,
                  vault_path: Path, **frontmatter_updates) -> Path:
    """Move a claimed file to its next destination folder.

    Args:
        in_progress_path: Path to the file in In_Progress/<role>/.
        destination_folder: Target folder relative to vault root
            (e.g., 'Pending_Approval/gmail', 'Done', 'Rejected').
        vault_path: Root path of the vault.
        **frontmatter_updates: Fields to update in frontmatter (e.g., status='done').

    Returns:
        New path in the destination folder.
    """
    dest_dir = vault_path / destination_folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / in_progress_path.name

    # Update frontmatter before moving
    for key, value in frontmatter_updates.items():
        _update_frontmatter_field(in_progress_path, key, value)

    # Read correlation_id before move (T038, FR-019)
    corr_id = ""
    try:
        fm = _read_frontmatter(in_progress_path)
        corr_id = fm.get("correlation_id", "")
    except Exception:
        pass

    os.rename(in_progress_path, dest_path)

    role = os.environ.get("FTE_ROLE", "unknown")
    log_file = vault_path / "Logs" / "actions.jsonl"
    log_operation(
        log_file,
        component="claim-move",
        action="complete",
        status="success",
        detail=f"Completed: {in_progress_path.name} → {destination_folder}/",
        agent=role,
        correlation_id=corr_id,
    )
    logger.info(f"Completed: {in_progress_path.name} → {destination_folder}/")
    return dest_path


def scan_needs_action(vault_path: Path, domain: str | None = None) -> list[Path]:
    """List files in Needs_Action/<domain>/ sorted by creation timestamp.

    Args:
        vault_path: Root path of the vault.
        domain: Optional domain subfolder ('gmail', 'whatsapp', 'scheduler', 'manual').
            If None, scans all domain subfolders and the root Needs_Action/.

    Returns:
        List of Path objects sorted by creation timestamp from frontmatter.
    """
    needs_action_root = vault_path / "Needs_Action"
    files = []

    if domain:
        scan_dirs = [needs_action_root / domain]
    else:
        # Scan root and all subfolders
        scan_dirs = [needs_action_root]
        if needs_action_root.exists():
            scan_dirs.extend(
                d for d in needs_action_root.iterdir() if d.is_dir()
            )

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        for f in scan_dir.iterdir():
            if f.is_file() and f.suffix == ".md":
                files.append(f)

    # Sort by creation timestamp from frontmatter
    def _get_created(path: Path) -> str:
        try:
            fm = _read_frontmatter(path)
            return fm.get("created", "")
        except Exception:
            return ""

    files.sort(key=_get_created)
    return files


def _read_frontmatter(file_path: Path) -> dict:
    """Read YAML frontmatter from a markdown file."""
    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}


def _update_frontmatter_field(file_path: Path, key: str, value: str) -> None:
    """Update a single field in a file's YAML frontmatter.

    If the key exists, replaces its value. If not, adds it before the
    closing ---. Preserves the rest of the file content.
    """
    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return

    parts = content.split("---", 2)
    if len(parts) < 3:
        return

    fm_text = parts[1]
    body = parts[2]

    # Check if key already exists
    lines = fm_text.strip().split("\n")
    key_found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            # Quote value if it contains special chars
            str_val = str(value)
            if any(c in str_val for c in (":", "#", "[", "]", "{", "}")):
                str_val = f'"{str_val}"'
            lines[i] = f"{key}: {str_val}"
            key_found = True
            break

    if not key_found:
        str_val = str(value)
        if any(c in str_val for c in (":", "#", "[", "]", "{", "}")):
            str_val = f'"{str_val}"'
        lines.append(f"{key}: {str_val}")

    new_content = "---\n" + "\n".join(lines) + "\n---" + body
    atomic_write(file_path, new_content)
