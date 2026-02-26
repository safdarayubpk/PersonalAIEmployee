# Feature Specification: Personal AI Employee — Silver Tier

**Feature Branch**: `002-silver-tier`
**Created**: 2026-02-26
**Status**: Draft
**Input**: User description: "Build on Bronze tier with multiple input sources, action execution, persistence, and scheduling for a proactive agent"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Multi-Source Watcher Expansion (Priority: P1)

A developer extends the agent beyond the single filesystem watcher. They configure and start a Gmail watcher that polls for unread emails, a WhatsApp watcher that monitors incoming messages via a browser session, and the existing filesystem watcher continues running. Each watcher independently creates structured `Needs_Action` markdown files in the vault when relevant items are detected. The developer can see items from all three sources appearing in `Needs_Action/` with source attribution. All watchers use the same shared risk-keyword list for consistent urgency classification.

**Why this priority**: Multiple input sources are the defining differentiator between Bronze (single watcher) and Silver (multi-source). Without this, the agent remains reactive to only one channel.

**Independent Test**: Start all three watchers. Drop a file into the drop folder, send a test email to the configured Gmail account, and send a WhatsApp message. Verify that three separate `Needs_Action` files appear — one per source — each with correct source attribution in frontmatter and consistent urgency classification.

**Acceptance Scenarios**:

1. **Given** the Gmail watcher is configured with valid credentials and running, **When** an unread email arrives from a non-spam sender, **Then** a `Needs_Action` file is created within 60 seconds with frontmatter containing `source: gmail-watcher`, the sender's name/address, email subject as title, and urgency classification (routine/sensitive/critical) derived from the shared risk-keyword list.
2. **Given** the WhatsApp watcher is running with an authenticated browser session, **When** an unread WhatsApp message is received, **Then** a `Needs_Action` file is created within 60 seconds with frontmatter containing `source: whatsapp-watcher`, sender name, message preview (truncated to 500 characters), and urgency classification derived from the same shared risk-keyword list.
3. **Given** the filesystem watcher is running (Bronze tier), **When** a file is dropped into the drop folder, **Then** a `Needs_Action` file is created within 5 seconds with `source: file-drop-watcher` (unchanged from Bronze behavior).
4. **Given** all three watchers are running simultaneously, **When** events occur on all three channels within the same minute, **Then** three separate `Needs_Action` files are created without interference, each with the correct source attribution and no data corruption.
5. **Given** the Gmail watcher encounters an authentication failure (expired token), **When** the failure occurs, **Then** the watcher logs the error, attempts to re-authenticate once, and if re-authentication fails, exits cleanly without crashing or affecting other watchers.
6. **Given** an email containing the keyword "invoice" (a high-risk keyword), **When** both the Gmail watcher and the orchestrator process it, **Then** both classify it as critical priority — demonstrating consistent keyword application from the shared risk-keyword configuration.

---

### User Story 2 — Action Execution with Safety Gates (Priority: P2)

A developer triggers action execution for items that have been processed and approved. The system provides an action executor that can perform real operations (send emails, manage calendar events, generate documents) but always defaults to dry-run mode. Actions requiring human judgment (sending emails, creating external events) are gated behind an approval flow: the action creates a file in `Pending_Approval/`, and only when the developer manually moves it to `Approved/` does the system execute the action for real. At least 6 actions are registered in the action registry covering email, social, calendar, and document domains.

**Why this priority**: Action execution is what transforms the agent from an information organizer into an active assistant. Without it, the agent can only observe and classify but never act.

**Independent Test**: Trigger `email.draft_email` in dry-run mode — verify it logs but takes no action. Trigger `email.send_email` without approval — verify it creates a `Pending_Approval` file. Move that file to `Approved/`, re-trigger with live mode — verify the action function is called and the result is logged.

**Acceptance Scenarios**:

