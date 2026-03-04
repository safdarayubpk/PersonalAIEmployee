"""APScheduler daemon for the AI Employee vault.

Schedules recurring tasks and creates Needs_Action .md files at trigger time.
Runs as a background daemon with PID lock and clean shutdown.

Usage:
    python scheduler_daemon.py                              # Start daemon
    python scheduler_daemon.py --config config/schedules.json
    python scheduler_daemon.py --add --task-name "daily-ceo-briefing" --interval daily --time "07:30"
    python scheduler_daemon.py --list                       # List active jobs

Requirements:
    pip install apscheduler
"""

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    print("Error: apscheduler not installed.")
    print("Run: pip install apscheduler")
    sys.exit(1)

DEFAULT_VAULT_PATH = "/home/safdarayub/Documents/AI_Employee_Vault"
COMPONENT = "daily-scheduler"
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT",
                    Path(__file__).resolve().parent.parent.parent.parent.parent))
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from vault_helpers import redact_sensitive, generate_correlation_id

DEFAULT_CONFIG = PROJECT_ROOT / "config" / "schedules.json"
DEFAULT_TIMEZONE = "Asia/Karachi"
MISFIRE_GRACE = 3600


def log_entry(log_file: Path, **fields) -> None:
    """Append a JSON line to the log file (sensitive fields redacted)."""
    entry = {"timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"), **fields}
    entry = redact_sensitive(entry)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def create_needs_action(job_id: str, description: str, priority: str,
                        schedule_str: str, tz: str, next_run: str,
                        vault_root: Path) -> str:
    """Create a Needs_Action .md file for a triggered scheduled task."""
    ts = datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
    ts_filename = ts.strftime("%Y%m%d-%H%M%S")

    filename = f"scheduled-{job_id}-{ts_filename}.md"
    filepath = vault_root / "Needs_Action" / filename

    corr_id = generate_correlation_id()

    content = f"""---
title: "scheduled-{job_id}"
created: "{ts_str}"
tier: silver
source: daily-scheduler
priority: "{priority}"
status: needs_action
type: scheduled
task: "{job_id}"
schedule: "{schedule_str}"
correlation_id: "{corr_id}"
---

## What happened

Scheduled task triggered: {description}

## Suggested action

Execute the scheduled task as defined.

## Context

- Task: {job_id}
- Schedule: {schedule_str}
- Timezone: {tz}
- Next run: {next_run}
"""

    tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(content, encoding="utf-8")
    os.rename(tmp_path, filepath)

    return filename


def make_trigger_callback(job_config: dict, scheduler, vault_root: Path, log_file: Path):
    """Create a callback for a scheduled job trigger."""
    def callback():
        job_id = job_config.get("id") or job_config.get("task_name", "unknown")
        description = job_config.get("description", job_id)
        priority = job_config.get("priority", "sensitive")
        tz = job_config.get("timezone", DEFAULT_TIMEZONE)

        schedule_str = job_config.get("cron", "")
        if not schedule_str:
            interval = job_config.get("interval", "daily")
            time_str = job_config.get("time", "09:00")
            day = job_config.get("day", "")
            if interval == "weekly" and day:
                schedule_str = f"weekly {day} at {time_str}"
            else:
                schedule_str = f"daily at {time_str}"

        # Get next run time
        job = scheduler.get_job(job_id)
        next_run = str(job.next_run_time) if job and job.next_run_time else "N/A"

        try:
            filename = create_needs_action(
                job_id, description, priority, schedule_str, tz, next_run, vault_root,
            )
            log_entry(log_file, component=COMPONENT, action="trigger", status="success",
                      job_id=job_id, description=description,
                      needs_action_file=filename, next_run=next_run,
                      detail=f"Scheduled task triggered, created Needs_Action file")
            print(f"[TRIGGER] {job_id}: Created Needs_Action/{filename}")
        except Exception as e:
            log_entry(log_file, component=COMPONENT, action="trigger", status="failure",
                      job_id=job_id, description=description, error=str(e),
                      detail=f"Failed to create Needs_Action file: {e}")
            print(f"[ERROR] {job_id}: {e}")

    return callback


