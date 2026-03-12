# Tasks: Platinum Tier — Cloud-Local Hybrid Operation

**Input**: Design documents from `/specs/004-platinum-tier/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

**Tests**: Unit tests are included as they are referenced in the implementation plan's testing strategy and are critical for verifying safety-critical role gating and concurrency control.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, Platinum folder structure, and shared utilities that all user stories depend on.

- [x] T001 Update vault folder structure in src/setup_vault.py to add Platinum folders: `Needs_Action/gmail/`, `Needs_Action/whatsapp/`, `Needs_Action/scheduler/`, `Needs_Action/manual/`, `In_Progress/cloud/`, `In_Progress/local/`, `Pending_Approval/gmail/`, `Pending_Approval/social/`, `Pending_Approval/odoo/`, `Pending_Approval/general/`, `Updates/`, `Rejected/` — conditional on FTE_ROLE being set (FR-020, FR-021, FR-022, FR-030)
- [x] T002 [P] Create src/role_gate.py with `get_fte_role()`, `is_cloud()`, `is_local()`, `enforce_role_gate()`, `validate_startup()` — reads FTE_ROLE from os.environ, raises SystemExit if missing/invalid, blocks sensitive/critical actions when cloud (FR-005, FR-006, FR-008)
- [x] T003 [P] Update src/correlation.py to generate new format `corr-YYYY-MM-DD-XXXXXXXX` (8 hex chars), update CORRELATION_ID_PATTERN regex, keep `is_valid_correlation_id()` backward-compatible with old 4-hex format (FR-017)
- [x] T004 [P] Update src/vault_helpers.py to import role_gate.get_fte_role and add `agent` field to every `log_operation()` and `log_error()` call
- [x] T005 [P] Create config/.env.example documenting all Platinum env vars: FTE_ROLE, VAULT_PATH, PROJECT_ROOT, GIT_SYNC_INTERVAL_SECONDS, DRY_RUN, FTE_CLOUD_HOST, RALPH_MAX_ITERATIONS, ODOO_HOST, ODOO_PORT

**Checkpoint**: Core utilities ready — role gating, correlation IDs, and vault structure available for all subsequent phases.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Git sync and claim-by-move — the two infrastructure components that ALL Platinum user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T006 Create src/git_sync.py with `sync_cycle()` (pull --rebase → stage → commit → push), `queue_offline_commits()`, and `run_sync_loop()` daemon. Handle push failures with 3 retries, log to Logs/sync.jsonl, create Needs_Action/manual/ on persistent failure. Use GIT_SYNC_INTERVAL_SECONDS env var (default 60). Include git stash/pop around rebase (FR-001, FR-002, FR-003, FR-004)
- [x] T007 Create src/claim_move.py with `claim_file()` using os.rename() for atomic move from Needs_Action/<domain>/ to In_Progress/<role>/, `complete_file()` for moving to next folder with frontmatter update, `scan_needs_action()` to list files sorted by creation timestamp. Handle FileNotFoundError as "already claimed" (FR-009, FR-010, FR-011)
- [x] T008 [P] Create tests/unit/test_role_gate.py — test: missing FTE_ROLE raises SystemExit, invalid value raises SystemExit, cloud blocks sensitive actions, cloud allows routine, local allows all risk levels, validate_startup() returns role string
- [x] T009 [P] Create tests/unit/test_git_sync.py — test: normal sync cycle, push failure with retry, offline commit queueing, conflict detection and Needs_Action/manual/ creation
- [x] T010 [P] Create tests/unit/test_claim_move.py — test: successful claim moves file, already-claimed returns None, scan_needs_action returns sorted list, complete_file updates frontmatter status

**Checkpoint**: Foundation ready — git sync and claim-by-move infrastructure in place. User story implementation can now begin.

---

## Phase 3: User Story 6 — Secrets Isolation and .gitignore Enforcement (Priority: P1) 🔒

**Goal**: Ensure zero secrets can leak into git, protecting the trust model before any syncing begins.

**Independent Test**: Run `git add .env && git commit` — verify pre-commit hook blocks it. Scan git history for secret file patterns — verify zero matches.

### Implementation

- [x] T011 [US6] Create hooks/pre-commit bash script that validates staged files against hardcoded exclusion patterns (`.env`, `*.session`, `*.token`, `*.key`, `*.pem`, `credentials/`, `secrets/`). Print "BLOCKED: <file> matches secrets exclusion pattern" and exit 1 on violation. Independent of .gitignore (FR-014, FR-015)
- [x] T012 [P] [US6] Verify vault .gitignore contains all constitution-mandated patterns: `.env`, `*.session`, `*.token`, `*.key`, `*.pem`, `credentials/`, `secrets/`, `__pycache__/`. Add any missing patterns.
- [x] T013 [US6] Add installation step for pre-commit hook: document `cp hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit` in config/.env.example and specs/004-platinum-tier/quickstart.md
- [x] T013b [P] [US6] Add cloud VM secrets audit to src/git_sync.py — on each sync cycle startup (or as a standalone function), scan vault directory for files matching secrets patterns (`.env`, `*.session`, `*.token`, `*.key`, `*.pem`, `credentials/`). If found, log a CRITICAL security event to Logs/sync.jsonl and create Needs_Action/manual/ alert. This is the runtime Layer 3 defense per ADR-0012 (FR-016).

**Checkpoint**: Secrets isolation enforced at all 3 layers (.gitignore + pre-commit hook + cloud runtime audit) — safe to begin git sync between cloud and local.

---

## Phase 4: User Story 2 — Git-Based Vault Sync Between Cloud and Local (Priority: P1) 🎯 MVP

**Goal**: Bidirectional vault sync via git so cloud and local agents can communicate through file-based IPC.

**Independent Test**: Create file on cloud VM, commit/push. Run sync on local — verify file appears. Reverse direction. Disconnect local, make changes on both sides, reconnect — verify both sets of changes present.

### Implementation

- [x] T014 [US2] Add sync.jsonl and sync-conflicts.jsonl log file paths to vault_helpers.py constants and setup_vault.py Logs/ folder creation
- [x] T015 [US2] Create config/ecosystem.cloud.config.js with 3 PM2 apps: cloud-git-sync, cloud-gmail-watcher, cloud-scheduler. All with FTE_ROLE=cloud, /home/ubuntu/AI_Employee_Vault paths, max_restarts 5/60s, ~/fte-env/bin/python3 interpreter (FR-023, FR-024)
- [x] T016 [US2] Update config/ecosystem.config.js to add FTE_ROLE=local to every existing app's env block (FR-030)

**Checkpoint**: Git sync operational — vault changes propagate between cloud and local within configured interval.

---

## Phase 5: User Story 3 — Role-Based Action Gating (Priority: P1) 🛡️

**Goal**: Cloud agent cannot execute sensitive/critical actions — only draft to Pending_Approval/. Local operates with full Gold-tier capabilities.

**Independent Test**: Set FTE_ROLE=cloud, call send_email action — verify blocked and draft created. Set FTE_ROLE=local — verify same action executes normally through HITL gate.

### Implementation

- [x] T017 [US3] Update src/mcp/base_server.py — import role_gate, add `role_gated_action()` function that checks FTE_ROLE and risk level, creates draft in Pending_Approval/ when cloud + sensitive/critical, proceeds through HITL when local. Add agent and correlation_id to frontmatter.
- [x] T018 [P] [US3] Update src/mcp/email_server.py — call enforce_role_gate("email_send", "sensitive") before existing HITL logic. When FTE_ROLE=cloud, return draft result instead of attempting send.
- [x] T019 [P] [US3] Update src/mcp/social_server.py — call enforce_role_gate() on post_facebook, post_instagram, post_twitter actions (all sensitive).
- [x] T020 [P] [US3] Update src/mcp/odoo_server.py — call enforce_role_gate("odoo_create_invoice", "critical") and enforce_role_gate("odoo_register_payment", "critical"). Read-only tools unchanged.
- [x] T021 [US3] Update src/actions/email.py, src/actions/social.py, src/actions/calendar_actions.py — add FTE_ROLE gate on write/send actions using enforce_role_gate() (FR-008 defense-in-depth)
- [x] T022 [US3] Update config/actions.json — add `fte_role_minimum` field per action defining minimum role required (cloud=routine only, local=all)

**Checkpoint**: Role gating enforced at both MCP server and action executor levels — cloud cannot execute sensitive/critical actions.

---

## Phase 6: User Story 1 — Always-On Email Triage While Laptop Is Off (Priority: P1) 🎯 Core Demo

**Goal**: Cloud agent detects email → drafts reply → writes to Pending_Approval/. Local agent syncs → user approves → email sent → task moved to Done/.

**Independent Test**: Drop test email while local is stopped. Verify cloud creates Pending_Approval/gmail/*.md with correct frontmatter. Start local, move to Approved/, verify email sent and task in Done/.

### Implementation

- [x] T023 [US1] Update .claude/skills/gmail-watcher/scripts/gmail_poll.py — import role_gate, call validate_startup() on start, write to Needs_Action/gmail/ (domain subfolder), add agent and tier=platinum to frontmatter, use SCOPES_READONLY when cloud, never call mark_as_read() when cloud, enter circuit breaker on token refresh failure with Needs_Action/manual/ alert (FR-017)
- [x] T024 [US1] Create src/approval_watcher.py with `process_approved()` — scan Approved/ for files, parse frontmatter for action type, dispatch to correct action handler (email.send_email, social.post_social, etc.), move to Done/ on success (FR-027), move to Needs_Action/manual/ on failure (FR-028). Guard: refuse to run when FTE_ROLE=cloud.
- [x] T025 [US1] Update .claude/skills/daily-scheduler/scripts/scheduler_daemon.py — import role_gate, add agent field to frontmatter, set tier=platinum, write to Needs_Action/scheduler/ instead of Needs_Action/ (domain subfolder)
- [x] T026 [US1] Create tests/integration/test_e2e_platinum.py — test the full lifecycle: create mock Needs_Action/gmail/ file → claim → draft to Pending_Approval/gmail/ → move to Approved/ → execute → verify Done/ with correlation_id trail in logs

**Checkpoint**: Core Platinum demo working — email triage operates while laptop is off, approval flow completes on reconnection.

---

## Phase 7: User Story 4 — Claim-by-Move Concurrency Control (Priority: P2)

**Goal**: First agent to detect a task file claims it via atomic move — prevents duplicate processing.

**Independent Test**: Place file in Needs_Action/gmail/. Simulate both agents claiming — verify exactly one succeeds, other logs "file already claimed, skipping".

### Implementation

- [x] T027 [US4] Integrate claim_move.claim_file() into the cloud orchestrator flow — before processing any Needs_Action file, attempt claim to In_Progress/cloud/. On failure (None return), log and skip. Update .claude/skills/central-orchestrator/scripts/orchestrator.py
- [x] T028 [US4] Integrate claim_move.claim_file() into local agent processing — before processing Needs_Action files, attempt claim to In_Progress/local/. Update orchestrator.py local flow path.
- [x] T029 [US4] Integrate claim_move.complete_file() into both agent flows — after processing, move from In_Progress/<role>/ to appropriate destination (Pending_Approval/, Done/). Update frontmatter status field.

**Checkpoint**: Concurrent operation safe — zero duplicate processing when both agents run simultaneously.

---

## Phase 8: User Story 5 — Single-Writer Dashboard Updates (Priority: P2)

**Goal**: Cloud writes incremental updates to Updates/. Local merges into Dashboard.md. No merge conflicts on Dashboard.md.

**Independent Test**: Cloud processes 3 emails, writes 3 update files. Local syncs, merges into Dashboard.md, deletes update files. Verify Dashboard.md has all 3 and Updates/ is empty.

### Implementation

- [x] T030 [US5] Create src/dashboard_merger.py with `write_update()` (cloud-only: creates Updates/dashboard-update-<ISO-timestamp>.md with frontmatter) and `merge_updates()` (local-only: reads Updates/*.md chronologically, appends to Dashboard.md under ## Cloud Updates section, deletes processed files) (FR-012, FR-013)
- [x] T031 [US5] Integrate dashboard_merger.write_update() into cloud agent flow — call after task processing completes (after drafting, after claiming, etc.)
- [x] T032 [US5] Integrate dashboard_merger.merge_updates() into local agent sync cycle — call after git pull, before git commit
- [x] T033 [P] [US5] Create tests/unit/test_dashboard_merger.py — test: single update merge, multiple chronological merge, empty Updates/ returns 0, cloud role creates update file, local role merges and deletes

**Checkpoint**: Dashboard.md stays conflict-free — cloud updates flow through Updates/ folder.

---

## Phase 9: User Story 8 — Cloud VM 24/7 Daemon Operation (Priority: P2)

**Goal**: Cloud services run as PM2-managed daemons with auto-restart, restart limits, and auto-start on boot.

**Independent Test**: SSH into cloud VM, verify pm2 list shows all services running. Kill one — verify restart within 5s. Check Logs/health.json for status.

### Implementation

- [x] T034 [US8] Finalize config/ecosystem.cloud.config.js — verify all paths, env vars, restart policies are correct for E2.1.Micro (already drafted in T015, may need tuning)
- [x] T035 [US8] Update src/circuit_breaker.py (or health monitoring) to add `agent` field to Logs/health.json entries, add git-sync as a tracked service
- [x] T036 [US8] Create cloud VM first-boot setup script or document in specs/004-platinum-tier/quickstart.md: install PM2, install Python deps, create .env, copy gmail token, create vault folders, install pre-commit hook, configure PM2 startup (FR-025)

**Checkpoint**: Cloud VM runs 24/7 with auto-recovery — meets SC-007 90%+ uptime target.

---

## Phase 10: User Story 7 — Correlation ID Tracking Across Agents (Priority: P3)

**Goal**: Every cross-agent task carries a correlation ID through its entire lifecycle, enabling end-to-end audit trails.

**Independent Test**: Process email through full lifecycle. Grep JSONL logs on both sides for correlation ID — verify every stage logged with same ID.

### Implementation

- [x] T037 [US7] Ensure all Needs_Action file creators (gmail_poll.py, scheduler_daemon.py, orchestrator.py) generate and include correlation_id in YAML frontmatter using updated correlation.py format (FR-017)
- [x] T038 [US7] Ensure claim_move.py preserves correlation_id when moving files between folders — never regenerate, always read from existing frontmatter and carry forward (FR-019)
- [x] T039 [US7] Ensure all JSONL log entries in vault_helpers.py, git_sync.py, approval_watcher.py, dashboard_merger.py include correlation_id field when processing a specific task (FR-018)
- [x] T040 [US7] Verify end-to-end: create a test that generates a task with known correlation_id, moves through all stages, and asserts the ID appears in every log entry at every stage (FR-018, SC-008)

**Checkpoint**: Complete audit trail — any task can be traced across both agents by correlation ID.

---

## Phase 11: Rejection Flow & Stale Detection (Priority: P2/P3)

**Goal**: Handle rejected drafts and detect stale files that need attention.

### Implementation

- [x] T041 [P] Create src/rejection_handler.py with `reject_file()` (local-only: move from Pending_Approval/ to Rejected/, add status=rejected and rejection_reason to frontmatter, log with correlation_id) and `process_rejections()` (cloud-only: scan Rejected/, re-draft if actionable or escalate to Needs_Action/manual/) (FR-031, FR-032)
- [x] T042 [P] Create src/stale_detector.py with `detect_stale_files()` (scan Pending_Approval/ >48h, Rejected/ >7d) and `update_dashboard_stale()` (local-only: add/update ## Stale Items section in Dashboard.md) (FR-033, FR-035)
- [x] T043 [P] Create tests/unit/test_stale_detector.py — test: fresh files not flagged, 49h pending flagged, 8d rejected flagged, stale section updated in Dashboard.md

**Checkpoint**: Rejection and stale detection working — no tasks fall through the cracks.

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Gold backward compatibility verification, security audit, and cloud deployment.

- [x] T044 Verify Gold-tier backward compatibility: run all existing Gold-tier workflows with FTE_ROLE=local, confirm no regressions (FR-029, FR-030, SC-006). Check: watchers, orchestrator, CEO briefing, health monitoring, Ralph Wiggum retries, circuit breakers all function identically.
- [x] T045 Run security scan: `git log --all --diff-filter=A --name-only | grep -E '\.(env|session|token|key|pem)$'` — verify zero secrets in git history (SC-004). Test pre-commit hook blocks `git add .env && git commit`.
- [x] T046 Deploy to cloud VM: execute first-boot setup (T036), transfer gmail read-only token.json via scp, start PM2 services, verify pm2 list shows all healthy.
- [x] T047 Run end-to-end offline email demo: send real test email while local is stopped → verify cloud drafts → start local → approve → verify send → verify Done/ with correlation trail (SC-003, SC-010)
- [x] T048 [P] Update specs/004-platinum-tier/quickstart.md with final setup instructions, troubleshooting guide, and demo script

**Checkpoint**: Platinum tier fully operational on both cloud VM and local machine.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 completion — BLOCKS all user stories
- **Phase 3 (US6 Secrets)**: Depends on Phase 1 — must complete before Phase 4 (git sync)
- **Phase 4 (US2 Git Sync)**: Depends on Phase 2 + Phase 3
- **Phase 5 (US3 Role Gating)**: Depends on Phase 1 (role_gate.py)
- **Phase 6 (US1 Email Triage)**: Depends on Phase 4 + Phase 5
- **Phase 7 (US4 Claim-by-Move)**: Depends on Phase 2 (claim_move.py exists) + Phase 5
- **Phase 8 (US5 Dashboard)**: Depends on Phase 4
- **Phase 9 (US8 Daemon)**: Depends on Phase 4 + Phase 6
- **Phase 10 (US7 Correlation)**: Depends on Phase 1 (correlation.py update) — can run parallel with later phases
- **Phase 11 (Rejection/Stale)**: Depends on Phase 5 + Phase 6
- **Phase 12 (Polish)**: Depends on ALL previous phases

### Critical Path

```
Phase 1 → Phase 2 → Phase 3 (Secrets) → Phase 4 (Git Sync) → Phase 6 (Email Triage) → Phase 12 (Polish)
                  ↘ Phase 5 (Role Gating) ↗