1. **Given** the `email.draft_email` action is registered (approval-exempt), **When** the developer triggers it in dry-run mode, **Then** the system logs the action parameters to `Logs/actions.jsonl` and returns a dry-run result — no file is created in `Plans/` and no email is sent.
2. **Given** the `email.send_email` action is registered (approval-required), **When** the developer triggers it without prior approval, **Then** the system creates a pending action file in `Pending_Approval/` containing the action ID, parameters, a unique request ID, and approval instructions, then exits with exit code 2 (HITL blocked).
3. **Given** a pending action file for `email.send_email` exists in `Pending_Approval/`, **When** the developer moves it to `Approved/` and re-triggers the action with live mode and `--approval-ref` pointing to the approved file, **Then** the system detects the approval, calls the `send_email` function, logs the result to `Logs/actions.jsonl`, and returns a success response.
4. **Given** the `documents.generate_report` action is registered (approval-exempt), **When** the developer triggers it with live mode, **Then** the system executes immediately without requiring approval flow and returns the function result.
5. **Given** an action fails during live execution (e.g., network error in `send_email`), **Then** the system catches the exception, logs the error with full details to `Logs/actions.jsonl`, returns an error response with exit code 1, and does not leave partial state.

---

### User Story 3 — Task Persistence and Retry (Priority: P3)

A developer relies on the agent to persist through transient failures. When an action or processing step fails (network timeout, temporary service unavailability), the system automatically retries with exponential backoff delays (2s, 4s, 8s, 16s... capped at 300 seconds). The developer can configure the maximum number of retries (default 15, hard cap 20) and backoff base (default 2). The retry loop logs every attempt and reports the final outcome (success after N retries, or permanent failure after exhausting retries).

**Why this priority**: Reliability separates a demo from a usable tool. Without retry logic, any transient failure requires manual re-triggering.

**Independent Test**: Create a task that fails twice then succeeds on the third attempt. Verify the retry loop executes 3 attempts with delays of approximately 2s and 4s respectively, logs all 3 attempts with timestamps, and ultimately reports success.

**Acceptance Scenarios**:

1. **Given** a task fails with a transient error, **When** the retry loop is active with default settings (max 15, backoff base 2), **Then** the system waits 2 seconds before the 2nd attempt, 4 seconds before the 3rd, 8 seconds before the 4th (doubling each time, capped at 300 seconds), and retries up to 15 times.
2. **Given** a task succeeds on the 3rd retry, **When** the success is detected, **Then** the system logs all 3 attempts with timestamps showing increasing delays, reports "Success on attempt 3", and updates the dashboard with the outcome.
3. **Given** a task fails on all retry attempts (15 by default), **When** the maximum is exhausted, **Then** the system logs the final failure with total elapsed time, creates a failure summary, and does not retry further.
4. **Given** a task raises a non-retryable error (PermissionError, SystemExit, KeyboardInterrupt), **When** the error is detected, **Then** the system immediately stops retrying without delay, logs the error class name and reason, and reports the failure.
5. **Given** the retry loop is running and the developer sends SIGINT (Ctrl+C), **When** the signal is received, **Then** the current attempt completes (or is interrupted if the task itself handles SIGINT), the loop stops cleanly, and the partial state is logged.

---

### User Story 4 — Recurring Task Scheduling (Priority: P4)

A developer configures the agent to perform tasks on a recurring schedule. They define one or more scheduled tasks (e.g., "every weekday at 9 AM, prepare a CEO briefing summary") via a JSON configuration file. At the scheduled time, the system creates a `Needs_Action` file with the task details, which then flows through the normal processing pipeline. The developer can list active jobs and add new ones via the command line.

**Why this priority**: Scheduling makes the agent truly proactive — it acts without any human trigger. This is the final piece that makes the Silver tier a genuine autonomous assistant.

**Independent Test**: Add a scheduled task with a trigger time 1 minute in the future, wait for the trigger, verify a `Needs_Action` file is created with `source: daily-scheduler`, `type: scheduled`, and the correct task description.

**Acceptance Scenarios**:

