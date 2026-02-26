# Quickstart: Silver Tier

**Date**: 2026-02-26
**Prerequisites**: Bronze tier fully operational, Python 3.13+ venv active

## 1. Verify Bronze Foundation

```bash
# Confirm vault exists with all 7 folders
ls /home/safdarayub/Documents/AI_Employee_Vault/
# Expected: Approved/ Done/ Inbox/ Logs/ Needs_Action/ Pending_Approval/ Plans/

# Confirm Bronze watcher works
python src/file_drop_watcher.py &
echo "test" > ~/Desktop/DropForAI/test-quickstart.txt
sleep 5
ls /home/safdarayub/Documents/AI_Employee_Vault/Needs_Action/
# Expected: file containing test-quickstart
```

## 2. Install Dependencies

```bash
# All should already be installed from Bronze
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
pip install playwright && playwright install chromium
pip install apscheduler
```

## 3. Configuration Files

```bash
# Risk keywords (should already exist)
cat config/risk-keywords.json

# Create action registry
cat config/actions.json
# See data-model.md for full registry contents

# Scheduler config (auto-created on first --add)
python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py \
  --add --task-name "test-job" --interval daily --time "09:00" \
  --priority sensitive --description "Test scheduled task"
```

## 4. Start Silver Components

```bash
# Terminal 1: Gmail watcher (dry-run first)
python .claude/skills/gmail-watcher/scripts/gmail_poll.py --minutes 60

# Terminal 2: WhatsApp watcher (first run: scan QR)
python .claude/skills/whatsapp-watcher/scripts/whatsapp_monitor.py

# Terminal 3: Scheduler daemon
python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py

# Or use PM2 for all:
pm2 start config/ecosystem.config.js
```

## 5. Test Action Executor

```bash
# Dry-run (default) — should log but take no action
python .claude/skills/action-executor/scripts/execute_action.py \
  --action email.draft_email \
  --params '{"to": "test@example.com", "subject": "Test", "body": "Hello"}'
# Expected: exit 0, dry-run result in stdout

# HITL gate test — should create Pending_Approval file
python .claude/skills/action-executor/scripts/execute_action.py \
  --action email.send_email \
  --params '{"to": "test@example.com", "subject": "Test", "body": "Hello"}' \
  --live
# Expected: exit 2, Pending_Approval file created
```

## 6. Run Orchestrator

```bash
# Process all Needs_Action files
python .claude/skills/central-orchestrator/scripts/orchestrator.py --batch-size 10
# Expected: JSON summary with scanned/processed/deferred counts
```

## 7. Test Retry Loop

```bash
# Wrap a failing command in retry
python .claude/skills/ralph-retry/scripts/ralph_retry.py \
  --command "python -c \"import sys; sys.exit(1)\"" \
  --max-retries 3 \
  --backoff-base 2 \
  --description "Test retry"
# Expected: 3 attempts with ~2s and ~4s delays, then failure
```

## 8. Verify Logs

```bash
# Check all JSONL logs exist and contain valid entries
for f in gmail.jsonl whatsapp.jsonl scheduler.jsonl orchestrator.jsonl actions.jsonl; do
  echo "=== $f ==="
  tail -1 /home/safdarayub/Documents/AI_Employee_Vault/Logs/$f 2>/dev/null || echo "(not yet created)"
done
```

## Key Paths

| Component | Script Path |
|-----------|-------------|
| Gmail watcher | `.claude/skills/gmail-watcher/scripts/gmail_poll.py` |
| WhatsApp watcher | `.claude/skills/whatsapp-watcher/scripts/whatsapp_monitor.py` |
| Action executor | `.claude/skills/action-executor/scripts/execute_action.py` |
| Ralph retry | `.claude/skills/ralph-retry/scripts/ralph_retry.py` |
| Scheduler | `.claude/skills/daily-scheduler/scripts/scheduler_daemon.py` |
| Orchestrator | `.claude/skills/central-orchestrator/scripts/orchestrator.py` |
| Action modules | `src/actions/*.py` |
| Action registry | `config/actions.json` |
| Risk keywords | `config/risk-keywords.json` |
| PM2 config | `config/ecosystem.config.js` |
