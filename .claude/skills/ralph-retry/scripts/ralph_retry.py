"""Ralph Wiggum persistence loop for the AI Employee vault.

Retries failed tasks with exponential backoff until success or max
iterations. Usable as both a CLI tool and an importable Python module.

CLI Usage:
    python ralph_retry.py --command "python some_task.py" --description "Task name"
    python ralph_retry.py --command "..." --max-retries 10 --backoff-base 3
    python ralph_retry.py --command "..." --description "..." --vault-path /custom/vault

Module Usage:
    from ralph_retry import ralph_loop
    result = ralph_loop(task=my_callable, task_description="Do the thing")

Requirements:
    No external dependencies (stdlib only).
"""

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DEFAULT_VAULT_PATH = "/home/safdarayub/Documents/AI_Employee_Vault"
COMPONENT = "ralph-retry"
_PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT",
                     Path(__file__).resolve().parent.parent.parent.parent.parent))
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
from vault_helpers import redact_sensitive
MAX_RETRIES_HARD_CAP = 20
BACKOFF_MAX_SECONDS = 300
SUBPROCESS_TIMEOUT = 60

# Errors that should never be retried
NO_RETRY_ERRORS = (KeyboardInterrupt, SystemExit, PermissionError)


class NonRetryableError(RuntimeError):
    """Raised when a command exits with code 2, indicating no retry should occur."""
    pass


def _generate_task_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    short_uuid = uuid.uuid4().hex[:4]
    return f"ralph-{ts}-{short_uuid}"


def _log_entry(log_file: Path, **fields) -> None:
    entry = {"timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"), **fields}
    entry = redact_sensitive(entry)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _update_dashboard(vault_root: Path, task_description: str, success: bool,
                      attempts: int, max_retries: int, elapsed: float,
                      last_error: str | None) -> None:
    dashboard = vault_root / "Dashboard.md"
    if not dashboard.exists():
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    result_str = "Success" if success else "FAILED"
    attempts_str = f"{attempts} / {max_retries}"
    if not success:
        attempts_str += " (exhausted)"

    entry = f"\n### Ralph Retry — {ts}\n\n"
    entry += "| Metric | Value |\n|--------|-------|\n"
    entry += f"| Task | {task_description} |\n"
    entry += f"| Result | {result_str} |\n"
    entry += f"| Attempts | {attempts_str} |\n"
    entry += f"| Total time | {elapsed:.1f}s |\n"
    if not success and last_error:
        error_oneline = last_error.split("\n")[0][:100]
        entry += f"| Last error | {error_oneline} |\n"

    with open(dashboard, "a") as f:
        f.write(entry)