1. **Given** a scheduled task is configured for a specific time, **When** the scheduled time arrives, **Then** the system creates a `Needs_Action` file within 5 seconds of the trigger time with frontmatter containing `source: daily-scheduler`, `type: scheduled`, the task ID, and the task description in the body.
2. **Given** the scheduler daemon is running, **When** the developer runs the list command, **Then** all configured tasks are displayed with their job ID, description, schedule expression, next run time, and enabled/disabled status.
3. **Given** the developer adds a new scheduled task via the add command, **When** the task is saved to the configuration file, **Then** it appears in the schedule list and will trigger at the next matching time without restarting the scheduler daemon.
4. **Given** the scheduler was not running at the configured trigger time (e.g., system restarted 30 minutes after the scheduled time), **When** the scheduler starts, **Then** the missed task is executed within the grace period (default 1 hour, configurable) — not silently dropped. Verified by checking that a `Needs_Action` file exists with a `created` timestamp after the scheduler start time.
5. **Given** the scheduler daemon is already running (PID lock file exists and process is alive), **When** the developer attempts to start another instance, **Then** the system refuses to start with a message identifying the existing process PID and exits with a non-zero code.

---

### User Story 5 — Central Orchestration Hub (Priority: P5)

A developer runs the central orchestrator, which scans all `Needs_Action` files regardless of their source (filesystem, Gmail, WhatsApp, scheduler), queues them by priority, performs risk assessment using the shared risk-keyword list, and routes each to the appropriate destination: routine-priority items are processed and moved to `Done/`, sensitive/critical-priority items are routed to `Pending_Approval/`, and items requiring external actions are evaluated against the action registry. The orchestrator handles 10+ files in a single run without failure and updates the dashboard with a comprehensive summary broken down by source.

**Why this priority**: The orchestrator ties all Silver tier components together into a cohesive system. Without it, each watcher and action operates in isolation.

**Independent Test**: Create 12 `Needs_Action` files (4 filesystem, 4 Gmail, 4 WhatsApp) with varied priorities (4 critical, 4 sensitive, 4 routine). Run the orchestrator with batch size 10 and verify: 10 files processed in priority order, 2 deferred, correct routing per priority level, and dashboard summary with accurate per-source counts.

**Acceptance Scenarios**:

1. **Given** 12 `Needs_Action` files exist from 3 different sources (4 filesystem, 4 Gmail, 4 WhatsApp) with priorities (4 critical, 4 sensitive, 4 routine), **When** the orchestrator runs with a batch size of 10, **Then** the 10 highest-priority files are processed in priority order (critical first, then sensitive, then routine), the remaining 2 lowest-priority files are deferred with a logged message including the count.
2. **Given** a mix of files with risk keywords ("payment" = critical-priority, "meeting" = sensitive-priority, routine content = routine-priority), **When** the orchestrator processes them, **Then** critical-priority files route to `Pending_Approval/`, sensitive-priority files route to `Pending_Approval/`, routine-priority files route to `Done/`, and each file's routing decision is logged with priority level and the specific matched keywords.
3. **Given** the orchestrator encounters an error processing one file (e.g., malformed frontmatter), **When** the error occurs, **Then** the failing file's status is reset to `needs_action`, the error is logged to `Logs/orchestrator.jsonl` with the filename and error detail, and the orchestrator continues processing the remaining files in the batch.
4. **Given** the orchestrator completes a run processing 10 files (3 filesystem, 4 Gmail, 3 WhatsApp), **When** the dashboard is updated, **Then** the summary table includes: files scanned (12), files processed (10), action calls attempted, files pending approval, files deferred (2), errors (0), and a per-source breakdown (filesystem: 3, gmail: 4, whatsapp: 3).
5. **Given** no `Needs_Action` files exist (folder empty or all files have `status: processing`), **When** the orchestrator runs, **Then** it logs "No pending files in Needs_Action/" and exits with a success status and no dashboard entry added.

---

### Edge Cases