def build_trigger(job_config: dict) -> CronTrigger:
    """Build an APScheduler CronTrigger from job config."""
    tz = job_config.get("timezone", DEFAULT_TIMEZONE)

    if "cron" in job_config:
        return CronTrigger.from_crontab(job_config["cron"], timezone=tz)

    time_str = job_config.get("time", "09:00")
    parts = time_str.split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(f"hour must be 0-23, minute must be 0-59")
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid time '{time_str}': {e}")

    interval = job_config.get("interval", "daily")

    if interval == "weekly":
        day = job_config.get("day", "monday").lower()[:3]
        return CronTrigger(day_of_week=day, hour=hour, minute=minute, timezone=tz)

    # daily
    return CronTrigger(hour=hour, minute=minute, timezone=tz)


def load_config(config_path: Path) -> dict:
    """Load schedule config, creating default if missing."""
    if not config_path.exists():
        default = {
            "jobs": [],
            "defaults": {
                "timezone": DEFAULT_TIMEZONE,
                "priority": "sensitive",
                "enabled": True,
            },
        }
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        print(f"Created default config: {config_path}")
        return default

    return json.loads(config_path.read_text(encoding="utf-8"))


def add_job_to_config(config_path: Path, task_name: str, description: str,
                      interval: str | None, day: str | None, time_str: str | None,
                      cron: str | None, priority: str, tz: str) -> dict:
    """Add a new job to the config file."""
    config = load_config(config_path)

    # Check for duplicate
    for job in config["jobs"]:
        if (job.get("id") or job.get("task_name")) == task_name:
            print(f"Error: Job '{task_name}' already exists. Remove it first or use a different name.")
            sys.exit(1)

    job = {
        "id": task_name,
        "description": description,
        "timezone": tz,
        "priority": priority,
        "enabled": True,
    }

    if cron:
        job["cron"] = cron
    elif interval == "weekly":
        job["interval"] = "weekly"
        job["day"] = day or "monday"
        job["time"] = time_str or "09:00"
    else:
        job["interval"] = "daily"
        job["time"] = time_str or "09:00"

    config["jobs"].append(job)
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    return job


def list_jobs(config_path: Path) -> None:
    """List all configured jobs."""
    config = load_config(config_path)
    jobs = config.get("jobs", [])

    if not jobs:
        print("No scheduled jobs configured.")
        return

    print(f"\n{'ID':<25} {'Schedule':<25} {'Priority':<10} {'Enabled':<8} Description")
    print("-" * 100)

    for job in jobs:
        if "cron" in job:
            sched = f"cron: {job['cron']}"
        elif job.get("interval") == "weekly":
            sched = f"weekly {job.get('day', 'mon')} {job.get('time', '09:00')}"
        else:
            sched = f"daily {job.get('time', '09:00')}"

        enabled = "yes" if job.get("enabled", True) else "no"
        job_id = job.get("id") or job.get("task_name", "unknown")
        print(f"{job_id:<25} {sched:<25} {job.get('priority', 'sensitive'):<10} {enabled:<8} {job.get('description', '')}")

    print(f"\nTotal: {len(jobs)} job(s)")


