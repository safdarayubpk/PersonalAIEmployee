# Implementation Plan: Silver Tier

**Branch**: `002-silver-tier` | **Date**: 2026-02-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-silver-tier/spec.md`

## Summary

Extend the Bronze tier Personal AI Employee with multi-source input (Gmail + WhatsApp watchers), an action execution framework (6 actions across 4 domains via direct function calls), exponential-backoff retry persistence, APScheduler-based recurring tasks, and a central orchestrator that ingests from all sources and routes by risk level. All existing Bronze skills, vault structure, and scripts carry forward unchanged. Silver tier uses the constitution-canonical priority vocabulary (routine|sensitive|critical) throughout.

## Technical Context

**Language/Version**: Python 3.13+ (existing venv)
**Primary Dependencies**:
- Existing: watchdog, google-api-python-client, google-auth-oauthlib, google-auth-httplib2, playwright, apscheduler
- No new dependencies required — all Silver scripts use stdlib + existing deps
**Storage**: Filesystem — Obsidian vault at `VAULT_PATH` (default `/home/safdarayub/Documents/AI_Employee_Vault`), JSONL logs, JSON config files
**Testing**: Manual test plan (markdown checklists) + optional pytest unit tests for retry logic and action executor
**Target Platform**: Linux (Ubuntu), single-user local machine
**Project Type**: Single project — CLI scripts organized as Claude Code skills
**Performance Goals**: Filesystem watcher <5s, Gmail/WhatsApp watchers <60s per poll, orchestrator batch of 10 files <30s total
**Constraints**: No cloud dependencies (C-008), atomic writes (C-002), dry-run default (C-004), 20 retry cap (C-005), 50 batch cap (C-006), 12-20 hour budget (C-009)
**Scale/Scope**: Single user, 10-50 files per orchestrator run, 3 concurrent watchers + 1 scheduler daemon

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Local-First | PASS | All data stays in vault. Only outbound calls: Gmail API (user-authorized OAuth2), WhatsApp Web (browser session). No user data transmitted to cloud storage. |
| II. HITL Safety | PASS | Action executor defaults to dry-run (C-004). Sensitive/critical actions create `Pending_Approval` file, exit code 2. Live mode requires `--live` flag + approval. Retry loops respect HITL gate (FR-004). |
| III. Proactive Autonomy | PASS | 3 watchers + scheduler create `Needs_Action` files autonomously. Ralph Wiggum retry loop persists tasks. Orchestrator processes without prompting. |
| IV. Modularity | PASS | Incremental on Bronze — zero breaking changes (FR-014). All Silver scripts are new files or extensions. Action execution via `importlib` (not MCP/FastAPI). |
| V. Cost-Efficiency | PASS | 24/7 autonomous watchers + scheduler + retry = continuous operation at minimal cost. |
| VI. Error Handling | PASS | Atomic writes (C-002), JSONL logging (FR-012), PID locks (FR-015), stale PID cleanup, SIGTERM/SIGINT handlers, status reset on error (FR-017). |

**Gate result**: ALL PASS. No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/002-silver-tier/
├── plan.md              # This file
├── research.md          # Phase 0 output (decisions already made)
├── data-model.md        # Phase 1 output (entities + state transitions)
├── quickstart.md        # Phase 1 output (setup + run instructions)
├── contracts/           # Phase 1 output (action registry schema + CLI interfaces)
└── tasks.md             # Phase 2 output (/sp.tasks command)
```

### Source Code (repository root)