- What happens when the Gmail watcher receives an email with no subject or body? The system MUST still create a `Needs_Action` file with a generated title based on sender and timestamp (e.g., `email-johndoe-20260226-093000`), and classify priority as "routine" by default.
- What happens when the WhatsApp watcher loses the browser session (QR code invalidated)? The system MUST detect the disconnection within 60 seconds, log the error to `Logs/whatsapp.jsonl`, remove the PID lock file, and exit with a clear message to re-authenticate — not hang or spin indefinitely.
- What happens when an action executor function raises an unexpected exception during live execution? The system MUST catch the exception, log the full error details (exception class, message, truncated traceback) to `Logs/actions.jsonl`, return a failure response with exit code 1, and not leave the vault in an inconsistent state (no partial files, no orphaned `.tmp` files).
- What happens when the scheduler configuration file is malformed or contains invalid time expressions (e.g., `"time": "25:99"`)? The system MUST validate hour (0-23) and minute (0-59) ranges on load, reject invalid entries with a specific error message identifying the invalid field and value, and continue operating with valid entries.
- What happens when the retry loop is configured with retries exceeding the hard cap (20)? The system MUST silently clamp to 20 and log a warning: "Max retries clamped from N to 20 (hard cap)".
- What happens when the orchestrator encounters a `Needs_Action` file with `status: processing` (from a previous interrupted run)? The system MUST skip it to avoid duplicate processing, log the skip with the filename, and not count it toward the batch size.
- What happens when multiple watchers create files simultaneously and the orchestrator runs concurrently? The system MUST process files sequentially within a batch (no parallel writes to vault) to prevent race conditions. Files created by watchers during an orchestrator run are picked up in the next run.
- What happens when the action executor is called with an action ID not in the registry (e.g., `--action nonexistent.action`)? The system MUST return a clear error message listing all available action IDs from the registry, log the failed lookup, and exit with code 1.

## Clarifications

### Session 2026-02-26

- Q: Should Silver tier use a different priority vocabulary (low/medium/high) or adopt the constitution's canonical scale (routine/sensitive/critical)? → A: Use the constitution's scale (routine|sensitive|critical) as the canonical frontmatter priority value for all Needs_Action .md files. Watchers map their internal keyword-matching logic (high-risk→critical, medium-risk→sensitive, default→routine) before writing frontmatter. The orchestrator reads only routine/sensitive/critical — no low/medium/high support needed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support three independent input watchers (filesystem, Gmail, WhatsApp) that each create `Needs_Action` files with source-specific frontmatter (`source: file-drop-watcher`, `source: gmail-watcher`, `source: whatsapp-watcher`) and urgency classification.
- **FR-002**: System MUST classify incoming items into three priority levels (routine, sensitive, critical) — the constitution-canonical vocabulary — using a shared, configurable risk-keyword list loaded from a single configuration source, applied consistently across all watchers and the orchestrator.
- **FR-003**: System MUST provide an action execution framework with at least 6 registered actions across 4 domains (email, social, calendar, documents) supporting per-action approval requirements, direct function call execution, and dry-run mode by default.
- **FR-004**: System MUST enforce an approval gate for sensitive actions: actions marked as approval-required MUST create a `Pending_Approval` file containing the action ID, parameters, request ID, and approval instructions, then block execution with exit code 2 until the corresponding file is moved to `Approved/`.
- **FR-005**: System MUST support live execution mode (triggered via explicit flag) that dynamically imports the action module, calls the registered function with provided parameters, and returns the result — only when approval requirements are satisfied or the action is approval-exempt.
- **FR-006**: System MUST provide a retry mechanism with configurable maximum retries (default 15, hard cap 20), exponential backoff with configurable base (default 2, range 1-5), and a maximum delay cap of 300 seconds between attempts.
- **FR-007**: System MUST immediately stop retrying on non-retryable errors (PermissionError, SystemExit, KeyboardInterrupt, and any error class listed in the no-retry configuration) and report the error class name and reason.
- **FR-008**: System MUST provide a scheduling daemon that creates `Needs_Action` files at configured times/intervals, supports daily, weekly, and cron-expression schedules, stores job definitions in a JSON configuration file, and runs with PID lock protection and signal handlers for clean shutdown.
- **FR-009**: System MUST handle missed scheduled triggers within a configurable grace period (default 3600 seconds) by executing the missed task on next startup rather than silently dropping it.
- **FR-010**: System MUST provide a central orchestrator that scans `Needs_Action/` for all `.md` files (excluding `.moved` files and files with `status: processing`), queues by priority (critical → sensitive → routine, then by creation time within same priority), performs inline risk assessment against the shared keyword list, and routes to Done/ (routine-risk), Pending_Approval/ (sensitive/critical-risk), or action execution. All priority values use the constitution-canonical vocabulary (routine|sensitive|critical).
- **FR-011**: System MUST support configurable batch sizes for orchestrator runs (default 10, hard cap 50) to prevent system overload, deferring excess files to the next run with a logged count.
- **FR-012**: System MUST log all watcher events to `Logs/<source>.jsonl`, action executions to `Logs/actions.jsonl`, retry attempts to `Logs/retry.jsonl`, scheduler triggers to `Logs/scheduler.jsonl`, orchestrator routing decisions to `Logs/orchestrator.jsonl`, and critical HITL action confirmations to `Logs/critical_actions.jsonl` — each entry containing ISO 8601 timestamp, component name, action, status, and detail fields.
- **FR-013**: System MUST update `Dashboard.md` after each orchestrator run by appending a summary table with: run timestamp, files scanned, files processed (moved to Done), action calls attempted, files pending approval, files deferred, errors encountered, and a per-source breakdown table.
- **FR-014**: System MUST maintain backward compatibility with all Bronze tier functionality: vault setup remains idempotent, filesystem watcher behavior is unchanged, vault-interact operations work identically, and check-and-process-needs-action routes files correctly — zero breaking changes to existing vault structure, file formats, or skill interfaces.
- **FR-015**: System MUST support process management for all long-running components (3 watchers + scheduler daemon) via PID lock files in `Logs/`, SIGTERM/SIGINT signal handlers for clean shutdown (PID file removal + log entry), and safe restart (stale PID file detection and cleanup).
- **FR-016**: System MUST redact sensitive fields (any key containing "password", "token", "secret", "api_key", "credential", or "auth") from all JSONL log entries, replacing values with `***REDACTED***`.
- **FR-017**: System MUST mark files with `status: processing` in frontmatter during active handling and reset to `needs_action` on error, preventing duplicate processing by concurrent orchestrator runs.

