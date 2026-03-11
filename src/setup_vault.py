"""Idempotent vault initialization script.

Creates the AI Employee Vault directory structure with 7 folders,
Dashboard.md, and Company_Handbook.md. Safe to re-run — skips
existing items and logs all actions.

Usage:
    python src/setup_vault.py
    VAULT_PATH=/custom/path python src/setup_vault.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent dir to path so we can import vault_helpers
sys.path.insert(0, str(Path(__file__).resolve().parent))

from vault_helpers import (
    resolve_vault_path,
    atomic_write,
    log_operation,
)

# Base vault folders (Bronze-Gold)
VAULT_FOLDERS = [
    "Inbox",
    "Needs_Action",
    "Done",
    "Pending_Approval",
    "Approved",
    "Plans",
    "Logs",
    "Briefings",
]

# Additional Platinum-tier folders (FR-020, FR-021, FR-022)
# Only created when FTE_ROLE is set (backward compat — FR-030)
PLATINUM_FOLDERS = [
    "Needs_Action/gmail",
    "Needs_Action/whatsapp",
    "Needs_Action/scheduler",
    "Needs_Action/manual",
    "In_Progress/cloud",
    "In_Progress/local",
    "Pending_Approval/gmail",
    "Pending_Approval/social",
    "Pending_Approval/odoo",
    "Pending_Approval/general",
    "Updates",
    "Rejected",
]

# Template directory relative to this script
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "vault_content"


def setup_vault() -> None:
    """Initialize the vault with required folders and files."""
    vault_root = resolve_vault_path()
    log_file = vault_root / "Logs" / "vault_operations.jsonl"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    folders_created = 0
    files_created = 0

    # Create vault root if needed
    if not vault_root.exists():
        vault_root.mkdir(parents=True, exist_ok=True)
        log_operation(log_file, "setup-vault", "create_folder", "success",
                      f"Created vault root: {vault_root}")

    # Create base folders (FR-001)
    for folder_name in VAULT_FOLDERS:
        folder_path = vault_root / folder_name
        if folder_path.exists():
            log_operation(log_file, "setup-vault", "create_folder", "skipped",
                          f"Folder already exists: {folder_name}/")
        else:
            folder_path.mkdir(parents=True, exist_ok=True)
            log_operation(log_file, "setup-vault", "create_folder", "success",
                          f"Created folder: {folder_name}/")
            folders_created += 1

    # Create Platinum folders only if FTE_ROLE is set (FR-020, FR-021, FR-022, FR-030)
    import os
    fte_role = os.environ.get("FTE_ROLE", "").strip().lower()
    if fte_role in ("cloud", "local"):
        for folder_name in PLATINUM_FOLDERS:
            folder_path = vault_root / folder_name
            if folder_path.exists():
                log_operation(log_file, "setup-vault", "create_folder", "skipped",
                              f"Platinum folder already exists: {folder_name}/")
            else:
                folder_path.mkdir(parents=True, exist_ok=True)
                log_operation(log_file, "setup-vault", "create_folder", "success",
                              f"Created Platinum folder: {folder_name}/")
                folders_created += 1

    # Create Dashboard.md (FR-002)
    dashboard_path = vault_root / "Dashboard.md"
    if dashboard_path.exists():
        log_operation(log_file, "setup-vault", "create_file", "skipped",
                      "File already exists: Dashboard.md")
    else:
        template = (TEMPLATE_DIR / "dashboard-template.md").read_text(encoding="utf-8")
        content = template.replace("{{CREATED_TIMESTAMP}}", timestamp)
        atomic_write(dashboard_path, content)
        log_operation(log_file, "setup-vault", "create_file", "success",
                      "Created file: Dashboard.md")
        files_created += 1

    # Create Company_Handbook.md (FR-003)
    handbook_path = vault_root / "Company_Handbook.md"
    if handbook_path.exists():
        log_operation(log_file, "setup-vault", "create_file", "skipped",
                      "File already exists: Company_Handbook.md")
    else:
        template = (TEMPLATE_DIR / "company-handbook.md").read_text(encoding="utf-8")
        content = template.replace("{{CREATED_TIMESTAMP}}", timestamp)
        atomic_write(handbook_path, content)
        log_operation(log_file, "setup-vault", "create_file", "success",
                      "Created file: Company_Handbook.md")
        files_created += 1

    print(f"{folders_created} folders and {files_created} files created")

    if folders_created == 0 and files_created == 0:
        print("Vault already fully initialized — no changes made")


if __name__ == "__main__":
    setup_vault()
