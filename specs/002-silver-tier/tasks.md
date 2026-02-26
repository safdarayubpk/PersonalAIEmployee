# Tasks: Silver Tier

**Input**: Design documents from `/specs/002-silver-tier/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Optional unit tests included for action executor and retry logic (spec references SC-002, SC-003 test verification).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create configuration files and action module stubs needed by multiple user stories

- [x] T001 Create action registry config/actions.json with 6 actions (email.send_email, email.draft_email, social.post_social, calendar.create_event, calendar.list_events, documents.generate_report) per specs/002-silver-tier/contracts/action-registry-schema.json
- [x] T002 [P] Create src/actions/social.py with post_social() stub that accepts **kwargs, returns structured dict {status, action, detail}, and logs to actions.jsonl
- [x] T003 [P] Create src/actions/calendar_actions.py with create_event() and list_events() stubs that accept **kwargs, return structured dicts, and log to actions.jsonl
- [x] T004 [P] Create src/actions/documents.py with generate_report() stub that accepts **kwargs, writes a markdown report to Plans/, returns structured dict, and logs to actions.jsonl
- [x] T005 Extend config/ecosystem.config.js to add Silver processes: gmail-watcher, whatsapp-watcher, scheduler-daemon (each with interpreter, script path, env vars, log paths, PID file)
- [x] T006 Add log redaction utility function redact_sensitive(data: dict) to src/vault_helpers.py that replaces values for keys containing "password", "token", "secret", "api_key", "credential", or "auth" with "***REDACTED***" per FR-016

**Checkpoint**: Configuration files and shared utilities ready — user story implementation can begin

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Wire log redaction into all existing scripts — MUST complete before user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Apply redact_sensitive() to log_entry() in .claude/skills/gmail-watcher/scripts/gmail_poll.py — import from src/vault_helpers.py, redact all log entry dicts before writing to JSONL
- [x] T008 [P] Apply redact_sensitive() to log_entry() in .claude/skills/whatsapp-watcher/scripts/whatsapp_monitor.py
- [x] T009 [P] Apply redact_sensitive() to log_entry() in .claude/skills/action-executor/scripts/execute_action.py
- [x] T010 [P] Apply redact_sensitive() to log_entry() in .claude/skills/ralph-retry/scripts/ralph_retry.py
- [x] T011 [P] Apply redact_sensitive() to log_entry() in .claude/skills/daily-scheduler/scripts/scheduler_daemon.py
- [x] T012 [P] Apply redact_sensitive() to log_entry() in .claude/skills/central-orchestrator/scripts/orchestrator.py

**Checkpoint**: Foundation ready — all components use redacted logging (FR-016)

---

## Phase 3: User Story 1 — Multi-Source Watcher Expansion (Priority: P1) 🎯 MVP

**Goal**: Three independent watchers (filesystem, Gmail, WhatsApp) create correctly formatted Needs_Action files with consistent priority classification from shared risk keywords

**Independent Test**: Start all three watchers. Drop a file, send a test email, send a WhatsApp message. Verify three separate Needs_Action files appear with correct source attribution and consistent urgency classification.

### Implementation for User Story 1

- [x] T013 [US1] Verify gmail_poll.py creates Needs_Action files with all 6 required frontmatter fields (title, created, tier, source, priority, status) and gmail-specific field (gmail_id) per specs/002-silver-tier/data-model.md Entity 1 in .claude/skills/gmail-watcher/scripts/gmail_poll.py
- [x] T014 [US1] Verify whatsapp_monitor.py creates Needs_Action files with all 6 required frontmatter fields plus whatsapp-specific field (chat_type: direct|group) per data-model.md Entity 1 in .claude/skills/whatsapp-watcher/scripts/whatsapp_monitor.py
- [x] T015 [US1] Verify gmail_poll.py loads risk keywords from config/risk-keywords.json and maps high→critical, medium→sensitive, default→routine before writing frontmatter priority field in .claude/skills/gmail-watcher/scripts/gmail_poll.py
- [x] T016 [US1] Verify whatsapp_monitor.py loads risk keywords from config/risk-keywords.json and maps high→critical, medium→sensitive, default→routine before writing frontmatter priority field in .claude/skills/whatsapp-watcher/scripts/whatsapp_monitor.py
- [x] T017 [US1] Verify gmail_poll.py handles edge case: email with no subject or body creates Needs_Action file with generated title (email-{sender}-{timestamp}) and routine priority in .claude/skills/gmail-watcher/scripts/gmail_poll.py
- [x] T018 [US1] Verify gmail_poll.py handles auth failure: catches expired token, attempts re-auth once, exits cleanly on failure without crashing in .claude/skills/gmail-watcher/scripts/gmail_poll.py
- [x] T019 [US1] Verify whatsapp_monitor.py handles session loss: detects disconnection within 60s, logs error to Logs/whatsapp.jsonl, removes PID lock file, exits cleanly in .claude/skills/whatsapp-watcher/scripts/whatsapp_monitor.py

**Checkpoint**: All three watchers independently create correctly formatted Needs_Action files with consistent priority classification (SC-001)

---

## Phase 4: User Story 2 — Action Execution with Safety Gates (Priority: P2)

**Goal**: Action executor dispatches 6 registered actions via importlib, defaults to dry-run, gates sensitive actions behind Pending_Approval flow

**Independent Test**: Trigger email.draft_email in dry-run (exit 0, no side effects). Trigger email.send_email without approval (exit 2, Pending_Approval file created). Move to Approved/, re-trigger with --live --approval-ref (function called, logged).

### Implementation for User Story 2

- [x] T020 [US2] Wire execute_action.py to load config/actions.json via load_registry(), resolve module+function via importlib.import_module(), and call with params dict in .claude/skills/action-executor/scripts/execute_action.py
- [x] T021 [US2] Implement dry-run mode in execute_action.py: when --live is NOT passed, log action params to Logs/actions.jsonl, return {status: "dry-run", action_id, result: "simulated"}, exit 0 in .claude/skills/action-executor/scripts/execute_action.py
- [x] T022 [US2] Implement HITL gate in execute_action.py: when --live is passed for hitl_required=true action WITHOUT --approval-ref, create Pending_Approval markdown file with frontmatter (title, created, type, action_id, request_id, status: pending_approval) and body (params JSON, instructions), exit 2 in .claude/skills/action-executor/scripts/execute_action.py
- [x] T023 [US2] Implement approval verification in execute_action.py: when --live and --approval-ref are both passed, verify the referenced file exists in Approved/ folder, then call the action function via importlib, log result to Logs/actions.jsonl, exit 0 on success or 1 on failure in .claude/skills/action-executor/scripts/execute_action.py
- [x] T024 [US2] Implement --list flag in execute_action.py: output all registered actions from config/actions.json with action_id, description, hitl_required for each in .claude/skills/action-executor/scripts/execute_action.py
- [x] T025 [US2] Verify execute_action.py handles unknown action_id: returns error listing all available action_ids from registry, logs failed lookup, exits 1 in .claude/skills/action-executor/scripts/execute_action.py
- [x] T026 [US2] Verify execute_action.py handles live execution failure: catches exception from action function, logs full error (class, message, truncated traceback) to Logs/actions.jsonl, returns error response, exits 1, no partial state in .claude/skills/action-executor/scripts/execute_action.py
- [x] T026b [US2] Implement critical action logging in execute_action.py: when a critical-risk action (hitl_required=true AND priority=critical) completes live execution, append entry to Logs/critical_actions.jsonl with timestamp, action_id, request_id, approval_ref, result, and acknowledgment_required=true per constitution II in .claude/skills/action-executor/scripts/execute_action.py
- [x] T027 [US2] Verify all 6 action stubs (email.send_email, email.draft_email, social.post_social, calendar.create_event, calendar.list_events, documents.generate_report) are importable and return structured dicts when called — test with dry-run mode via execute_action.py

**Checkpoint**: Action executor handles all three lifecycle states (dry-run, HITL-blocked, live-approved) for all 6 actions (SC-002)

---

## Phase 5: User Story 3 — Task Persistence and Retry (Priority: P3)

**Goal**: Ralph retry wraps any shell command with exponential backoff, configurable limits, JSONL logging, and clean abort on non-retryable errors

**Independent Test**: Create a task that fails twice then succeeds on 3rd attempt. Verify 3 attempts with ~2s and ~4s delays logged to Logs/retry.jsonl with timestamps.

### Implementation for User Story 3

- [x] T028 [US3] Verify ralph_retry.py implements exponential backoff: delay = min(base^attempt, 300s), default base=2, configurable via --backoff-base in .claude/skills/ralph-retry/scripts/ralph_retry.py
- [x] T029 [US3] Verify ralph_retry.py enforces hard cap: --max-retries silently clamped to 20 with warning log "Max retries clamped from N to 20 (hard cap)" in .claude/skills/ralph-retry/scripts/ralph_retry.py
- [x] T030 [US3] Verify ralph_retry.py logs every attempt to Logs/retry.jsonl with fields: timestamp, component (ralph-retry), action (attempt|success|failure|abort), status, task_id, attempt, delay_seconds, error, detail per data-model.md Entity 5 in .claude/skills/ralph-retry/scripts/ralph_retry.py
- [x] T031 [US3] Verify ralph_retry.py handles non-retryable errors: exit code 2 from command causes immediate abort (no further retries), logged as action:abort in .claude/skills/ralph-retry/scripts/ralph_retry.py
- [x] T032 [US3] Verify ralph_retry.py handles SIGINT: current attempt completes or is interrupted, loop stops cleanly, partial state logged in .claude/skills/ralph-retry/scripts/ralph_retry.py
- [x] T033 [US3] Verify ralph_retry.py exit codes: 0 on eventual success, 1 on exhausted retries, 2 on non-retryable abort per contracts/cli-interfaces.md in .claude/skills/ralph-retry/scripts/ralph_retry.py

**Checkpoint**: Retry mechanism recovers from transient failures with correct backoff timing and logging (SC-003)

---

## Phase 6: User Story 4 — Recurring Task Scheduling (Priority: P4)

**Goal**: Scheduler daemon creates Needs_Action files at configured times, supports daily/weekly/cron schedules, PID lock protection, and missed trigger recovery

**Independent Test**: Add a task scheduled 1 minute in the future, wait, verify Needs_Action file created with source: daily-scheduler, type: scheduled.

### Implementation for User Story 4

- [x] T034 [US4] Verify scheduler_daemon.py creates Needs_Action files with correct frontmatter: source: daily-scheduler, type: scheduled, task (job ID), schedule, priority (from job config), status: needs_action per data-model.md Entity 1 in .claude/skills/daily-scheduler/scripts/scheduler_daemon.py
- [x] T035 [US4] Verify scheduler_daemon.py --add creates/updates config/schedules.json with job definition (id, description, interval|cron, time, day, timezone, priority, enabled) per data-model.md Entity 4 in .claude/skills/daily-scheduler/scripts/scheduler_daemon.py
- [x] T036 [US4] Verify scheduler_daemon.py --list displays all configured jobs with ID, description, schedule, next run time, enabled status in .claude/skills/daily-scheduler/scripts/scheduler_daemon.py
- [x] T037 [US4] Verify scheduler_daemon.py validates schedule config: rejects invalid time expressions (hour 0-23, minute 0-59), reports specific invalid field and value in .claude/skills/daily-scheduler/scripts/scheduler_daemon.py
- [x] T038 [US4] Verify scheduler_daemon.py PID lock: writes PID to Logs/scheduler.pid, detects stale PID via os.kill(pid, 0), refuses duplicate start with message showing existing PID in .claude/skills/daily-scheduler/scripts/scheduler_daemon.py
- [x] T039 [US4] Verify scheduler_daemon.py handles missed triggers: misfire_grace_time (default 3600s) causes missed jobs to fire on next startup in .claude/skills/daily-scheduler/scripts/scheduler_daemon.py
- [x] T040 [US4] Verify scheduler_daemon.py signal handlers: SIGTERM/SIGINT triggers clean shutdown — scheduler stops, PID file removed, shutdown logged to Logs/scheduler.jsonl in .claude/skills/daily-scheduler/scripts/scheduler_daemon.py

**Checkpoint**: Scheduler creates Needs_Action files on schedule with correct attributes and PID protection (SC-004)

---

## Phase 7: User Story 5 — Central Orchestration Hub (Priority: P5)

**Goal**: Orchestrator scans all Needs_Action files, queues by priority, routes by risk, updates dashboard with per-source breakdown, handles 10+ files per run

**Independent Test**: Create 12 Needs_Action files (4 per source, mixed priorities). Run orchestrator with batch 10. Verify priority ordering, correct routing, 2 deferred, dashboard updated.

### Implementation for User Story 5

- [x] T041 [US5] Verify orchestrator.py scans Needs_Action/*.md excluding .moved files and status:processing files, returns list sorted by priority (critical→sensitive→routine, then by creation time) in .claude/skills/central-orchestrator/scripts/orchestrator.py
- [x] T042 [US5] Verify orchestrator.py enforces batch-size cap (default 10, hard cap 50 per C-006), defers excess files with logged count in .claude/skills/central-orchestrator/scripts/orchestrator.py
- [x] T043 [US5] Verify orchestrator.py marks files status:processing during handling and resets to needs_action on error (FR-017) in .claude/skills/central-orchestrator/scripts/orchestrator.py
- [x] T044 [US5] Verify orchestrator.py routes correctly: assess_risk() scans content against config/risk-keywords.json, high-risk→Pending_Approval, medium-risk→Pending_Approval, low-risk→Done in .claude/skills/central-orchestrator/scripts/orchestrator.py
- [x] T045 [US5] Verify orchestrator.py attempt_action() calls execute_action.py (dry-run) for files from sources with action mappings (gmail→email.draft_email, etc.) in .claude/skills/central-orchestrator/scripts/orchestrator.py
- [x] T046 [US5] Verify orchestrator.py handles malformed frontmatter gracefully: skips file, resets status to needs_action, logs error with filename and detail, continues processing remaining files in .claude/skills/central-orchestrator/scripts/orchestrator.py
- [x] T047 [US5] Verify orchestrator.py update_dashboard() appends summary table to Dashboard.md with: run_id, timestamp, scanned, processed, action_calls, pending_approval, deferred, errors, per-source breakdown table per data-model.md Entity 6 in .claude/skills/central-orchestrator/scripts/orchestrator.py
- [x] T048 [US5] Add stale Pending_Approval detection: orchestrator logs warning for any Pending_Approval files older than 48 hours during each run in .claude/skills/central-orchestrator/scripts/orchestrator.py
- [x] T049 [US5] Verify orchestrator.py logs all routing decisions to Logs/orchestrator.jsonl with fields: timestamp, component, action, status, detail, run_id, priority, source per data-model.md Entity 7 in .claude/skills/central-orchestrator/scripts/orchestrator.py

**Checkpoint**: Orchestrator processes 12-file test batch correctly with priority ordering, risk routing, and dashboard update (SC-005)

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Test plan, PM2 validation, Bronze regression, stability testing

- [x] T050 Create tests/manual/silver-tier-test-plan.md covering SC-001 through SC-010 with step-by-step verification procedures, expected outputs, and pass/fail criteria
- [x] T051 [P] Create tests/unit/test_action_executor.py with pytest tests: dry-run returns correct dict, unknown action_id returns error, HITL gate creates Pending_Approval file, approval-exempt actions skip gate
- [x] T052 [P] Create tests/unit/test_ralph_retry.py with pytest tests: exponential backoff timing, hard cap clamping, non-retryable exit code 2 aborts immediately, success on Nth attempt logs all N attempts
- [x] T053 Verify config/ecosystem.config.js starts all Silver processes via pm2 start and all reach "online" status within 10 seconds
- [x] T054 Run Bronze tier regression: re-execute tests/manual/bronze-tier-test-plan.md and verify all 9 Bronze success criteria pass unchanged (SC-009)
- [x] T055 Run 30-minute stability test with all watchers + scheduler active, process 15+ events, verify zero unhandled exceptions and zero orphaned files (SC-006)
- [x] T056 Verify SC-008: search all Logs/*.jsonl for known test credential values — all must show ***REDACTED*** instead of actual values
- [x] T057 Run quickstart.md validation: execute specs/002-silver-tier/quickstart.md steps 1-8 end-to-end and verify each step produces expected output
- [x] T058 Clean up any orphaned .tmp files or stale PID files in Logs/, verify all PID files are removed on clean shutdown

**Checkpoint**: All Silver success criteria (SC-001 through SC-010) validated

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on T006 (redaction utility) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 completion — no dependencies on other stories
- **US2 (Phase 4)**: Depends on Phase 1 (T001 actions.json, T002-T004 stubs) + Phase 2
- **US3 (Phase 5)**: Depends on Phase 2 — no dependencies on US1 or US2
- **US4 (Phase 6)**: Depends on Phase 2 — no dependencies on US1-US3
- **US5 (Phase 7)**: Depends on US1 (watchers create files) + US2 (action executor wired) — orchestrator integrates both
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Independent after Phase 2
- **US2 (P2)**: Independent after Phase 1 + Phase 2 (needs actions.json + stubs)
- **US3 (P3)**: Independent after Phase 2
- **US4 (P4)**: Independent after Phase 2
- **US5 (P5)**: Depends on US1 + US2 (orchestrator calls watchers' output and action executor)

### Within Each User Story

- Verify/fix core functionality first
- Then verify edge cases and error handling
- Then verify logging and output format

### Parallel Opportunities

- T002, T003, T004 can run in parallel (different action stub files)
- T007-T012 can run in parallel after T006 (different script files for redaction wiring)
- US1, US2, US3, US4 can run in parallel after Phase 2 (independent stories)
- T051, T052 can run in parallel (different test files)
- US5 must wait for US1 + US2 to be complete

---

## Parallel Example: Phase 1 Setup

```bash
# After T001 (actions.json), launch all stubs in parallel:
Task: "Create src/actions/social.py with post_social() stub"
Task: "Create src/actions/calendar_actions.py with create_event() and list_events() stubs"
Task: "Create src/actions/documents.py with generate_report() stub"
```

## Parallel Example: Phase 2 Foundational

```bash
# After T006 (redaction utility), apply to all scripts in parallel:
Task: "Apply redact_sensitive() to gmail_poll.py"
Task: "Apply redact_sensitive() to whatsapp_monitor.py"
Task: "Apply redact_sensitive() to execute_action.py"
Task: "Apply redact_sensitive() to ralph_retry.py"
Task: "Apply redact_sensitive() to scheduler_daemon.py"
Task: "Apply redact_sensitive() to orchestrator.py"
```

## Parallel Example: User Stories 1-4

```bash
# After Phase 2, all independent stories can start:
Task: "US1: Multi-Source Watcher Expansion (T013-T019)"
Task: "US2: Action Execution with Safety Gates (T020-T027)"
Task: "US3: Task Persistence and Retry (T028-T033)"
Task: "US4: Recurring Task Scheduling (T034-T040)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T012)
3. Complete Phase 3: User Story 1 — Multi-Source Watchers (T013-T019)
4. **STOP and VALIDATE**: Run SC-001 — all three watchers create correct files
5. Demonstrate multi-source ingestion

### Incremental Delivery

1. Setup + Foundational → Configuration ready
2. Add US1 → Test independently → Three watchers operational (MVP!)
3. Add US2 → Test independently → Actions execute with safety gates
4. Add US3 → Test independently → Retry loop handles failures
5. Add US4 → Test independently → Scheduled tasks fire on time
6. Add US5 → Test independently → Orchestrator ties everything together
7. Polish → Full validation → SC-001 through SC-010

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All 6 Silver scripts are already scaffolded with CLI entry points — tasks verify/fix functionality, not create from scratch
- Many tasks are "Verify and fix" rather than "Create" because scripts exist but may need adjustments to match spec exactly
- config/actions.json must match specs/002-silver-tier/contracts/action-registry-schema.json exactly
- Stop at any checkpoint to validate story independently
- Commit after each phase or logical group
