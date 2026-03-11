from __future__ import annotations

"""Git-based vault synchronization service for Platinum tier.

Runs a pull → commit → push loop at a configurable interval to keep
cloud and local vaults in sync via a private GitHub repository.

Usage:
    FTE_ROLE=cloud VAULT_PATH=/path/to/vault python src/git_sync.py

Environment variables:
    FTE_ROLE                   - Required: 'cloud' or 'local'
    VAULT_PATH                 - Required: absolute path to vault
    GIT_SYNC_INTERVAL_SECONDS  - Optional: sync interval (default 60)
"""

import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from role_gate import validate_startup
from vault_helpers import log_operation, resolve_vault_path, atomic_write, generate_frontmatter
from dashboard_merger import merge_updates

logger = logging.getLogger(__name__)

MAX_PUSH_RETRIES = 3

# Secrets patterns for cloud-side Layer 3 audit (FR-016, ADR-0012)
SECRETS_PATTERNS = (".env", ".session", ".token", ".key", ".pem")
SECRETS_DIRS = ("credentials", "secrets")


class SyncResult:
    """Result of a single sync cycle."""

    def __init__(self, pulled: bool = False, pushed: bool = False,
                 files_changed: int = 0, conflict: bool = False,
                 error: str | None = None):
        self.pulled = pulled
        self.pushed = pushed
        self.files_changed = files_changed
        self.conflict = conflict
        self.error = error

    @property
    def success(self) -> bool:
        return not self.conflict and self.error is None


def _run_git(args: list[str], cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    cmd = ["git"] + args
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )


def _log_sync(vault_path: Path, action: str, status: str, detail: str,
              files_changed: int = 0, retry_count: int = 0) -> None:
    """Log a sync operation to Logs/sync.jsonl."""
    role = os.environ.get("FTE_ROLE", "unknown")
    log_file = vault_path / "Logs" / "sync.jsonl"
    log_operation(
        log_file,
        component="git-sync",
        action=action,
        status=status,
        detail=detail,
        agent=role,
        files_changed=files_changed,
        retry_count=retry_count,
    )


