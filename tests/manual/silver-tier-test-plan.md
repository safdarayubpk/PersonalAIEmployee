# Silver Tier Test Plan

**Date**: 2026-02-26
**Tier**: Silver
**Success Criteria**: SC-001 through SC-010

---

## SC-001: Multi-Source Watcher Expansion

**Test**: Three watchers create correctly formatted Needs_Action files

### Steps

1. Ensure vault exists at `/home/safdarayub/Documents/AI_Employee_Vault`
2. Start filesystem watcher: `pm2 start config/ecosystem.config.js --only ai-employee-watcher`
3. Drop a test file into `Inbox/` folder
4. Verify `Needs_Action/` contains a new `.md` file with frontmatter: title, created, tier, source (file-drop-watcher), priority, status
5. Start Gmail watcher: `python .claude/skills/gmail-watcher/scripts/gmail_poll.py`
6. Verify it polls unread emails and creates Needs_Action files with source: gmail-watcher, gmail_id field
7. Verify priority mapping: financial keywords → critical, meeting keywords → sensitive, other → routine
8. Start WhatsApp watcher: `python .claude/skills/whatsapp-watcher/scripts/whatsapp_monitor.py`
9. Verify it detects unread chats and creates Needs_Action files with source: whatsapp-watcher, chat_type field

**Pass Criteria**: Three separate Needs_Action files with correct source attribution and priority

---

## SC-002: Action Execution with Safety Gates

**Test**: Action executor handles dry-run, HITL-blocked, and live-approved states

### Steps

1. Dry-run test (exit 0):
   ```bash
   python .claude/skills/action-executor/scripts/execute_action.py \
     --action email.draft_email --params '{"to": "test@example.com", "subject": "Test"}'
   ```
   Verify: exit 0, output contains "DRY RUN", no side effects

2. HITL-blocked test (exit 2):
   ```bash
   python .claude/skills/action-executor/scripts/execute_action.py \
     --action email.send_email --params '{"to": "test@example.com"}' --live
   ```
   Verify: exit 2, Pending_Approval file created with type: pending-action, action_id, request_id

3. Approval test (exit 0):
   - Move the Pending_Approval file to `Approved/`
   - Re-run with `--live --approval-ref "Approved/<filename>"`
   - Verify: exit 0, action function called, logged to actions.jsonl

4. List test:
   ```bash
   python .claude/skills/action-executor/scripts/execute_action.py --list
   ```
   Verify: 6 actions displayed with hitl_required status

5. Unknown action test (exit 1):
   ```bash
   python .claude/skills/action-executor/scripts/execute_action.py --action fake.action
   ```
   Verify: exit 1, error lists available actions

**Pass Criteria**: All three lifecycle states work correctly for all 6 actions

---

## SC-003: Task Persistence and Retry

**Test**: Ralph retry with exponential backoff

### Steps

1. Create a test script that fails twice then succeeds:
   ```bash
   # test_flaky.sh
   FILE="/tmp/ralph_test_counter"
   COUNT=$(cat "$FILE" 2>/dev/null || echo 0)
   COUNT=$((COUNT + 1))
   echo "$COUNT" > "$FILE"
   if [ "$COUNT" -lt 3 ]; then exit 1; fi
   echo "Success on attempt $COUNT"
   ```

2. Run ralph retry:
   ```bash
   python .claude/skills/ralph-retry/scripts/ralph_retry.py \
     --command "bash /tmp/test_flaky.sh" --description "Flaky test" \
     --max-retries 5 --backoff-base 2
   ```

3. Verify: 3 attempts logged to Logs/retry.jsonl with timestamps showing ~2s and ~4s delays
4. Verify exit code 0 on success

5. Test hard cap:
   ```bash
   python .claude/skills/ralph-retry/scripts/ralph_retry.py \
     --command "false" --description "Always fails" --max-retries 25
   ```
   Verify: clamped to 20, warning logged

6. Test non-retryable (exit 2):
   ```bash
   python .claude/skills/ralph-retry/scripts/ralph_retry.py \
     --command "exit 2" --description "Non-retryable"
   ```
   Verify: immediate abort, exit code 2, action:abort in log