def ralph_loop(
    task: Callable[[], Any],
    task_description: str,
    max_retries: int = 15,
    backoff_base: int = 2,
    task_id: str | None = None,
    vault_path: str | None = None,
) -> dict:
    """Execute a callable with exponential backoff retry.

    Args:
        task: Callable to execute (no arguments). Raise exception to signal failure.
        task_description: Human-readable description for logs.
        max_retries: Max attempts (hard cap: 20).
        backoff_base: Base for exponential backoff in seconds (1-5).
        task_id: Unique ID for this retry session (auto-generated if None).
        vault_path: Override vault root path.

    Returns:
        Dict with success, attempts, error, task_id, total_elapsed_seconds, result.
    """
    vault_root = Path(vault_path or os.environ.get("VAULT_PATH", DEFAULT_VAULT_PATH))
    log_file = vault_root / "Logs" / "retry.jsonl"

    original_max = max_retries
    max_retries = min(max(max_retries, 1), MAX_RETRIES_HARD_CAP)
    backoff_base = min(max(backoff_base, 1), 5)

    if original_max > MAX_RETRIES_HARD_CAP:
        _log_entry(log_file, component=COMPONENT, action="clamp", status="warning",
                   detail=f"Max retries clamped from {original_max} to {MAX_RETRIES_HARD_CAP} (hard cap)")
    task_id = task_id or _generate_task_id()

    _log_entry(log_file, component=COMPONENT, action="start", status="success",
               task_id=task_id, task_description=task_description,
               max_retries=max_retries, backoff_base=backoff_base,
               detail=f"Starting ralph loop: {task_description}")

    start_time = time.monotonic()
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            result = task()
            elapsed = time.monotonic() - start_time

            _log_entry(log_file, component=COMPONENT, action="attempt", status="success",
                       task_id=task_id, task_description=task_description,
                       attempt=attempt, max_retries=max_retries,
                       total_elapsed_seconds=round(elapsed, 1),
                       detail=f"Attempt {attempt}/{max_retries} succeeded")

            _update_dashboard(vault_root, task_description, True,
                              attempt, max_retries, elapsed, None)

            return {
                "success": True,
                "attempts": attempt,
                "error": None,
                "task_id": task_id,
                "task_description": task_description,
                "total_elapsed_seconds": round(elapsed, 1),
                "result": result,
            }

        except NO_RETRY_ERRORS:
            raise

        except NonRetryableError as e:
            elapsed = time.monotonic() - start_time
            _log_entry(log_file, component=COMPONENT, action="abort", status="failure",
                       task_id=task_id, task_description=task_description,
                       attempt=attempt, max_retries=max_retries,
                       error=str(e), total_elapsed_seconds=round(elapsed, 1),
                       detail=f"Non-retryable error on attempt {attempt}, aborting")
            _update_dashboard(vault_root, task_description, False,
                              attempt, max_retries, elapsed, str(e))
            return {
                "success": False,
                "attempts": attempt,
                "error": str(e),
                "task_id": task_id,
                "task_description": task_description,
                "total_elapsed_seconds": round(elapsed, 1),
                "result": None,
                "aborted": True,
            }

        except Exception as e:
            last_error = str(e)
            tb = traceback.format_exc()
            backoff = min(backoff_base ** attempt, BACKOFF_MAX_SECONDS)

            _log_entry(log_file, component=COMPONENT, action="attempt", status="failure",
                       task_id=task_id, task_description=task_description,
                       attempt=attempt, max_retries=max_retries,
                       error=last_error, traceback=tb,
                       next_backoff_seconds=backoff if attempt < max_retries else None,
                       detail=f"Attempt {attempt}/{max_retries} failed"
                              + (f", retrying in {backoff}s" if attempt < max_retries else " (exhausted)"))

            if attempt < max_retries:
                time.sleep(backoff)

    elapsed = time.monotonic() - start_time

    _log_entry(log_file, component=COMPONENT, action="exhausted", status="failure",
               task_id=task_id, task_description=task_description,
               attempts=max_retries, total_elapsed_seconds=round(elapsed, 1),
               error=last_error,
               detail=f"All {max_retries} attempts exhausted")

    _update_dashboard(vault_root, task_description, False,
                      max_retries, max_retries, elapsed, last_error)

    return {
        "success": False,
        "attempts": max_retries,
        "error": last_error,
        "task_id": task_id,
        "task_description": task_description,
        "total_elapsed_seconds": round(elapsed, 1),
        "result": None,
    }


def _run_subprocess(command: str, timeout: int) -> str:
    """Run a shell command as a subprocess. Raises on non-zero exit.

    Exit code 2 raises NonRetryableError (immediate abort, no further retries).
    """
    proc = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        error_msg = proc.stderr.strip() or proc.stdout.strip() or f"Exit code {proc.returncode}"
        if proc.returncode == 2:
            raise NonRetryableError(error_msg)
        raise RuntimeError(error_msg)
    return proc.stdout.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ralph Wiggum persistence loop — retry with exponential backoff",
    )
    parser.add_argument("--command", required=True, help="Shell command to retry")
    parser.add_argument("--description", required=True, help="Human-readable task description")
    parser.add_argument("--max-retries", type=int, default=15, help="Max attempts (cap: 20)")
    parser.add_argument("--backoff-base", type=int, default=2, help="Backoff base in seconds (1-5)")
    parser.add_argument("--timeout", type=int, default=SUBPROCESS_TIMEOUT,
                        help="Timeout per attempt in seconds (default: 60)")
    parser.add_argument("--vault-path", default=None, help="Vault root path override")
    parser.add_argument("--task-id", default=None, help="Custom task ID")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    vault_path = args.vault_path or os.environ.get("VAULT_PATH", DEFAULT_VAULT_PATH)

    if not Path(vault_path).exists():
        print(f"Error: Vault not found at {vault_path}")
        sys.exit(1)

    print(f"Ralph Retry — {args.description}")
    print(f"Command: {args.command}")
    print(f"Max retries: {min(args.max_retries, MAX_RETRIES_HARD_CAP)}, "
          f"Backoff base: {min(max(args.backoff_base, 1), 5)}s")

    def task():
        return _run_subprocess(args.command, args.timeout)

    result = ralph_loop(
        task=task,
        task_description=args.description,
        max_retries=args.max_retries,
        backoff_base=args.backoff_base,
        task_id=args.task_id,
        vault_path=vault_path,
    )

    print(f"\n{'SUCCESS' if result['success'] else 'FAILED'} after {result['attempts']} attempt(s)")
    print(f"Total time: {result['total_elapsed_seconds']}s")
    if result["error"]:
        print(f"Last error: {result['error']}")
    if result["result"]:
        print(f"Output: {result['result'][:500]}")

    print(json.dumps(result, indent=2, default=str))

    if result["success"]:
        sys.exit(0)
    elif result.get("aborted"):
        sys.exit(2)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
