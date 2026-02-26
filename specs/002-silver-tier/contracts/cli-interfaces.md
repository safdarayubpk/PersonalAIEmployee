# CLI Interfaces: Silver Tier

## Action Executor

```text
python execute_action.py --action <action_id> [--params <json>] [--live] [--approval-ref <path>] [--vault-path <path>]

Arguments:
  --action        Required. Action ID from config/actions.json (e.g., email.send_email)
  --params        Optional. JSON string of action parameters (default: "{}")
  --live          Optional. Execute for real (default: dry-run)
  --approval-ref  Optional. Path to approved file in Approved/ (required for HITL live actions)
  --vault-path    Optional. Vault root override (default: VAULT_PATH env or standard)

Exit codes:
  0 = success (dry-run result or live execution completed)
  1 = failure (action error, registry lookup failure, invalid params)
  2 = HITL blocked (approval-required action without approval; Pending_Approval file created)

Output: JSON to stdout with keys: status, action_id, dry_run, result/error
```

## Gmail Watcher

```text
python gmail_poll.py [--live] [--minutes <N>] [--vault-path <path>]

Arguments:
  --live          Mark processed emails as read in Gmail (default: dry-run, read-only)
  --minutes       Poll window in minutes (default: 30)
  --vault-path    Vault root override

Exit codes:
  0 = success
  1 = failure (auth error, vault not found)
```

## WhatsApp Watcher

```text
python whatsapp_monitor.py [--headless] [--interval <seconds>] [--vault-path <path>]

Arguments:
  --headless      Run browser headless (use after QR is linked)
  --interval      Poll interval in seconds (default: 15)
  --vault-path    Vault root override

Exit codes:
  0 = clean shutdown
  1 = failure (vault not found, session error)
```

## Scheduler Daemon

```text
python scheduler_daemon.py [--config <path>] [--vault-path <path>]
python scheduler_daemon.py --add --task-name <id> [--description <text>] [--interval daily|weekly] [--day <weekday>] [--time HH:MM] [--cron <expr>] [--priority routine|sensitive|critical] [--timezone <tz>]
python scheduler_daemon.py --list [--config <path>]

Daemon mode exit codes:
  0 = clean shutdown (SIGTERM/SIGINT)
  1 = failure (no jobs, vault not found, PID lock conflict)

Add mode exit codes:
  0 = job added
  1 = duplicate job ID or invalid config
```

## Central Orchestrator

```text
python orchestrator.py [--batch-size <N>] [--source <filter>] [--vault-path <path>]

Arguments:
  --batch-size    Max files per run (default: 10, cap: 50)
  --source        Filter by source name substring (e.g., gmail, whatsapp)
  --vault-path    Vault root override

Exit codes:
  0 = success (all files processed or no files found)
  1 = failure (vault not found)

Output: JSON to stdout with run summary (scanned, processed, deferred, errors, by_source)
```

## Ralph Retry

```text
python ralph_retry.py --command <shell_command> [--max-retries <N>] [--backoff-base <N>] [--description <text>] [--vault-path <path>]

Arguments:
  --command       Required. Shell command to retry
  --max-retries   Max attempts (default: 15, cap: 20)
  --backoff-base  Exponential base (default: 2, range: 1-5)
  --description   Human-readable task description for logging
  --vault-path    Vault root override

Exit codes:
  0 = task succeeded (possibly after retries)
  1 = task failed after exhausting retries
  2 = task aborted (non-retryable error or HITL block)
```