```text
# Existing Bronze infrastructure (unchanged)
src/
├── setup_vault.py           # Vault initialization (Bronze)
├── file_drop_watcher.py     # Filesystem watcher (Bronze)
├── vault_helpers.py         # Shared vault utilities (Bronze)
└── actions/                 # Action modules (Silver)
    ├── __init__.py           # exists
    ├── email.py              # exists (send_email, draft_email)
    ├── social.py             # NEW stub (post_social)
    ├── calendar_actions.py   # NEW stub (create_event, list_events)
    └── documents.py          # NEW stub (generate_report)

# Skills (Claude Code skill bundles)
.claude/skills/
├── vault-interact/                    # Bronze (unchanged)
├── process-needs-action/              # Bronze (unchanged)
├── check-and-process-needs-action/    # Bronze (unchanged)
├── skill-creator/                     # Bronze (unchanged)
├── gmail-watcher/scripts/gmail_poll.py         # Silver (exists, updated)
├── whatsapp-watcher/scripts/whatsapp_monitor.py # Silver (exists, updated)
├── action-executor/scripts/execute_action.py    # Silver (exists, updated)
├── ralph-retry/scripts/ralph_retry.py           # Silver (exists)
├── daily-scheduler/scripts/scheduler_daemon.py  # Silver (exists, updated)
└── central-orchestrator/scripts/orchestrator.py # Silver (exists, updated)

# Configuration
config/
├── ecosystem.config.js   # PM2 config (Bronze, extend for Silver)
├── risk-keywords.json     # Shared risk keywords (exists)
├── actions.json           # NEW — action registry
└── schedules.json         # Auto-created by scheduler daemon

# Tests
tests/
├── manual/
│   ├── bronze-tier-test-plan.md   # exists
│   └── silver-tier-test-plan.md   # NEW
└── unit/                          # NEW (optional, for retry + action executor)
    ├── test_ralph_retry.py
    └── test_action_executor.py
```

**Structure Decision**: Single project with CLI scripts organized as Claude Code skills. Action modules live under `src/actions/`. No web framework needed — Silver tier uses direct function calls via `importlib`. PM2 ecosystem config extended for Silver watchers + scheduler.

## Architecture

### Component Interaction Flow

```text
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ file_drop_watcher│  │   gmail_poll     │  │whatsapp_monitor  │  │scheduler_daemon  │
│   (Bronze)       │  │   (Silver)       │  │   (Silver)       │  │   (Silver)       │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │                     │
         ▼                     ▼                     ▼                     ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                    Needs_Action/ (vault folder)                         │
    │  Each file: YAML frontmatter (source, priority, status) + body         │
    └────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                    central-orchestrator (orchestrator.py)                │
    │  1. Scan Needs_Action/*.md (skip .moved, skip status:processing)       │
    │  2. Queue by priority (critical → sensitive → routine)                 │
    │  3. For each file in batch (cap 10):                                   │
    │     a. Mark status:processing                                          │
    │     b. Assess risk (keyword scan)                                      │
    │     c. Create plan in Plans/                                           │
    │     d. Route: routine→Done/, sensitive/critical→Pending_Approval/      │
    │     e. Attempt action (dry-run) if source has action mapping           │
    │  4. Update Dashboard.md with summary                                   │
    └──────────┬──────────────────────────────┬──────────────────────────────┘
               │                              │
               ▼                              ▼
    ┌─────────────────┐            ┌─────────────────────┐
    │   Done/ folder   │            │ Pending_Approval/    │
    │  (routine items) │            │ (sensitive/critical) │
    └─────────────────┘            └──────────┬──────────┘
                                              │ user moves to Approved/
                                              ▼
                                   ┌─────────────────────┐
                                   │   Approved/ folder   │
                                   │  + action-executor   │
                                   │  --live --approval-ref│
                                   └──────────┬──────────┘
                                              │
                                              ▼
                                   ┌─────────────────────┐
                                   │  src/actions/*.py    │
                                   │  (importlib call)    │
                                   └─────────────────────┘
```

### Action Execution Architecture

```text
action-executor (execute_action.py)
  │
  ├── --action email.send_email --params '{"to":"...", "subject":"..."}'
  │   ├── Loads config/actions.json → finds module="actions.email", func="send_email", hitl=true
  │   ├── DRY-RUN (default): logs params, returns dry-run result, exit 0
  │   ├── LIVE without approval: creates Pending_Approval file, exit 2
  │   └── LIVE with --approval-ref: importlib.import_module("actions.email").send_email(**params), exit 0/1
  │
  ├── --action email.draft_email (hitl=false)
  │   └── LIVE: executes immediately (approval-exempt), exit 0/1
  │
  ├── --action social.post_social (hitl=true) → stub, returns NotImplementedError in live
  ├── --action calendar.create_event (hitl=true) → stub
  ├── --action calendar.list_events (hitl=false) → stub, returns empty list
  └── --action documents.generate_report (hitl=false) → stub, writes markdown to Plans/
```

### Retry Integration