### Key Entities

- **Watcher**: A long-running process that monitors an external source (filesystem, email, messaging) for new events and creates `Needs_Action` files in the vault at `/home/safdarayub/Documents/AI_Employee_Vault/Needs_Action/`. Key attributes: source type, poll interval, authentication state, PID (stored in `Logs/<source>.pid`), operational status. Three instances: file-drop-watcher (Bronze, extended), gmail-watcher (Silver), whatsapp-watcher (Silver).
- **Action**: A registered executable function with defined parameters, approval requirements, and dry-run capability. Key attributes: action ID (format: `<domain>.<function>`, e.g., `email.send_email`), description, approval-required flag (boolean), module path (relative to `src/`), function name. Registered in the action registry.
- **Action Registry**: A JSON configuration file at `config/actions.json` listing all available actions. Contains at least 6 actions across 4 domains: email (send_email, draft_email), social (post_social), calendar (create_event, list_events), documents (generate_report). Each entry specifies description, HITL flag, module path, and function name.
- **Risk-Keyword Configuration**: A shared JSON file at `config/risk-keywords.json` containing two arrays: `high` (keywords triggering critical priority — e.g., payment, invoice, legal, delete) and `medium` (keywords triggering sensitive priority — e.g., email, send, meeting, approve). Watchers map high→critical, medium→sensitive, default→routine before writing frontmatter. Used by all watchers and the orchestrator for consistent classification.
- **Retry Loop**: A persistence mechanism wrapping a fallible task with exponential backoff. Key attributes: task callable, description, max retries (default 15, cap 20), backoff base (default 2), attempt count, outcome (success/failure/aborted). Logs to `Logs/retry.jsonl`.
- **Scheduled Task**: A recurring job definition stored in `config/schedules.json`. Key attributes: job ID, description, schedule type (daily/weekly/cron), time expression, timezone, enabled flag, next run time. Triggers by creating `Needs_Action` files with `source: daily-scheduler`.
- **Orchestrator Run**: A batch processing cycle with a unique run ID (format: `orch-YYYYMMDD-HHMMSS`). Key attributes: batch size (default 10, cap 50), files scanned, priority queue (canonical values: critical → sensitive → routine), routing decisions (done/pending_approval/done_with_action/pending_approval_with_action), per-source statistics, error count.

### Assumptions

