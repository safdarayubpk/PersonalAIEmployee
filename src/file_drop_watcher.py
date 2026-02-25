"""Watchdog-based filesystem watcher for the AI Employee vault.

Monitors a drop folder for new files and creates metadata .md files
in Needs_Action/ with YAML frontmatter. Uses PID lock to ensure
only one watcher instance runs at a time.

Usage:
    python src/file_drop_watcher.py
    python src/file_drop_watcher.py --drop-folder ~/Desktop/DropForAI
    python src/file_drop_watcher.py --vault-path /custom/vault
"""

import argparse
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Add parent dir to path so we can import vault_helpers
sys.path.insert(0, str(Path(__file__).resolve().parent))

from vault_helpers import (
    atomic_write,
    generate_frontmatter,
    log_error,
    log_operation,
    resolve_vault_path,
)

# Defaults
DEFAULT_DROP_FOLDER = "~/Desktop/DropForAI"
COMPONENT = "file-drop-watcher"
DEBOUNCE_SECONDS = 0.5


class DropHandler(FileSystemEventHandler):
    """Handle file creation events in the drop folder.

    Creates a Needs_Action metadata .md file for each new file detected.
    Ignores directory creation events and applies debounce filtering.
    """

    def __init__(self, vault_root: Path) -> None:
        super().__init__()
        self.vault_root = vault_root
        self.log_file = vault_root / "Logs" / "vault_operations.jsonl"
        self._recent: dict[str, float] = {}

    def on_created(self, event) -> None:
        """Handle file creation events (FR-004)."""
        # Ignore directory creation (FR-004 AS4)
        if event.is_directory:
            return

        src_path = Path(event.src_path)

        # Debounce: skip if same file seen within 0.5s (research R1)
        now = time.monotonic()
        last_seen = self._recent.get(str(src_path), 0)
        if now - last_seen < DEBOUNCE_SECONDS:
            return
        self._recent[str(src_path)] = now

        try:
            self._create_needs_action(src_path)
        except Exception as e:
            # Log error and continue watching (FR-004 AS5)
            log_error(
                self.vault_root, COMPONENT, "create_metadata",
                f"Failed to process: {src_path.name}", e,
            )
            print(f"Error processing {src_path.name}: {e}")

    def _create_needs_action(self, src_path: Path) -> None:
        """Create a Needs_Action metadata file for a dropped file."""
        timestamp = datetime.now(timezone.utc)
        ts_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S")
        ts_filename = timestamp.strftime("%Y%m%d-%H%M%S")

        # Generate filename: dropped-{stem}-{YYYYMMDD-HHMMSS}.md
        original_stem = src_path.stem
        needs_action_name = f"dropped-{original_stem}-{ts_filename}.md"
        needs_action_path = self.vault_root / "Needs_Action" / needs_action_name

        # Get file info
        try:
            file_size = src_path.stat().st_size
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.0f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
        except OSError:
            size_str = "unknown"

        file_type = src_path.suffix or "no extension"

        # Generate frontmatter (6 fields per contracts/needs-action-format.md)
        frontmatter = generate_frontmatter(
            title=f"dropped-{original_stem}-{file_type.lstrip('.')}",
            created=ts_str,
            tier="bronze",
            source=COMPONENT,
            priority="routine",
            status="needs_action",
        )

        # Generate body sections
        body = f"""
## What happened

New file detected in drop folder: `{src_path.name}` ({size_str})

## Suggested action

Review and organize the dropped file.

## Context

- Original file: {src_path}
- File type: {file_type}
- File size: {size_str}
- Drop time: {ts_str}"""

        content = frontmatter + "\n" + body + "\n"

        # Write atomically (D4)
        atomic_write(needs_action_path, content)

        # Log success
        log_operation(
            self.log_file, COMPONENT, "write_file", "success",
            f"Created {needs_action_name}",
        )
        print(f"Created: Needs_Action/{needs_action_name}")


# --- PID Lock Management (FR-019, research R2) ---