def _create_manual_alert(vault_path: Path, title: str, detail: str) -> None:
    """Create a Needs_Action/manual/ file for human intervention."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    safe_title = title.lower().replace(" ", "-").replace("/", "-")[:50]
    filename = f"{safe_title}-{timestamp.replace(':', '-')}.md"
    alert_dir = vault_path / "Needs_Action" / "manual"
    alert_dir.mkdir(parents=True, exist_ok=True)

    role = os.environ.get("FTE_ROLE", "unknown")
    frontmatter = generate_frontmatter(
        title=safe_title,
        created=timestamp,
        tier="platinum",
        source="git-sync",
        priority="sensitive",
        status="needs_action",
        agent=role,
    )
    content = f"{frontmatter}\n\n## What happened\n\n{detail}\n\n## Suggested action\n\nManual intervention required.\n"
    alert_path = alert_dir / filename
    atomic_write(alert_path, content)


def audit_secrets_on_cloud(vault_path: Path) -> list[str]:
    """Scan vault directory for files matching secrets patterns (FR-016).

    Only runs when FTE_ROLE=cloud. Returns list of violating file paths.
    If violations found, logs CRITICAL event and creates manual alert.
    """
    role = os.environ.get("FTE_ROLE", "")
    if role != "cloud":
        return []

    violations = []
    for root, dirs, files in os.walk(vault_path):
        # Check directory names
        rel_root = Path(root).relative_to(vault_path)
        for d in dirs:
            if d.lower() in SECRETS_DIRS:
                violations.append(str(rel_root / d))
        # Check file names
        for f in files:
            f_lower = f.lower()
            if f_lower == ".env" or any(f_lower.endswith(pat) for pat in SECRETS_PATTERNS[1:]):
                violations.append(str(rel_root / f))

    if violations:
        detail = (
            f"CRITICAL SECURITY: Secrets-matching files detected on cloud VM:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )
        logger.critical(detail)
        log_file = vault_path / "Logs" / "sync.jsonl"
        log_operation(
            log_file,
            component="git-sync",
            action="secrets_audit",
            status="failure",
            detail=detail,
            agent="cloud",
        )
        _create_manual_alert(vault_path, "secrets-detected-on-cloud", detail)

    return violations


def sync_cycle(vault_path: Path) -> SyncResult:
    """Execute one complete pull → commit → push cycle.

    Steps:
        1. git stash (protect uncommitted work)
        2. git pull --rebase origin main
        3. git stash pop (if stashed)
        4. git add . (respects .gitignore)
        5. git commit (if changes)
        6. git push (with retries)

    Returns:
        SyncResult with details of what happened.
    """
    role = os.environ.get("FTE_ROLE", "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    # Step 1: Stash any uncommitted changes
    stash_result = _run_git(["stash"], cwd=vault_path)
    has_stash = "No local changes to save" not in stash_result.stdout

    # Step 2: Pull with rebase
    pull_result = _run_git(["pull", "--rebase", "origin", "main"], cwd=vault_path)
    if pull_result.returncode != 0:
        # Check if it's a network error (offline) vs merge conflict
        stderr = pull_result.stderr.lower()
        if "could not resolve" in stderr or "unable to access" in stderr or "connection" in stderr:
            _log_sync(vault_path, "pull", "failure", f"Network offline: {pull_result.stderr.strip()}")
            # Pop stash back if we stashed
            if has_stash:
                _run_git(["stash", "pop"], cwd=vault_path)
            return SyncResult(error="network_offline")

        # Rebase conflict — abort and report
        _run_git(["rebase", "--abort"], cwd=vault_path)
        if has_stash:
            _run_git(["stash", "pop"], cwd=vault_path)

        conflict_detail = f"Git rebase conflict: {pull_result.stderr.strip()}"
        _log_sync(vault_path, "conflict", "failure", conflict_detail)

        # Log to sync-conflicts.jsonl
        conflict_log = vault_path / "Logs" / "sync-conflicts.jsonl"
        log_operation(
            conflict_log,
            component="git-sync",
            action="rebase_conflict",
            status="failure",
            detail=conflict_detail,
            agent=role,
        )
        _create_manual_alert(vault_path, "git-merge-conflict", conflict_detail)
        return SyncResult(conflict=True, error=conflict_detail)

    _log_sync(vault_path, "pull", "success", "Pull --rebase successful")

    # Step 3: Pop stash
    if has_stash:
        pop_result = _run_git(["stash", "pop"], cwd=vault_path)
        if pop_result.returncode != 0:
            _log_sync(vault_path, "stash_pop", "failure", pop_result.stderr.strip())

    # Step 3b: Local agent merges cloud Updates/ into Dashboard.md (T032, FR-013)
    if role != "cloud":
        try:
            merged_count = merge_updates(vault_path)
            if merged_count > 0:
                _log_sync(vault_path, "merge_updates", "success",
                          f"Merged {merged_count} cloud update(s) into Dashboard.md",
                          files_changed=merged_count)
        except Exception as e:
            _log_sync(vault_path, "merge_updates", "failure", str(e))

    # Step 4: Stage changes
    _run_git(["add", "."], cwd=vault_path)

    # Step 5: Check for staged changes
    status_result = _run_git(["status", "--porcelain"], cwd=vault_path)
    staged_files = [line for line in status_result.stdout.strip().split("\n") if line.strip()]

    if not staged_files:
        _log_sync(vault_path, "commit", "skipped", "No changes to commit")
        return SyncResult(pulled=True)

    files_changed = len(staged_files)
    commit_msg = f"sync: {role} {timestamp} [{files_changed} files]"
    commit_result = _run_git(["commit", "-m", commit_msg], cwd=vault_path)

    if commit_result.returncode != 0:
        _log_sync(vault_path, "commit", "failure", commit_result.stderr.strip())
        return SyncResult(pulled=True, error=commit_result.stderr.strip())

    _log_sync(vault_path, "commit", "success", commit_msg, files_changed=files_changed)

    # Step 6: Push with retries
    for attempt in range(MAX_PUSH_RETRIES):
        push_result = _run_git(["push", "origin", "main"], cwd=vault_path)
        if push_result.returncode == 0:
            _log_sync(vault_path, "push", "success", "Push successful",
                      files_changed=files_changed, retry_count=attempt)
            return SyncResult(pulled=True, pushed=True, files_changed=files_changed)

        # Push failed — try pull --rebase then push again
        _log_sync(vault_path, "push", "failure",
                  f"Push failed (attempt {attempt + 1}/{MAX_PUSH_RETRIES}): {push_result.stderr.strip()}",
                  retry_count=attempt)
        retry_pull = _run_git(["pull", "--rebase", "origin", "main"], cwd=vault_path)
        if retry_pull.returncode != 0:
            _run_git(["rebase", "--abort"], cwd=vault_path)

    # All retries exhausted
    detail = f"Push failed after {MAX_PUSH_RETRIES} retries"
    _log_sync(vault_path, "push", "failure", detail, retry_count=MAX_PUSH_RETRIES)
    _create_manual_alert(vault_path, "git-push-failed", detail)
    return SyncResult(pulled=True, files_changed=files_changed, error=detail)


def run_sync_loop(vault_path: Path, interval: int = 60) -> None:
    """Run the sync loop daemon.

    Pulls, commits, and pushes on the configured interval.
    Runs audit_secrets_on_cloud() on startup (FR-016).
    """
    role = validate_startup()
    logger.info(f"Git sync daemon starting: role={role}, interval={interval}s, vault={vault_path}")

    # Run secrets audit on startup (Layer 3 defense, FR-016)
    audit_secrets_on_cloud(vault_path)

    while True:
        try:
            result = sync_cycle(vault_path)
            if result.success:
                logger.debug(f"Sync cycle complete: pushed={result.pushed}, files={result.files_changed}")
            else:
                logger.warning(f"Sync cycle issue: error={result.error}, conflict={result.conflict}")
        except Exception as e:
            logger.error(f"Sync cycle crashed: {e}")
            _log_sync(vault_path, "cycle", "failure", str(e))

        time.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    vault = resolve_vault_path()
    interval = int(os.environ.get("GIT_SYNC_INTERVAL_SECONDS", "60"))
    run_sync_loop(vault, interval)