```

### User Story Dependencies

- **US6 (Secrets)**: Independent — can start after Phase 1
- **US2 (Git Sync)**: Depends on US6 (secrets must be enforced before syncing)
- **US3 (Role Gating)**: Independent — can start after Phase 1, parallel with US6
- **US1 (Email Triage)**: Depends on US2 + US3
- **US4 (Claim-by-Move)**: Depends on US3 (role-aware claiming)
- **US5 (Dashboard)**: Depends on US2 (sync needed for cloud updates to reach local)
- **US7 (Correlation)**: Low dependency — can be woven in throughout
- **US8 (Daemon)**: Depends on US2 + US1 (need sync + watchers working)

### Parallel Opportunities

Phase 1: T002, T003, T004, T005 are all independent files — run in parallel.
Phase 2: T008, T009, T010 (tests) can run parallel with T006, T007 (implementation).
Phase 3 + Phase 5: Can run in parallel (secrets + role gating are independent).
Phase 7 + Phase 8 + Phase 10: Can run in parallel after their dependencies are met.
Phase 11: T041, T042, T043 are all independent files — run in parallel.

---

## Parallel Example: Phase 1 (Setup)

```bash
# All these can run simultaneously:
Task T002: "Create src/role_gate.py"
Task T003: "Update src/correlation.py"
Task T004: "Update src/vault_helpers.py"
Task T005: "Create config/.env.example"
# Then T001 (setup_vault.py) can run after — it may reference role_gate
```

## Parallel Example: Phase 5 (Role Gating)

```bash
# After T017 (base_server.py), these can run simultaneously:
Task T018: "Update email_server.py"
Task T019: "Update social_server.py"
Task T020: "Update odoo_server.py"
```

---

## Implementation Strategy

### MVP First (Core Demo — Phases 1-6)

1. Complete Phase 1: Setup (role_gate, correlation, vault folders)
2. Complete Phase 2: Foundational (git sync, claim-by-move)
3. Complete Phase 3: Secrets isolation (pre-commit hook)
4. Complete Phase 4: Git sync deployment
5. Complete Phase 5: Role gating on all action executors
6. Complete Phase 6: Email triage flow
7. **STOP and VALIDATE**: Run end-to-end offline email demo (SC-003, SC-010)
8. Deploy to cloud VM for live demo

### Incremental Delivery

1. Phases 1-6 → MVP: Offline email triage demo works
2. Add Phase 7 (Claim-by-Move integration) → Concurrent safety
3. Add Phase 8 (Dashboard updates) → User situational awareness
4. Add Phase 9 (PM2 daemon) → True 24/7 reliability
5. Add Phase 10 (Correlation IDs end-to-end) → Full audit trail
6. Add Phase 11 (Rejection/Stale) → Edge case handling
7. Phase 12 → Final polish, regression tests, live demo

---

## Notes

- [P] tasks = different files, no dependencies on each other
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Phase 3 (Secrets) is ordered before Phase 4 (Git Sync) intentionally — never sync without protection