def run_daemon(config_path: Path, vault_root: Path) -> None:
    """Start the scheduler daemon."""
    log_file = vault_root / "Logs" / "scheduler.jsonl"
    pid_file = vault_root / "Logs" / "scheduler.pid"

    # PID lock
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    if pid_file.exists():
        try:
            existing_pid = int(pid_file.read_text().strip())
            os.kill(existing_pid, 0)
            print(f"Error: Scheduler already running (PID: {existing_pid})")
            sys.exit(1)
        except ProcessLookupError:
            pid_file.unlink()
        except ValueError:
            pid_file.unlink()
    pid_file.write_text(str(os.getpid()))

    config = load_config(config_path)
    scheduler = BackgroundScheduler(timezone=config.get("defaults", {}).get("timezone", DEFAULT_TIMEZONE))

    jobs = [j for j in config.get("jobs", []) if j.get("enabled", True)]

    if not jobs:
        print("No enabled jobs to schedule. Add jobs with --add or edit config.")
        pid_file.unlink()
        sys.exit(0)

    for job_config in jobs:
        trigger = build_trigger(job_config)
        callback = make_trigger_callback(job_config, scheduler, vault_root, log_file)
        scheduler.add_job(callback, trigger, id=job_config.get("id") or job_config.get("task_name", "unknown"),
                          misfire_grace_time=MISFIRE_GRACE, coalesce=True)

    scheduler.start()

    log_entry(log_file, component=COMPONENT, action="startup", status="success",
              jobs_registered=len(jobs),
              detail=f"Scheduler started with {len(jobs)} job(s)")

    print(f"Scheduler started with {len(jobs)} job(s) (PID: {os.getpid()})")
    for job in scheduler.get_jobs():
        next_run = str(job.next_run_time) if job.next_run_time else "N/A"
        print(f"  {job.id}: next run {next_run}")
        confirmation = {"scheduled": True, "job_id": job.id, "next_run": next_run}
        print(f"  {json.dumps(confirmation)}")

    def shutdown(signum=None, frame=None):
        print("\nShutting down scheduler...")
        scheduler.shutdown(wait=False)
        if pid_file.exists():
            pid_file.unlink()
        log_entry(log_file, component=COMPONENT, action="shutdown", status="success",
                  detail="Clean shutdown via signal")
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        shutdown()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="APScheduler daemon for AI Employee vault")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG),
                        help="Path to schedules.json config file")
    parser.add_argument("--vault-path", default=None, help="Vault root path override")

    # Add job mode
    parser.add_argument("--add", action="store_true", help="Add a new scheduled job")
    parser.add_argument("--task-name", default=None, help="Job ID/name (required with --add)")
    parser.add_argument("--description", default="", help="Human-readable description")
    parser.add_argument("--interval", choices=["daily", "weekly"], default=None,
                        help="Interval type")
    parser.add_argument("--day", default=None,
                        help="Day of week for weekly jobs (monday, tuesday, ...)")
    parser.add_argument("--time", default="09:00", help="Time in HH:MM format (default: 09:00)")
    parser.add_argument("--cron", default=None, help="Cron expression (overrides --interval)")
    parser.add_argument("--priority", default="sensitive",
                        choices=["routine", "sensitive", "critical"],
                        help="Task priority (default: sensitive)")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE, help="Timezone (default: Asia/Karachi)")

    # List mode
    parser.add_argument("--list", action="store_true", help="List all configured jobs")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    vault_path = args.vault_path or os.environ.get("VAULT_PATH", DEFAULT_VAULT_PATH)
    vault_root = Path(vault_path)
    config_path = Path(args.config)

    if not vault_root.exists():
        print(f"Error: Vault not found at {vault_root}")
        sys.exit(1)

    if args.list:
        list_jobs(config_path)
        return

    if args.add:
        if not args.task_name:
            print("Error: --task-name is required with --add")
            sys.exit(1)

        job = add_job_to_config(
            config_path, args.task_name, args.description or args.task_name,
            args.interval, args.day, args.time, args.cron,
            args.priority, args.timezone,
        )
        print(f"Added job: {json.dumps(job, indent=2)}")

        log_file = vault_root / "Logs" / "scheduler.jsonl"
        log_entry(log_file, component=COMPONENT, action="add_job", status="success",
                  job_id=args.task_name, detail=f"Added scheduled job: {args.task_name}")
        return

    run_daemon(config_path, vault_root)


if __name__ == "__main__":
    main()
