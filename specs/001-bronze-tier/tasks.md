# Tasks: Bronze Tier — Personal AI Employee

**Input**: Design documents from `/specs/001-bronze-tier/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Manual end-to-end test scenarios only (no automated test framework for Bronze). Verification tasks are included as checkpoints within each user story phase.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create project directory structure and install dependencies

- [x] T001 Create project directory structure: `src/`, `vault_content/`, `config/`, `tests/manual/` at repository root per plan.md project structure
- [x] T002 [P] Install Python dependencies: `pip install watchdog` and verify import works with Python 3.13+

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared utility module that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: Both `setup_vault.py` and `file_drop_watcher.py` depend on this module

- [x] T003 Implement shared utilities module in `src/vault_helpers.py` with the following functions:
  - `resolve_vault_path()` — resolve `VAULT_PATH` env var with default `/home/safdarayub/Documents/AI_Employee_Vault`, validate absolute path (FR-008)
  - `validate_path(target, vault_root)` — check target resolves within vault root, raise `PathViolationError` if not (FR-008)
  - `log_operation(log_file, component, action, status, detail, **extra)` — append one JSON line to specified `.jsonl` file with ISO 8601 timestamp and required fields per `contracts/log-formats.md` (FR-012)
  - `log_error(component, action, detail, error, traceback_str)` — append to `Logs/errors.jsonl` with error class name and traceback (FR-012)
  - `generate_frontmatter(**fields)` — return YAML frontmatter string via f-string formatting per research.md R4 (no PyYAML dump)
  - `atomic_write(target_path, content)` — write to `{target}.tmp` then `os.rename()` per research.md R3, constitution Principle VI (D4)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Vault Foundation Setup (Priority: P1) 🎯 MVP

**Goal**: Developer runs `setup_vault.py` and gets a fully initialized Obsidian vault with 7 folders, `Dashboard.md`, and `Company_Handbook.md`

**Independent Test**: Run `python src/setup_vault.py`, then `ls /home/safdarayub/Documents/AI_Employee_Vault/` — verify all 7 folders and 2 files exist. Run again and verify existing files unchanged (SC-001).

### Implementation for User Story 1

- [x] T004 [P] [US1] Create Dashboard template in `vault_content/dashboard-template.md` matching the exact format from `contracts/dashboard-format.md`: YAML frontmatter (`title`, `created`, `tier: bronze`, `status: active`), Status Overview section, empty Processing History section with HTML comment placeholder
- [x] T005 [P] [US1] Create Company Handbook template in `vault_content/company-handbook.md` with categorized action rules per FR-003: Routine actions (at least 2 examples: file organization, report generation), Sensitive actions (at least 2 examples: send email, post to social media), Critical actions (at least 2 examples: execute payment, delete files). Include YAML frontmatter (`title`, `created`, `tier: bronze`, `status: active`)
- [x] T006 [US1] Implement idempotent vault setup script in `src/setup_vault.py` per FR-001, FR-002, FR-003, FR-017:
  - Resolve vault path via `vault_helpers.resolve_vault_path()`
  - Create 7 folders if missing: `Inbox/`, `Needs_Action/`, `Done/`, `Pending_Approval/`, `Approved/`, `Plans/`, `Logs/` (FR-001)
  - Copy `Dashboard.md` from `vault_content/dashboard-template.md` if not exists, injecting current ISO 8601 timestamp into `created` field (FR-002)
  - Copy `Company_Handbook.md` from `vault_content/company-handbook.md` if not exists (FR-003)
  - Use `vault_helpers.atomic_write()` for all file creation (D4)
  - Use `vault_helpers.log_operation()` to log each action to `Logs/vault_operations.jsonl` with `component: "setup-vault"` (FR-012)
  - Skip existing folders/files with log entry `status: "skipped"` (FR-017)
  - Print summary: "N folders and M files created" on completion
- [x] T007 [US1] Verify US1: Run `python src/setup_vault.py` against empty vault path, verify 7 folders + 2 files created. Run again, verify no files overwritten and log shows `skipped` entries. Verify `Dashboard.md` matches `contracts/dashboard-format.md` format. Verify `Company_Handbook.md` has 3 categories with 2+ examples each. (SC-001)

**Checkpoint**: Vault is initialized and ready for watcher and skill operations

---

## Phase 4: User Story 2 — File Drop Watcher (Priority: P2)

**Goal**: A Watchdog-based filesystem watcher monitors `~/Desktop/DropForAI`, detects new files, and creates metadata `.md` files in `Needs_Action/` with valid YAML frontmatter

**Independent Test**: Start watcher, drop a `.txt` file into `~/Desktop/DropForAI`, verify a `dropped-*.md` file appears in `Needs_Action/` within 5 seconds with correct frontmatter (SC-002).

**Depends on**: Phase 3 (vault must exist for `Needs_Action/` folder and `Logs/`)

### Implementation for User Story 2

- [x] T008 [US2] Implement core watcher and metadata file creation in `src/file_drop_watcher.py`:
  - Subclass `watchdog.events.FileSystemEventHandler` with custom `on_created` handler
  - Filter: only `event.is_directory == False` (ignore folder creation events, FR-004 AS4)
  - Debounce: 0.5s delay before processing to handle temp files (research.md R1)
  - Generate Needs_Action filename: `dropped-{original_stem}-{YYYYMMDD-HHMMSS}.md` per `contracts/needs-action-format.md`
  - Generate file content: YAML frontmatter (`title`, `created`, `tier: bronze`, `source: file-drop-watcher`, `priority: routine`, `status: needs_action`) + three body sections (What happened, Suggested action, Context with original path, file type, file size) per FR-005 and `contracts/needs-action-format.md`
  - Write via `vault_helpers.atomic_write()` to `Needs_Action/` (D4)
  - Log to `vault_operations.jsonl` via `vault_helpers.log_operation()` with `component: "file-drop-watcher"` (FR-012)
  - On error: log to `errors.jsonl` via `vault_helpers.log_error()`, continue watching (FR-004 AS5)
- [x] T009 [US2] Add PID lock management and signal handlers to `src/file_drop_watcher.py`:
  - On startup: check `Logs/watcher.pid` — if exists and PID alive (`os.kill(pid, 0)`), exit with error "Watcher already running (PID: N)" (FR-019, research.md R2)
  - If PID file exists but process is dead, log warning and overwrite
  - Write current PID to `Logs/watcher.pid`
  - Register `signal.SIGTERM` and `signal.SIGINT` handlers that: stop Observer, remove PID file, log clean shutdown, exit 0
  - On unclean exit: PID file remains (stale lock — detected on next startup)
- [x] T010 [US2] Add CLI argument parsing and main entry point to `src/file_drop_watcher.py`:
  - Use `argparse` with: `--drop-folder` (default: `DROP_FOLDER` env var or `~/Desktop/DropForAI`), `--vault-path` (default: `VAULT_PATH` env var or `/home/safdarayub/Documents/AI_Employee_Vault`) per research.md R6
  - Precedence: CLI arg > env var > default
  - Create drop folder if it doesn't exist, log warning (edge case from spec)
  - Validate vault path exists (exit with error if not — must run `setup_vault.py` first)
  - Start `watchdog.observers.Observer`, schedule handler on drop folder, print "Watching {path} for new files..."
  - Block on `observer.join()` in main thread
- [x] T011 [US2] Verify US2: Start watcher (`python src/file_drop_watcher.py`), drop a `.txt` file into `~/Desktop/DropForAI`, verify `Needs_Action/dropped-*.md` appears within 5s with all 6 frontmatter fields valid. Drop 3 files quickly and verify 3 separate metadata files created. Verify original files untouched. Stop watcher with Ctrl+C and verify PID file removed. (SC-002)

**Checkpoint**: Watcher creates correct Needs_Action files and handles startup/shutdown cleanly

---

## Phase 5: User Story 3 — Claude Code Vault Read/Write (Priority: P3)

**Goal**: Verify that the vault-interact skill correctly reads, writes, appends, lists, moves, and creates files in the vault — all with JSONL logging and path validation

**Independent Test**: Ask Claude Code to read `Company_Handbook.md`, append to `Dashboard.md`, list `Needs_Action/`, write a test file, move a file with `.moved` pattern, and attempt a path violation. Verify all operations succeed/fail correctly. (SC-003, SC-008)

**Depends on**: Phase 3 (vault must exist). No Python code to write — vault-interact skill already exists in `.claude/skills/vault-interact/SKILL.md`

### Verification for User Story 3

- [x] T012 [US3] Verify all 6 vault-interact operations against the live vault (SC-003):
  - **Read**: Ask Claude to `read Company_Handbook.md` — verify full content returned
  - **Write**: Ask Claude to `write Inbox/test-write.md` with frontmatter — verify file created
  - **Append**: Ask Claude to `append to Dashboard.md` with "Test entry" — verify text appended (read-back)
  - **List**: Ask Claude to `list Needs_Action/` — verify bullet list of `.md` files (or empty message)
  - **Move**: Ask Claude to `move Inbox/test-write.md to Done` — verify content at `Done/test-write.md`, source renamed to `Inbox/test-write.md.moved`
  - **Create**: Ask Claude to `create Inbox/new-task.md with title "Test Task"` — verify file with valid YAML frontmatter
  - Verify each operation logs to `Logs/vault_operations.jsonl` with correct JSONL format (SC-007)
- [x] T013 [US3] Verify path violation rejection and JSONL logging (SC-008):
  - Ask Claude to `read /etc/passwd` via vault-interact — verify "Error: Path violation" returned
  - Ask Claude to `write /tmp/outside.md` via vault-interact — verify rejected
  - Check `Logs/vault_operations.jsonl` for corresponding failure entries with `status: "failure"`
  - Verify zero path violations succeed

**Checkpoint**: All 6 vault-interact operations work correctly with JSONL audit trail

---

## Phase 6: User Story 4 — End-to-End Skill Processing (Priority: P4)

**Goal**: Validate the complete Bronze tier loop: drop file → watcher creates Needs_Action → check-and-process-needs-action processes → plan created → file routed to Done/Pending_Approval → Dashboard updated

**Independent Test**: Drop a test file, wait for watcher, trigger `check-and-process-needs-action`, verify plan in `Plans/`, result in `Done/` or `Pending_Approval/`, and dashboard summary. (SC-004, SC-005, SC-009)

**Depends on**: Phase 3 (vault), Phase 4 (watcher), Phase 5 (vault-interact verified)

### Implementation for User Story 4

- [x] T014 [US4] Create sample test Needs_Action files for E2E testing by dropping files via watcher:
  - Drop a `.txt` file with routine content (e.g., `organize-notes.txt`) — expect Needs_Action file with `priority: routine`
  - Manually create a Needs_Action file with `priority: sensitive` and suggested action "Send email to team" for HITL testing
  - Manually create a Needs_Action file with `priority: critical` and suggested action "Delete old records" for dry-run testing
  - Verify all test files exist in `Needs_Action/` with correct frontmatter per `contracts/needs-action-format.md`
- [x] T015 [US4] Run single-file E2E processing and verify routing (SC-004, SC-009):
  - With one routine Needs_Action file: trigger `check-and-process-needs-action` in Claude Code
  - Verify: plan created in `Plans/plan-*.md` with correct frontmatter per `contracts/plan-format.md`
  - Verify: result file in `Done/`, original moved (`.moved` suffix in `Needs_Action/`)
  - Verify: `Dashboard.md` shows processing summary with "Auto-executed: 1"
  - Verify: `Logs/actions.jsonl` contains entry with `risk_level: "low"` and `status: "done"`
  - With one sensitive Needs_Action file: trigger processing
  - Verify: routed to `Pending_Approval/` with approval header, NOT executed (SC-009, FR-018)
  - Verify: log shows `status: "pending_approval"` — no external side effects
- [x] T016 [US4] Run 5-file batch processing and verify counts (SC-005):
  - Create 5 Needs_Action files: 3 routine, 1 sensitive, 1 critical
  - Trigger `check-and-process-needs-action`
  - Verify: 3 files routed to `Done/`, 2 to `Pending_Approval/`
  - Verify: 5 plans in `Plans/`
  - Verify: `Dashboard.md` summary shows "Files processed: 5, Auto-executed: 3, Pending approval: 2"
  - Verify: all 5 entries in `Logs/actions.jsonl` with correct risk levels

**Checkpoint**: Complete Bronze tier loop works end-to-end with correct routing and audit trail

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Production readiness, documentation, and stability validation

- [x] T017 [P] Create PM2 ecosystem config in `config/ecosystem.config.js` for `file_drop_watcher.py`: app name `"ai-employee-watcher"`, interpreter `"python3"`, script `"src/file_drop_watcher.py"`, max restarts 5, restart delay 1000ms, log paths to vault `Logs/` per constitution Reproducibility standard
- [x] T018 [P] Write manual test plan in `tests/manual/bronze-tier-test-plan.md` covering SC-001 through SC-009: one section per success criterion, step-by-step instructions, expected outputs, pass/fail criteria
- [x] T019 Run 10-minute stability test (SC-006): start watcher, drop 5+ files at varied intervals, trigger processing for each batch, verify no unhandled exceptions, no orphaned files (every Needs_Action reaches Done/ or Pending_Approval/), watcher remains responsive throughout

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — establishes vault structure
- **US2 (Phase 4)**: Depends on US1 — needs `Needs_Action/` and `Logs/` folders to exist
- **US3 (Phase 5)**: Depends on US1 — needs vault files to read/write against
- **US4 (Phase 6)**: Depends on US1 + US2 + US3 — full pipeline integration
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

```
Phase 1: Setup
    │