```text
ralph_retry.py wraps any callable:
  ralph_retry.py --command "python execute_action.py --action email.send_email --live ..."
  │
  ├── Attempt 1: run command
  │   ├── exit 0 → success, stop
  │   ├── exit 2 → HITL blocked, stop (non-retryable)
  │   └── exit 1 → failure, schedule retry
  │
  ├── Attempt 2: wait 2s (base^1), re-run
  ├── Attempt 3: wait 4s (base^2), re-run
  ├── ...
  └── Attempt N: wait min(base^(N-1), 300s), re-run or exhaust
```

## Technology Decisions

All technology decisions for Silver tier are pre-resolved — no NEEDS CLARIFICATION items. Key decisions:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Action execution | Direct `importlib` function calls | Simpler than MCP/FastAPI; no HTTP overhead; already implemented in action-executor |
| Priority vocabulary | `routine\|sensitive\|critical` | Constitution-canonical; consistent across all tiers |
| Gmail sending | Gmail API (OAuth2) | Reuses existing OAuth2 credentials from gmail-watcher; no new SMTP deps |
| Risk keywords | Shared `config/risk-keywords.json` | Single source of truth; already centralized from prior fixes |
| Scheduling | APScheduler (in-memory) | Already implemented; no external cron dependency |
| Process management | PM2 with PID lock files | Bronze established PM2; PID locks prevent duplicate instances |
| Action stubs | Return structured dict + log | Enough to pass SC-002 lifecycle tests; real implementations in Gold |

## Phases

### Phase 1: Setup & Configuration (estimated: 1-2 hours)

- Create `config/actions.json` action registry with 6 actions
- Extend `config/ecosystem.config.js` for Silver processes (3 watchers + scheduler)
- Verify `.env` has all required vars (`VAULT_PATH`, `PROJECT_ROOT`, `RALPH_MAX_ITERATIONS`)

### Phase 2: Action Module Stubs (estimated: 1-2 hours)

- Create `src/actions/social.py` with `post_social()` stub
- Create `src/actions/calendar_actions.py` with `create_event()` and `list_events()` stubs
- Create `src/actions/documents.py` with `generate_report()` stub
- Each stub: accepts `**kwargs`, returns structured dict, logs to `Logs/actions.jsonl`

### Phase 3: Log Redaction (estimated: 1 hour)

- Implement FR-016: redact sensitive fields in all `log_entry()` functions
- Add redaction utility to `src/vault_helpers.py` or as shared function
- Verify no credential values appear in any JSONL log

### Phase 4: Integration & Wiring (estimated: 2-3 hours)

- Wire action-executor to read `config/actions.json` for action discovery
- Ensure orchestrator's `attempt_action()` correctly calls action-executor for all source types
- Add `--approval-ref` flow to action-executor for live mode with approval verification
- Test the full pipeline: watcher → Needs_Action → orchestrator → Done/Pending → action-executor

### Phase 5: Dashboard Enhancement (estimated: 1 hour)

- Update orchestrator's `update_dashboard()` to include per-source breakdown table
- Add stale `Pending_Approval` file detection (>48 hours per constitution VI)
- Ensure Dashboard.md shows cumulative run history

### Phase 6: Test Plan & Validation (estimated: 2-3 hours)

- Create `tests/manual/silver-tier-test-plan.md` covering SC-001 through SC-010
- Optional: create `tests/unit/test_ralph_retry.py` and `tests/unit/test_action_executor.py`
- Run 30-minute stability test (SC-006)
- Run Bronze regression (SC-009)

### Phase 7: Polish & Documentation (estimated: 1-2 hours)

- Update SKILL.md files with Silver-specific documentation
- Verify PM2 ecosystem config starts all components
- Final cross-watcher keyword consistency test (SC-001)
- Clean up any orphaned `.tmp` files or stale PID files

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gmail OAuth2 token expiry during long run | Watcher stops processing | Already patched: try/except on refresh, clean exit on failure |
| WhatsApp QR session invalidation | Watcher hangs | Already patched: 60s timeout detection, clean exit, PID cleanup |
| Action stubs insufficient for SC-002 | Test failure | Stubs return structured dicts with all expected fields; dry-run and HITL lifecycle tested separately |
| Priority vocabulary inconsistency | Misrouting | Resolved: all scripts use routine/sensitive/critical; orchestrator queues by canonical values |
| Concurrent watcher + orchestrator writes | File corruption | Mitigated: atomic writes (C-002), sequential processing in orchestrator, status:processing lock |

## Complexity Tracking

No constitution violations. No complexity justifications needed.
