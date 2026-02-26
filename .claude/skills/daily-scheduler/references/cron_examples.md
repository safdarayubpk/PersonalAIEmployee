# Cron Examples for AI Employee Tasks

Common cron expressions for use in `config/schedules.json`.

## Format

```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, Mon=0)
│ │ │ │ │
* * * * *
```

## Daily Tasks

| Expression | Description |
|------------|-------------|
| `30 7 * * *` | Daily at 7:30 AM — CEO briefing prep |
| `0 9 * * *` | Daily at 9:00 AM — Morning inbox sweep |
| `0 17 * * *` | Daily at 5:00 PM — End-of-day summary |
| `0 23 * * *` | Daily at 11:00 PM — Nightly cleanup |

## Weekly Tasks

| Expression | Description |
|------------|-------------|
| `0 9 * * 1` | Monday 9:00 AM — Weekly status report |
| `0 14 * * 5` | Friday 2:00 PM — Weekly review prep |
| `0 8 * * 1-5` | Weekdays 8:00 AM — Workday start check |

## Periodic Tasks

| Expression | Description |
|------------|-------------|
| `0 */6 * * *` | Every 6 hours — Stale task sweep |
| `*/30 * * * *` | Every 30 minutes — Quick inbox check |
| `0 */2 * * *` | Every 2 hours — Process pending items |
| `0 0 1 * *` | First of month — Monthly report |

## AI Employee Recommended Schedule

```json
{
  "jobs": [
    {"id": "morning-briefing", "cron": "30 7 * * 1-5", "priority": "high"},
    {"id": "inbox-sweep", "cron": "0 */4 * * *", "priority": "medium"},
    {"id": "weekly-report", "cron": "0 9 * * 1", "priority": "high"},
    {"id": "stale-check", "cron": "0 18 * * *", "priority": "low"},
    {"id": "nightly-cleanup", "cron": "0 23 * * *", "priority": "low"}
  ]
}
```