def _pid_file_path(vault_root: Path) -> Path:
    """Return the PID lock file path."""
    return vault_root / "Logs" / "watcher.pid"


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it
        return True


def acquire_pid_lock(vault_root: Path) -> None:
    """Write PID lock file, exiting if another instance is running."""
    pid_path = _pid_file_path(vault_root)
    log_file = vault_root / "Logs" / "vault_operations.jsonl"

    if pid_path.exists():
        try:
            existing_pid = int(pid_path.read_text().strip())
        except (ValueError, OSError):
            existing_pid = -1

        if existing_pid > 0 and _is_pid_alive(existing_pid):
            print(f"Error: Watcher already running (PID: {existing_pid})")
            sys.exit(1)
        else:
            log_operation(
                log_file, COMPONENT, "pid_lock", "success",
                f"Stale PID file found (PID: {existing_pid}), overwriting",
            )

    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(str(os.getpid()))

    log_operation(
        log_file, COMPONENT, "pid_lock", "success",
        f"Acquired PID lock (PID: {os.getpid()})",
    )


def release_pid_lock(vault_root: Path) -> None:
    """Remove PID lock file on clean shutdown."""
    pid_path = _pid_file_path(vault_root)
    if pid_path.exists():
        pid_path.unlink()


# --- CLI and Main Entry Point (research R6) ---

def parse_args() -> argparse.Namespace:
    """Parse CLI arguments with env var fallbacks."""
    parser = argparse.ArgumentParser(
        description="Watch a drop folder and create Needs_Action metadata files",
    )
    parser.add_argument(
        "--drop-folder",
        default=os.environ.get("DROP_FOLDER", DEFAULT_DROP_FOLDER),
        help="Folder to watch for new files (default: DROP_FOLDER env or ~/Desktop/DropForAI)",
    )
    parser.add_argument(
        "--vault-path",
        default=None,
        help="Vault root path (default: VAULT_PATH env or /home/safdarayub/Documents/AI_Employee_Vault)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for the file drop watcher."""
    args = parse_args()

    # Resolve vault path: CLI > env > default
    if args.vault_path:
        os.environ["VAULT_PATH"] = args.vault_path
    vault_root = resolve_vault_path()

    # Validate vault exists
    if not vault_root.exists():
        print(f"Error: Vault not found at {vault_root}")
        print("Run 'python src/setup_vault.py' first to initialize the vault.")
        sys.exit(1)

    # Resolve drop folder
    drop_folder = Path(args.drop_folder).expanduser().resolve()

    # Create drop folder if needed (edge case from spec)
    if not drop_folder.exists():
        drop_folder.mkdir(parents=True, exist_ok=True)
        log_file = vault_root / "Logs" / "vault_operations.jsonl"
        log_operation(
            log_file, COMPONENT, "create_folder", "success",
            f"Created drop folder: {drop_folder}",
        )
        print(f"Warning: Created drop folder at {drop_folder}")

    # Acquire PID lock (FR-019)
    acquire_pid_lock(vault_root)

    # Set up signal handlers for clean shutdown
    observer = Observer()

    def shutdown_handler(signum, frame):
        print("\nShutting down watcher...")
        observer.stop()
        release_pid_lock(vault_root)
        log_file = vault_root / "Logs" / "vault_operations.jsonl"
        log_operation(
            log_file, COMPONENT, "shutdown", "success",
            "Clean shutdown via signal",
        )
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    # Start watching
    handler = DropHandler(vault_root)
    observer.schedule(handler, str(drop_folder), recursive=False)
    observer.start()

    log_file = vault_root / "Logs" / "vault_operations.jsonl"
    log_operation(
        log_file, COMPONENT, "startup", "success",
        f"Watching {drop_folder} for new files",
    )
    print(f"Watching {drop_folder} for new files...")

    try:
        observer.join()
    except KeyboardInterrupt:
        shutdown_handler(None, None)


if __name__ == "__main__":
    main()