**Pass Criteria**: Backoff timing correct, hard cap enforced, non-retryable abort works

---

## SC-004: Recurring Task Scheduling

**Test**: Scheduler creates Needs_Action files on schedule

### Steps

1. Add a test job 1 minute in the future:
   ```bash
   python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py \
     --add --task-name "test-task" --description "Test scheduled task" \
     --time "$(date -d '+1 min' +%H:%M)" --priority sensitive
   ```

2. Start daemon:
   ```bash
   python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py &
   ```

3. Wait ~90 seconds
4. Verify Needs_Action file: source: daily-scheduler, type: scheduled, task: test-task
5. Verify PID file exists: `Logs/scheduler.pid`
6. Send SIGTERM: `kill $(cat Logs/scheduler.pid)`
7. Verify: clean shutdown logged, PID file removed

8. List jobs:
   ```bash
   python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py --list
   ```
   Verify: test-task displayed with schedule and priority

**Pass Criteria**: Job fires on schedule, Needs_Action file correct, clean shutdown

---

## SC-005: Central Orchestration Hub

**Test**: Orchestrator processes 12-file test batch

### Steps

1. Create 12 test Needs_Action files (4 per source):
   - 4 from gmail-watcher (1 critical, 1 sensitive, 2 routine)
   - 4 from whatsapp-watcher (1 critical, 1 sensitive, 2 routine)
   - 4 from file-drop-watcher (1 critical, 1 sensitive, 2 routine)

2. Run orchestrator with batch 10:
   ```bash
   python .claude/skills/central-orchestrator/scripts/orchestrator.py --batch-size 10
   ```

3. Verify:
   - Priority ordering (critical first, then sensitive, then routine)
   - 2 deferred (12 - 10 batch)
   - High-risk → Pending_Approval
   - Low-risk → Done
   - Dashboard.md updated with run_id, per-source breakdown

4. Run again to process deferred files

**Pass Criteria**: Priority ordering, correct routing, deferred count, dashboard updated

---

## SC-006: Stability Test

**Test**: 30-minute run with all watchers + scheduler

### Steps

1. Start all processes via PM2: `pm2 start config/ecosystem.config.js`
2. Generate 15+ events across all sources over 30 minutes
3. Monitor for exceptions: `pm2 logs --err`
4. After 30 minutes, check for orphaned `.tmp` files
5. Verify zero unhandled exceptions in all JSONL logs

**Pass Criteria**: Zero exceptions, zero orphaned files

---

## SC-007: Action Stub Verification

**Test**: All 6 action stubs are importable and return structured dicts

### Steps

1. Test each stub via dry-run:
   ```bash
   for action in email.send_email email.draft_email social.post_social \
     calendar.create_event calendar.list_events documents.generate_report; do
     python .claude/skills/action-executor/scripts/execute_action.py \
       --action "$action" --params '{}'
   done
   ```

2. Verify each returns {success: true, dry_run: true} without import errors

**Pass Criteria**: All 6 stubs importable and return structured dicts

---

## SC-008: Log Redaction

**Test**: Sensitive fields redacted in all logs

### Steps

1. Process events containing test credential values
2. Search all JSONL logs: `grep -r "test_password\|test_token\|test_secret" Logs/`
3. Verify all sensitive values show `***REDACTED***`

**Pass Criteria**: Zero raw credential values in any log file

---

## SC-009: Bronze Regression

**Test**: All Bronze functionality still works

### Steps

1. Re-execute `tests/manual/bronze-tier-test-plan.md` steps
2. Verify all 9 Bronze success criteria pass unchanged

**Pass Criteria**: All Bronze tests pass without modification

---

## SC-010: End-to-End Integration

**Test**: Full pipeline from watcher → orchestrator → action

### Steps

1. Start all watchers and scheduler
2. Trigger an event (e.g., send test email)
3. Verify watcher creates Needs_Action file
4. Run orchestrator
5. Verify routing (risk assessment → appropriate folder)
6. For HITL items: move to Approved, re-run with --live
7. Verify action executed and logged

**Pass Criteria**: Complete pipeline works end-to-end
