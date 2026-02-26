---
name: daily-scheduler
description: Schedules recurring tasks using APScheduler (daily CEO prep, weekly status check, custom intervals) and creates Needs_Action .md files at trigger time. Use when the user asks to "schedule a task", "set up daily briefing", "create recurring job", "schedule weekly report", "start scheduler", "add cron job", or when another skill needs time-based triggering. Also triggers on phrases like "every morning at 8am", "run daily", "weekly check", or "schedule processing". Requires APScheduler installed.
---

# Daily Scheduler

Schedule recurring tasks with APScheduler. At trigger time, creates a Needs_Action markdown file in the vault so the processing pipeline picks it up automatically.

**Vault root**: `/home/safdarayub/Documents/AI_Employee_Vault`
(override via `VAULT_PATH` env var)

## Dependencies

- `apscheduler` (v3.x)

Install:

```bash
pip install apscheduler
```

## Workflow

```
Load schedule config (config/schedules.json)
       │
       ├── Register jobs with APScheduler
       │     ├── Daily jobs → IntervalTrigger or CronTrigger
       │     ├── Weekly jobs → CronTrigger (day_of_week)
       │     └── Custom jobs → CronTrigger (full cron expression)
       │
       └── Run scheduler in background
              │
              ├── Trigger fires
              │     ├── Create Needs_Action .md with task details
              │     ├── Log to Logs/scheduler.jsonl
              │     └── Continue running
              │
              └── Loop until SIGTERM/SIGINT → Clean shutdown
```

## Usage

### Start the scheduler daemon

```bash
# Start with default config
python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py

# Custom config file
python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py --config config/schedules.json

# Custom vault path
python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py --vault-path /custom/vault
```

### Add a one-off schedule via CLI

```bash
# Daily CEO briefing at 7:30 AM
python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py \
  --add --task-name "daily-ceo-briefing" \
  --interval daily --time "07:30" \
  --description "Prepare Monday Morning CEO Briefing"

# Weekly status check every Monday at 9:00 AM
python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py \
  --add --task-name "weekly-status-check" \
  --interval weekly --day monday --time "09:00" \
  --description "Generate weekly team status report"

# Custom cron: every 6 hours
python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py \
  --add --task-name "inbox-sweep" \
  --cron "0 */6 * * *" \
  --description "Sweep Needs_Action for stale items"

# List active schedules
python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py --list
```

## Schedule Configuration

`config/schedules.json`:

```json
{
  "jobs": [
    {
      "id": "daily-ceo-briefing",
      "description": "Prepare Monday Morning CEO Briefing",
      "interval": "daily",
      "time": "07:30",
      "timezone": "Asia/Karachi",
      "priority": "high",
      "enabled": true
    },
    {
      "id": "weekly-status-check",
      "description": "Generate weekly team status report",
      "interval": "weekly",
      "day": "monday",
      "time": "09:00",
      "timezone": "Asia/Karachi",
      "priority": "medium",
      "enabled": true
    },
    {
      "id": "inbox-sweep",
      "description": "Sweep Needs_Action for stale items",
      "cron": "0 */6 * * *",
      "timezone": "Asia/Karachi",
      "priority": "low",
      "enabled": true
    }
  ],
  "defaults": {
    "timezone": "Asia/Karachi",
    "priority": "medium",
    "enabled": true
  }
}
```

## Step 1: Load and Register Jobs

1. Read `config/schedules.json` (create with defaults if missing)
2. For each enabled job, register with APScheduler:
   - `interval: "daily"` + `time` → `CronTrigger(hour=H, minute=M)`
   - `interval: "weekly"` + `day` + `time` → `CronTrigger(day_of_week=D, hour=H, minute=M)`
   - `cron: "..."` → `CronTrigger.from_crontab(expr)`
3. Log all registered jobs to `Logs/scheduler.jsonl`

## Step 2: Handle Trigger

When a scheduled job fires:

1. Generate a Needs_Action markdown file
2. Write to `Needs_Action/` using atomic write

**Filename**: `scheduled-<task-id>-<YYYYMMDD-HHMMSS>.md`

**Content**:

```markdown
---
title: "scheduled-<task-id>"
created: "<ISO timestamp>"
tier: silver
source: daily-scheduler
priority: "<from config>"
status: needs_action
type: scheduled
task: "<task-id>"
schedule: "<interval or cron>"
---

## What happened

Scheduled task triggered: <description>

## Suggested action

Execute the scheduled task as defined.

## Context

- Task: <task-id>
- Schedule: <daily at 07:30 / weekly Monday 09:00 / cron expression>
- Timezone: <timezone>
- Next run: <next trigger time>
```

3. Log the trigger to `Logs/scheduler.jsonl`

## Step 3: Output Confirmation

After registering or triggering a job, output:

```json
{
  "scheduled": true,
  "job_id": "daily-ceo-briefing",
  "next_run": "2026-02-26T07:30:00+05:00",
  "interval": "daily",
  "timezone": "Asia/Karachi"
}
```

## Logging

Append one JSON line per event to `Logs/scheduler.jsonl`:

```json
{
  "timestamp": "2026-02-25T07:30:00",
  "component": "daily-scheduler",
  "action": "trigger",
  "status": "success",
  "job_id": "daily-ceo-briefing",
  "description": "Prepare Monday Morning CEO Briefing",
  "needs_action_file": "scheduled-daily-ceo-briefing-20260225-073000.md",
  "next_run": "2026-02-26T07:30:00+05:00",
  "detail": "Scheduled task triggered, created Needs_Action file"
}
```

## Safety Rules

1. **No direct execution** — scheduler only creates Needs_Action files; processing is handled by the pipeline
2. **PID lock** at `Logs/scheduler.pid` — single instance enforcement
3. **Clean shutdown** — SIGTERM/SIGINT stops scheduler gracefully and removes PID file
4. **Timezone-aware** — all times stored and triggered in configured timezone (default: Asia/Karachi)
5. **Missed job handling** — APScheduler `misfire_grace_time=3600` (1 hour grace), coalesce=True (run once if multiple misfires)
6. **All vault writes scoped to vault root** — path validation on Needs_Action writes
7. **No-deletion policy** — never delete schedule config, logs, or vault files
8. **Disabled jobs skipped** — set `"enabled": false` in config to pause without removing
9. **Log everything** — every registration, trigger, and error logged to `Logs/scheduler.jsonl`

## Resources

### scripts/

- `scheduler_daemon.py` — Main daemon with APScheduler, CLI for adding/listing jobs, PID lock, signal handling

### references/

- `cron_examples.md` — Common cron expressions for AI Employee tasks