- Bronze tier is fully operational: vault structure exists at `/home/safdarayub/Documents/AI_Employee_Vault` with all 7 folders, `Dashboard.md`, and `Company_Handbook.md`; filesystem watcher works; vault-interact, process-needs-action, and check-and-process-needs-action skills are functional.
- Gmail OAuth2 credentials (`credentials.json`) are pre-configured by the developer following the setup guide at `.claude/skills/gmail-watcher/references/gmail_api_setup.md`; the system handles token refresh but not initial Google Cloud Console setup.
- WhatsApp Web requires an initial manual QR code scan for session authentication (stored in `~/.whatsapp-watcher-session/`); subsequent runs reuse the persistent browser context.
- All watchers, scheduler, and orchestrator run on the same machine with direct filesystem access to the vault — no distributed or networked deployment.
- The developer manually triggers the orchestrator or sets it up as a recurring scheduled task — event-driven orchestration (watcher auto-triggers orchestrator) is Gold tier.
- Action modules in `src/actions/` are created by the developer; the action executor discovers them via `config/actions.json` and imports via `importlib`. At least `src/actions/email.py` (send_email, draft_email) exists as a reference implementation.
- The 4 existing subagents (gmail-analyzer, whatsapp-handler, action-planner, risk-assessor) in `.claude/agents/` are available for Claude Code to invoke during processing but are not directly called by Python scripts — they operate within Claude Code's agent framework.
- The system operates on a single-user local machine — no concurrent multi-user access.

### Constraints

- **C-001**: All vault operations MUST be scoped to `/home/safdarayub/Documents/AI_Employee_Vault`. No reads, writes, or moves to paths outside this root.
- **C-002**: All file writes MUST use atomic write (write to `.tmp` then `os.rename()`) to prevent corruption from interrupted writes.
- **C-003**: No file deletion allowed. Move operations use rename-to-`.moved` pattern on the source file.
- **C-004**: Dry-run mode MUST be the default for all action execution. Live mode requires explicit opt-in via flag AND satisfied approval requirements.
- **C-005**: Maximum 20 retries per task (hard cap, non-configurable). Maximum 300-second delay between retries.
- **C-006**: Maximum 50 files per orchestrator batch (hard cap). Default batch size is 10.
- **C-007**: All long-running processes MUST use PID lock files in `Logs/` and handle SIGTERM/SIGINT for clean shutdown.
- **C-008**: No external cloud dependencies. All processing is local. No data leaves the machine unless an action is explicitly approved and executed in live mode.
- **C-009**: Implementation time budget: 12–20 hours maximum. Silver tier builds incrementally on Bronze — no rewriting existing functionality.
- **C-010**: All credentials (OAuth tokens, API keys) stored outside the vault and git repository (via `.env`, OS keychain, or `credentials.json` in project root). Never stored in vault markdown files or committed to version control.

### Not in Scope