Phase 2: Foundational (vault_helpers.py)
    │
Phase 3: US1 — Vault Foundation Setup ← MVP STOP POINT
    │
    ├── Phase 4: US2 — File Drop Watcher (needs vault folders)
    │
    ├── Phase 5: US3 — Vault Read/Write (needs vault files) [can parallel with US2]
    │
    └── Phase 6: US4 — E2E Processing (needs US2 watcher + US3 verified skills)
         │
    Phase 7: Polish & Stability
```

### Within Each User Story

- Templates before scripts (T004/T005 before T006)
- Core logic before safety features (T008 before T009)
- Safety features before CLI/entry point (T009 before T010)
- Implementation before verification (T006 before T007)

### Parallel Opportunities

- **Phase 1**: T001 and T002 are sequential (structure before dependencies)
- **Phase 2**: T003 is a single task (no parallelism)
- **Phase 3**: T004 and T005 can run in parallel (different template files)
- **Phase 4**: T008, T009, T010 are sequential (same file, incremental build)
- **Phase 5**: T012 and T013 can run in parallel (different verification concerns)
- **Phase 6**: T014 must precede T015/T016 (test data before processing)
- **Phase 7**: T017 and T018 can run in parallel (different files)
- **Cross-phase**: US2 (Phase 4) and US3 (Phase 5) can run in parallel after US1

---

## Parallel Example: After US1 Complete

```bash
# These can run in parallel since they work on different files:
Agent A: T008 [US2] Implement core watcher in src/file_drop_watcher.py
Agent B: T012 [US3] Verify vault-interact operations against live vault
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational — `vault_helpers.py` (T003)
3. Complete Phase 3: User Story 1 — Vault Setup (T004–T007)
4. **STOP and VALIDATE**: Run `setup_vault.py`, open vault in Obsidian, verify structure
5. Demo-ready: "The AI Employee vault is set up and organized"

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Vault initialized → **MVP Demo** 🎯
3. Add US2 → Watcher detects file drops → Demo: "Drop a file, see it appear in Needs_Action"
4. Add US3 → Verify skill integration → Demo: "Claude can read/write vault files"
5. Add US4 → Full E2E pipeline → Demo: "Drop file → auto-process → Done/Pending + Dashboard"
6. Polish → Stability verified, docs complete → **Bronze Tier Complete**

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- US3 and US4 have no new Python code — they verify existing Claude Code skills against the vault
- All file writes use `vault_helpers.atomic_write()` per constitution Principle VI
- All logging uses `vault_helpers.log_operation()` producing JSONL per constitution Logging standard
- Commit after each task or logical group per constitution commit discipline: `bronze: <description>`
- Manual test scenarios are the only testing approach for Bronze (no automated test framework)