- Full Odoo ERP integration or CEO briefing document generation (Gold tier).
- Cloud deployment, remote VM hosting, or Git-based vault synchronization (Platinum tier).
- Event-driven orchestration (watcher triggers orchestrator automatically) — orchestration is manually triggered or scheduled.
- Parallel or concurrent file processing within a single orchestrator batch — files are processed sequentially.
- Custom AI model training, fine-tuning, or ethical AI governance (out of scope entirely).
- Real-time notifications or push alerts to the developer (out of scope — developer checks dashboard or logs).
- Advanced subagent orchestration beyond the 4 existing subagents (gmail-analyzer, whatsapp-handler, action-planner, risk-assessor).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each of the three watchers creates correctly formatted `Needs_Action` files within its expected latency: filesystem watcher within 5 seconds, Gmail watcher within 60 seconds (one poll cycle), WhatsApp watcher within 60 seconds. Each file contains valid YAML frontmatter with all 6 required fields (title, created, tier, source, priority, status). Priority classification for the same keyword (e.g., "invoice") produces the same result (critical) regardless of which watcher processes it — verified by cross-watcher keyword test.
- **SC-002**: The action executor correctly handles all three action lifecycle states across the 6 registered actions (email.send_email, email.draft_email, social.post_social, calendar.create_event, calendar.list_events, documents.generate_report): dry-run returns a descriptive result without side effects and exits with code 0; approval-blocked creates a `Pending_Approval` file and exits with code 2; live-approved calls the function, logs the result to `Logs/actions.jsonl`, and exits with code 0 on success or code 1 on failure.
- **SC-003**: The retry mechanism recovers from transient failures with exponential backoff. Verified by a test task that fails twice then succeeds on the 3rd attempt: attempt 1 fails immediately, attempt 2 fires after ~2 seconds (backoff base 2, exponent 1), attempt 3 fires after ~4 seconds (backoff base 2, exponent 2). All 3 attempts are logged to `Logs/retry.jsonl` with timestamps proving increasing delays. Non-retryable errors (PermissionError) abort immediately with zero delay — verified by a test task raising PermissionError on first attempt.
- **SC-004**: The scheduler creates `Needs_Action` files within 5 seconds of the configured trigger time. Verified by: (a) adding a task scheduled 1 minute in the future, confirming `Needs_Action` file appears at the scheduled time; (b) starting the scheduler 30 minutes after a missed trigger time, confirming the missed task executes within 60 seconds of scheduler start (grace period). PID lock prevents duplicate instances — verified by attempting to start a second instance and confirming it exits with an error message containing the existing PID.
- **SC-005**: The orchestrator processes a test batch of 12 `Needs_Action` files from 3 sources (4 filesystem, 4 Gmail, 4 WhatsApp) with mixed priorities (4 critical, 4 sensitive, 4 routine) in a single run with batch size 10. Verification: exactly 10 files processed (all 4 critical first, then 4 sensitive, then 2 of 4 routine), 2 routine-priority files deferred. Critical/sensitive files (containing keywords like "payment", "delete") route to `Pending_Approval/`, routine files route to `Done/`. Dashboard summary shows accurate counts: scanned=12, processed=10 (split by route), deferred=2, errors=0, with per-source breakdown matching (filesystem: ~3, gmail: ~4, whatsapp: ~3).
- **SC-006**: System runs for 30 continuous minutes with all three watchers active, the scheduler daemon running with at least 1 configured task, and a minimum of 15 events processed through the full pipeline (at least 3 per source: filesystem, Gmail, WhatsApp, plus scheduler-generated). The orchestrator is triggered at least 3 times during the run (manually or via schedule). Zero unhandled exceptions across all components. Zero orphaned files (every `Needs_Action` file reaches either `Done/` or `Pending_Approval/`). Verified by: checking all JSONL logs for error-level entries, counting files in `Needs_Action/` (should be 0 or only files from the most recent un-processed batch), and confirming all PID files are cleaned up on shutdown.
- **SC-007**: Every operation produces a corresponding log entry in the appropriate JSONL file. Verification: count of watcher-created files equals count of entries in source-specific logs; count of orchestrator-processed files equals count of entries in `Logs/orchestrator.jsonl`; count of action executor calls equals count of entries in `Logs/actions.jsonl`; count of retry attempts equals count of entries in `Logs/retry.jsonl`. 100% audit coverage — zero unlogged operations.
- **SC-008**: No sensitive field values appear in any JSONL log file. Verified by running a text search across all `Logs/*.jsonl` files for known test credential values (e.g., the OAuth client secret, any password used in test params). All matches MUST show `***REDACTED***` instead of the actual value. Additionally, `credentials.json` and `token.json` are never referenced by absolute path in any log entry.
- **SC-009**: All Bronze tier functionality continues unchanged after Silver tier implementation. Verified by re-running the Bronze tier test plan (`tests/manual/bronze-tier-test-plan.md`): vault setup is idempotent (SC-001 from Bronze), filesystem watcher creates correct files within 5 seconds (SC-002 from Bronze), all 6 vault-interact operations succeed (SC-003 from Bronze), and check-and-process-needs-action routes files correctly (SC-004 from Bronze). Zero regressions — all 9 Bronze success criteria pass.
- **SC-010**: The 4 existing subagents (gmail-analyzer, whatsapp-handler, action-planner, risk-assessor) remain functional and invocable by Claude Code. Verified by: (a) asking Claude Code to invoke the gmail-analyzer subagent on a test email `Needs_Action` file and receiving a structured analysis; (b) asking Claude Code to invoke the action-planner subagent on a task file and receiving a step-by-step plan with action calls identified.
