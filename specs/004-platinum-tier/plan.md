# Implementation Plan: Platinum Tier — Cloud-Local Hybrid Operation

**Branch**: `004-platinum-tier` | **Date**: 2026-03-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/004-platinum-tier/spec.md`

## Summary

Upgrade the Personal AI Employee from Gold to Platinum tier by introducing a two-agent architecture: a cloud agent on Oracle Cloud VM (141.145.146.17) handles 24/7 triage and drafting, while the local agent retains exclusive authority over sensitive/critical execution. Agents communicate exclusively through git-synced Obsidian vault folders using file-based IPC with claim-by-move concurrency control. All existing Gold-tier components (watchers, MCP servers, orchestrator, scheduler) are extended with `FTE_ROLE` gating — no new components are created.

## Technical Context

**Language/Version**: Python 3.13+ (local), Python 3.12.3 (cloud VM)
**Primary Dependencies**: watchdog, PyYAML, google-api-python-client, apscheduler, FastMCP, odoorpc, PM2 (process manager), Git
**Storage**: Obsidian vault (filesystem — markdown + YAML frontmatter + JSONL logs), private GitHub repo for sync
**Testing**: Manual end-to-end test scenarios, pytest for unit tests on new modules
**Target Platform**: Linux (Ubuntu 20.04 local laptop, Ubuntu 24.04 cloud VM)
**Project Type**: Single project (shared repo, role-gated at runtime via `FTE_ROLE`)
**Performance Goals**: Git sync ≤60s interval, draft visibility ≤3 min from event, 90%+ uptime on E2.1.Micro
**Constraints**: 1 OCPU / 1GB RAM on cloud VM, no direct network IPC between agents, secrets never in git
**Scale/Scope**: 2 machines, 1 user, 10-50 tasks/day

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Evidence |
|------|--------|----------|
| I. Local-First & Privacy-Centric | PASS | Cloud operates on sanitized markdown only; secrets remain local-only via `.gitignore` + pre-commit hook (FR-014, FR-015, FR-016) |
| II. HITL Safety | PASS | Cloud agent NEVER executes Sensitive/Critical actions (FR-006); only drafts to `Pending_Approval/` |
| III. Proactive Autonomy | PASS | Cloud agent runs 24/7 watchers and scheduler; Ralph Wiggum caps preserved (FR-029) |
| IV. Modularity | PASS | Platinum builds on Gold; `FTE_ROLE=local` gives identical Gold behavior (FR-030) |
| V. Cost-Efficiency | PASS | Free-tier VM; same Claude API costs |
| VI. Error Handling | PASS | PM2 restart limits (5/60s), circuit breakers, atomic writes — all preserved (FR-024, FR-029) |
| VII. Hybrid Cloud-Local | PASS | This plan implements all VII subsections: role gating (7.1), file-based IPC (7.2), rejection flow (7.2.1), claim-by-move (7.3), single-writer (7.4), correlation IDs (7.5), git sync (7.6), offline tolerance (7.7), safety preservation (7.8) |
| `.gitignore` secrets mandate | PASS | FR-014 + FR-015 enforce; pre-commit hook validates independently |
| No code in vault | PASS | Only markdown, JSONL, and JSON config synced |

**Post-design re-check**: All gates remain PASS. No violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/004-platinum-tier/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/sp.tasks command)
```

### Source Code (repository root)

```text
src/
├── actions/
│   ├── __init__.py              # Existing (no changes)
│   ├── email.py                 # MODIFY: add FTE_ROLE gate on send_email()
│   ├── social.py                # MODIFY: add FTE_ROLE gate on post_social()
│   ├── calendar_actions.py      # MODIFY: add FTE_ROLE gate on write actions
│   └── documents.py             # Existing (no changes — reports are Routine)
├── mcp/
│   ├── base_server.py           # MODIFY: add get_fte_role(), enforce_role_gate()
│   ├── email_server.py          # MODIFY: gate email_send when FTE_ROLE=cloud
│   ├── social_server.py         # MODIFY: gate post actions when FTE_ROLE=cloud
│   ├── odoo_server.py           # MODIFY: gate create/payment when FTE_ROLE=cloud
│   └── documents_server.py      # Existing (no changes)
├── git_sync.py                  # NEW: git sync service (pull/commit/push loop)
├── role_gate.py                 # NEW: FTE_ROLE detection, validation, enforcement
├── claim_move.py                # NEW: claim-by-move atomic file operations
├── dashboard_merger.py          # NEW: merge Updates/*.md into Dashboard.md
├── approval_watcher.py          # NEW: watch Approved/ and execute actions (local only)
├── rejection_handler.py         # NEW: handle Rejected/ files (cloud re-draft or escalate)
├── stale_detector.py            # NEW: flag stale Pending_Approval/Rejected files
├── vault_helpers.py             # MODIFY: add agent field to log_operation()
├── correlation.py               # MODIFY: update format to match constitution (8 hex chars)
├── circuit_breaker.py           # Existing (no changes)
├── setup_vault.py               # MODIFY: add Platinum folder creation
└── file_drop_watcher.py         # Existing (no changes — not used on cloud)

.claude/skills/
├── gmail-watcher/scripts/
│   └── gmail_poll.py            # MODIFY: add FTE_ROLE-aware behavior
├── daily-scheduler/scripts/
│   └── scheduler_daemon.py      # MODIFY: add FTE_ROLE to Needs_Action frontmatter
└── whatsapp-watcher/scripts/
    └── whatsapp_monitor.py      # Existing (not run on cloud — requires .session files)

config/
├── ecosystem.config.js          # MODIFY: add FTE_ROLE to all app envs
├── ecosystem.cloud.config.js    # NEW: cloud-specific PM2 config
├── actions.json                 # MODIFY: add fte_role_minimum field per action
├── risk-keywords.json           # Existing (no changes)
├── schedules.json               # Existing (no changes — same schedule both roles)
└── .env.example                 # NEW: document all Platinum env vars

hooks/
└── pre-commit                   # NEW: secrets exclusion validation hook

tests/
├── unit/
│   ├── test_role_gate.py        # NEW: FTE_ROLE validation tests
│   ├── test_claim_move.py       # NEW: claim-by-move tests
│   ├── test_git_sync.py         # NEW: git sync tests
│   ├── test_dashboard_merger.py # NEW: dashboard merge tests
│   └── test_stale_detector.py   # NEW: stale file detection tests
└── integration/
    └── test_e2e_platinum.py     # NEW: end-to-end offline email demo test
```

### Vault Folder Structure (both cloud and local)

```text
AI_Employee_Vault/
├── Inbox/                       # Existing (Bronze)
├── Needs_Action/
│   ├── gmail/                   # NEW: domain-specific subfolder
│   ├── whatsapp/                # NEW: domain-specific subfolder
│   ├── scheduler/               # NEW: domain-specific subfolder
│   └── manual/                  # NEW: human-created and escalated tasks
├── In_Progress/
│   ├── cloud/                   # NEW: cloud agent's active work
│   └── local/                   # NEW: local agent's active work
├── Pending_Approval/
│   ├── gmail/                   # NEW: domain-specific subfolder
│   ├── social/                  # NEW: domain-specific subfolder
│   ├── odoo/                    # NEW: domain-specific subfolder
│   └── general/                 # NEW: other actions
├── Updates/                     # NEW: cloud agent incremental updates
├── Approved/                    # Existing (Gold)
├── Rejected/                    # NEW: rejected drafts with reason
├── Done/                        # Existing (Bronze)
├── Plans/                       # Existing (Silver)
├── Briefings/                   # Existing (Gold)
├── Logs/                        # Existing (Bronze)
│   ├── actions.jsonl            # Existing
│   ├── gmail.jsonl              # Existing
│   ├── scheduler.jsonl          # Existing
│   ├── sync.jsonl               # NEW: git sync operations
│   ├── sync-conflicts.jsonl     # NEW: git merge conflicts
│   ├── health.json              # Existing (circuit breaker state)
│   └── critical_actions.jsonl   # Existing (local-only writes)
├── Dashboard.md                 # Existing (local single-writer)
└── Company_Handbook.md          # Existing (local-only modifications)
```

**Structure Decision**: Single project with role-gated runtime behavior. No separate cloud/local codebases — both run the same code with `FTE_ROLE` env var controlling permissions. This matches Gold-tier's established single-repo pattern and minimizes code duplication.

## Architecture: Component Interaction

### Cloud Agent Flow (FTE_ROLE=cloud)

```
[Gmail API] → gmail_poll.py (read-only) → Needs_Action/gmail/*.md
                                              ↓
                          git-sync → push to GitHub
                                              ↓
                    cloud orchestrator claims → In_Progress/cloud/*.md
                                              ↓
                              draft reply → Pending_Approval/gmail/*.md
                                              ↓
                          git-sync → push to GitHub
                                              ↓
                        (write update) → Updates/dashboard-update-*.md
```

### Local Agent Flow (FTE_ROLE=local)

```
git-sync → pull from GitHub → detect Pending_Approval/*.md
                                              ↓
                    user reviews in Obsidian → moves to Approved/*.md
                                              ↓
                    approval_watcher detects → executes via MCP server
                                              ↓
                              move to Done/ → log with correlation_id
                                              ↓
                    dashboard_merger reads Updates/ → merge into Dashboard.md
                                              ↓
                          git-sync → push to GitHub
```

### Claim-by-Move Protocol

```
Agent detects file in Needs_Action/<domain>/
  ↓
  Try: os.rename(Needs_Action/<domain>/file.md → In_Progress/<role>/file.md)
  ↓
  Success? → Process file (add agent + correlation_id to frontmatter)
  Failure (FileNotFoundError)? → Log "file already claimed", skip
  ↓
  After processing: move to Pending_Approval/<domain>/ or Done/
```

## New Components Design

### 1. `src/role_gate.py` — FTE_ROLE Detection & Enforcement

**Purpose**: Centralized role validation. Single import point for all components.

**Functions**:
- `get_fte_role() -> str` — Read `FTE_ROLE` from `.env`/os.environ. Returns `"cloud"` or `"local"`. Raises `SystemExit` if missing or invalid (FR-005).
- `is_cloud() -> bool` — Shorthand for `get_fte_role() == "cloud"`
- `is_local() -> bool` — Shorthand for `get_fte_role() == "local"`
- `enforce_role_gate(action_name: str, risk_level: str) -> None` — Checks if the current role permits the action at the given risk level. When `FTE_ROLE=cloud` and risk is `sensitive` or `critical`, raises `RoleViolationError`. Logs the refusal (FR-006, FR-008).
- `validate_startup() -> str` — Called at process start. Validates `FTE_ROLE` is set and valid. Returns the role string or exits with fatal error.

**Design Decision**: Role check at action executor level, not just orchestrator (FR-008). Every component that can trigger external effects must call `enforce_role_gate()` before execution.

### 2. `src/git_sync.py` — Git Sync Service

**Purpose**: Bidirectional vault synchronization via git (FR-001 to FR-004).

**Functions**:
- `sync_cycle(vault_path: Path) -> SyncResult` — One complete pull→commit→push cycle:
  1. `git pull --rebase` (FR-001)
  2. Stage changes: `git add .` (respects `.gitignore` — FR-004)
  3. Commit with auto-generated message: `"sync: <role> <timestamp> [<N files>]"`
  4. `git push`
  5. On push failure: retry `pull --rebase` + `push` up to 3 times (FR-002)
  6. On persistent failure: log to `Logs/sync-conflicts.jsonl`, create `Needs_Action/manual/` file
- `queue_offline_commits(vault_path: Path) -> None` — When offline, commits locally and queues for next push (FR-003)
- `run_sync_loop(vault_path: Path, interval: int) -> None` — Daemon loop with `GIT_SYNC_INTERVAL_SECONDS` (default 60) sleep between cycles

**Environment Variables**:
- `GIT_SYNC_INTERVAL_SECONDS` (default: `60`)
- `VAULT_PATH` (required)
- `FTE_ROLE` (required)

**Logging**: All operations logged to `Logs/sync.jsonl` with `component: "git-sync"`, `agent: <role>`, `correlation_id: null` (sync is infrastructure, not task-specific).

### 3. `src/claim_move.py` — Claim-by-Move Concurrency Control

**Purpose**: Prevent duplicate processing when both agents are active (FR-009 to FR-011).

**Functions**:
- `claim_file(source_path: Path, role: str) -> Path | None` — Atomically move file from `Needs_Action/<domain>/` to `In_Progress/<role>/`. Returns new path on success, `None` if file already claimed. Uses `os.rename()` for atomicity (FR-009). Logs "file already claimed" on `FileNotFoundError` (FR-010).
- `complete_file(in_progress_path: Path, destination_folder: str, **frontmatter_updates) -> Path` — Move from `In_Progress/<role>/` to destination (`Pending_Approval/<domain>/`, `Done/`, `Rejected/`). Updates frontmatter status (FR-011).
- `scan_needs_action(vault_path: Path, domain: str | None) -> list[Path]` — List files in `Needs_Action/<domain>/` (or all domains). Returns sorted by creation timestamp from frontmatter.

### 4. `src/dashboard_merger.py` — Single-Writer Dashboard Merge

**Purpose**: Merge cloud agent's incremental updates into `Dashboard.md` (FR-012, FR-013).

**Functions**:
- `merge_updates(vault_path: Path) -> int` — Read all `Updates/dashboard-update-*.md` files chronologically, append their content to `Dashboard.md` under a `## Cloud Updates` section, then delete processed files. Returns count of merged updates. Only runs when `FTE_ROLE=local` (FR-013).
- `write_update(vault_path: Path, content: str, source: str) -> Path` — Create an update file in `Updates/` with ISO timestamp filename. Only runs when `FTE_ROLE=cloud` (FR-012). Returns the created file path.

### 5. `src/approval_watcher.py` — Approved/ Action Executor

**Purpose**: Watch `Approved/` folder and execute approved actions (FR-026 to FR-028). Local-only.

**Functions**:
- `process_approved(vault_path: Path) -> int` — Scan `Approved/` for files, parse frontmatter to determine action type, execute via appropriate MCP server call, move to `Done/` on success (FR-027), move to `Needs_Action/manual/` on failure (FR-028). Returns count of processed files.
- `execute_action(file_path: Path) -> dict` — Read frontmatter `source` and `suggested_action` fields, dispatch to correct action handler (`email.send_email`, `social.post_social`, etc.), return result dict.

**Guard**: Refuses to run when `FTE_ROLE=cloud` (logs fatal error, exits).

### 6. `src/rejection_handler.py` — Rejected/ File Processing

**Purpose**: Handle rejected drafts per constitution Section 7.2.1 (FR-031 to FR-033).

**Functions**:
- `reject_file(file_path: Path, reason: str, vault_path: Path) -> Path` — Move from `Pending_Approval/<domain>/` to `Rejected/`, add `status: rejected` and `rejection_reason` to frontmatter, log with correlation ID (FR-031). Local-only.
- `process_rejections(vault_path: Path) -> int` — Cloud-only. Scan `Rejected/` for files, check if rejection reason is actionable, either re-draft (move back through pipeline) or escalate to `Needs_Action/manual/` (FR-032).

### 7. `src/stale_detector.py` — Stale File Detection

**Purpose**: Flag old files in Dashboard.md (FR-035).

**Functions**:
- `detect_stale_files(vault_path: Path) -> list[dict]` — Scan `Pending_Approval/` for files >48 hours old and `Rejected/` for files >7 days old. Returns list of stale file metadata.
- `update_dashboard_stale(vault_path: Path) -> int` — Add/update a `## Stale Items` section in Dashboard.md with stale file list. Local-only.

## Modifications to Existing Components

### 1. `src/vault_helpers.py` — Add Agent Field

**Changes**:
- Import `role_gate.get_fte_role`
- `log_operation()`: Add `agent` field to every log entry (value from `FTE_ROLE`)
- `log_error()`: Add `agent` field

### 2. `src/correlation.py` — Update Format

**Changes**:
- Update format from `corr-YYYYMMDD-HHMMSS-XXXX` (4 hex) to `corr-YYYY-MM-DD-XXXXXXXX` (8 hex) to match constitution spec `corr-<ISO-date>-<8-char-hex>`
- Update `CORRELATION_ID_PATTERN` regex accordingly
- `is_valid_correlation_id()` accepts both old and new formats for backward compatibility
- `generate_correlation_id()` generates new format only

### 3. `src/setup_vault.py` — Platinum Folder Creation

**Changes**:
- Add Platinum folders to `VAULT_FOLDERS`: `Needs_Action/gmail/`, `Needs_Action/whatsapp/`, `Needs_Action/scheduler/`, `Needs_Action/manual/`, `In_Progress/cloud/`, `In_Progress/local/`, `Pending_Approval/gmail/`, `Pending_Approval/social/`, `Pending_Approval/odoo/`, `Pending_Approval/general/`, `Updates/`, `Rejected/`
- Conditional creation: only create Platinum folders if `FTE_ROLE` is set (backward compat — FR-030)
- Existing folders (`Inbox/`, `Done/`, etc.) remain unchanged

### 4. `src/mcp/base_server.py` — Role Enforcement

**Changes**:
- Add `from role_gate import get_fte_role, enforce_role_gate`
- New function `role_gated_action(tool: str, risk_level: str, params: dict, execute_fn, correlation_id: str) -> dict`:
  - If `FTE_ROLE=cloud` and risk is sensitive/critical: create draft in `Pending_Approval/`, return `{status: "draft_created", ...}`
  - If `FTE_ROLE=local`: proceed through existing HITL flow
- `create_pending_approval()`: Add `agent` and `correlation_id` to frontmatter
- `log_tool_call()`: Add `agent` field

### 5. `src/mcp/email_server.py` — Cloud Draft Mode

**Changes**:
- `email_send()`: Before existing HITL logic, call `enforce_role_gate("email_send", "sensitive")`. When `FTE_ROLE=cloud`, return draft result instead of attempting send.
- All other tools (`email_draft`, `email_search`) unchanged — they're Routine level.

### 6. `src/mcp/odoo_server.py` — Cloud Draft Mode

**Changes**:
- `odoo_create_invoice()`: Call `enforce_role_gate("odoo_create_invoice", "critical")`. Cloud → draft only.
- `odoo_register_payment()`: Call `enforce_role_gate("odoo_register_payment", "critical")`. Cloud → draft only.
- Read-only tools (`odoo_list_invoices`, `odoo_financial_summary`, `odoo_list_partners`) unchanged.

### 7. `.claude/skills/gmail-watcher/scripts/gmail_poll.py` — Role-Aware Behavior

**Changes**:
- Import `role_gate.get_fte_role`
- On startup: call `validate_startup()` to confirm `FTE_ROLE` is set
- `create_needs_action()`:
  - Write to `Needs_Action/gmail/` instead of `Needs_Action/` (domain subfolder — FR-021)
  - Add `agent: <role>` to frontmatter
  - Set `tier: platinum` in frontmatter
- Cloud mode: Use `SCOPES_READONLY` only (never `SCOPES_MODIFY`)
- Cloud mode: Never call `mark_as_read()` even with `--live` flag
- Authentication: When `FTE_ROLE=cloud` and token refresh fails → enter circuit breaker, create `Needs_Action/manual/` for human re-auth

### 8. `.claude/skills/daily-scheduler/scripts/scheduler_daemon.py` — Role Field

**Changes**:
- Import `role_gate.get_fte_role`
- `create_needs_action()`: Add `agent: <role>` to frontmatter, set `tier: platinum`
- Write to `Needs_Action/scheduler/` instead of `Needs_Action/`

### 9. `config/ecosystem.config.js` — Add FTE_ROLE

**Changes**:
- Add `FTE_ROLE: "local"` to every app's `env` block
- Update vault paths to use env var pattern

### 10. `config/ecosystem.cloud.config.js` — NEW Cloud PM2 Config

**Contents**:
- 3 apps: `cloud-git-sync`, `cloud-gmail-watcher`, `cloud-scheduler` (orchestrator excluded — E2.1.Micro memory constraint per ADR-0014; cloud processing handled by watchers and scheduler directly)
- All with `FTE_ROLE: "cloud"` in env
- Paths: `/home/ubuntu/AI_Employee_Vault` for vault, `~/fte-env/bin/python3` for interpreter
- Max restarts: 5 per 60s window (FR-024)
- Auto-start on boot via `pm2 startup` (FR-025)
- **WhatsApp watcher excluded** (requires `.session` files — Non-Goal)

## Environment Variables

| Variable | Local Value | Cloud Value | Required | Default |
|----------|-------------|-------------|----------|---------|
| `FTE_ROLE` | `local` | `cloud` | Yes (Platinum) | None — fatal if missing |
| `VAULT_PATH` | `/home/safdarayub/Documents/AI_Employee_Vault` | `/home/ubuntu/AI_Employee_Vault` | Yes | Hardcoded defaults |
| `PROJECT_ROOT` | `/home/safdarayub/Desktop/claude/fte` | `/home/ubuntu/AI_Employee_Vault` (repo root) | Yes | Auto-detected |
| `GIT_SYNC_INTERVAL_SECONDS` | `60` | `60` | No | `60` |
| `DRY_RUN` | `true` (dev) / `false` (live) | `true` (always) | No | `true` |
| `FTE_CLOUD_HOST` | `141.145.146.17` | N/A | No | None |
| `RALPH_MAX_ITERATIONS` | `15` | `15` | No | `15` |
| `ODOO_HOST` | `localhost` | `localhost` | No | `localhost` |
| `ODOO_PORT` | `8069` | `8069` | No | `8069` |

## Secrets Management

### Files That MUST Stay Local-Only

| File | Why | Enforcement |
|------|-----|-------------|
| `.env` | All API keys, tokens, passwords | `.gitignore` + pre-commit hook |
| `credentials.json` | Google OAuth client secrets | `.gitignore` + pre-commit hook |
| `token.json` | Gmail OAuth refresh token | `.gitignore` + pre-commit hook |
| `*.session` | WhatsApp Playwright session | `.gitignore` + pre-commit hook |
| `*.key`, `*.pem` | SSH/TLS private keys | `.gitignore` + pre-commit hook |
| `credentials/` | Credential store directory | `.gitignore` + pre-commit hook |

### Pre-Commit Hook (`hooks/pre-commit`)

```bash
#!/bin/bash
# Platinum tier: block secrets from git
BLOCKED_PATTERNS=(".env" "*.session" "*.token" "*.key" "*.pem" "credentials/" "secrets/")
# Check staged files against each pattern
# Exit 1 with clear error message on violation (FR-015)
```

The hook validates independently of `.gitignore` — even if `.gitignore` is modified, the hook blocks secrets (Edge Case 6 in spec).

### Cloud VM `.env` (Minimal)

```bash
FTE_ROLE=cloud
VAULT_PATH=/home/ubuntu/AI_Employee_Vault
PROJECT_ROOT=/home/ubuntu/AI_Employee_Vault
GIT_SYNC_INTERVAL_SECONDS=60
DRY_RUN=true
# Gmail read-only token will be copied manually during setup
# No banking, WhatsApp, or payment credentials
```

## Git Sync Protocol Detail

### Sync Cycle Pseudocode

```
1. git stash (protect uncommitted work)
2. git pull --rebase origin main
   - On conflict: abort rebase, log to sync-conflicts.jsonl,
     create Needs_Action/manual/ file, skip this cycle
3. git stash pop (if stashed)
4. git add . (respects .gitignore)
5. Check: any staged changes?
   - No: skip commit/push, log "no changes"
   - Yes: git commit -m "sync: <role> <ISO-timestamp> [<N> files]"
6. git push origin main
   - On failure: retry pull --rebase + push (max 3 attempts)
   - On persistent failure: log, create Needs_Action/manual/
```

### Sync Frequency

- Default: every 60 seconds (`GIT_SYNC_INTERVAL_SECONDS=60`)
- This gives SC-002 compliance: email arrives → cloud processes within ~60s → commits → next sync pushes within ~60s → total ≤3 min

### Offline Behavior

- If `git pull` fails (network down): continue local processing, queue commits (FR-003)
- If `git push` fails: commits accumulate locally, pushed on reconnection (FR-003)
- Neither agent assumes the other is online (constitution 7.7)

## PM2 Configuration (Cloud VM)

### `config/ecosystem.cloud.config.js`

```javascript
module.exports = {
  apps: [
    {
      name: "cloud-git-sync",
      interpreter: "/home/ubuntu/fte-env/bin/python3",
      script: "src/git_sync.py",
      cwd: "/home/ubuntu/AI_Employee_Vault",
      max_restarts: 5,
      min_uptime: 60000,
      restart_delay: 5000,
      autorestart: true,
      env: {
        FTE_ROLE: "cloud",
        VAULT_PATH: "/home/ubuntu/AI_Employee_Vault",
        GIT_SYNC_INTERVAL_SECONDS: "60",
      },
    },
    {
      name: "cloud-gmail-watcher",
      interpreter: "/home/ubuntu/fte-env/bin/python3",
      script: ".claude/skills/gmail-watcher/scripts/gmail_poll.py",
      args: "--minutes 30 --interval 120",
      cwd: "/home/ubuntu/AI_Employee_Vault",
      max_restarts: 5,
      min_uptime: 60000,
      restart_delay: 5000,
      autorestart: true,
      env: {
        FTE_ROLE: "cloud",
        VAULT_PATH: "/home/ubuntu/AI_Employee_Vault",
        PROJECT_ROOT: "/home/ubuntu/AI_Employee_Vault",
        DRY_RUN: "true",
      },
    },
    {
      name: "cloud-scheduler",
      interpreter: "/home/ubuntu/fte-env/bin/python3",
      script: ".claude/skills/daily-scheduler/scripts/scheduler_daemon.py",
      cwd: "/home/ubuntu/AI_Employee_Vault",
      max_restarts: 5,
      min_uptime: 60000,
      restart_delay: 5000,
      autorestart: true,
      env: {
        FTE_ROLE: "cloud",
        VAULT_PATH: "/home/ubuntu/AI_Employee_Vault",
        PROJECT_ROOT: "/home/ubuntu/AI_Employee_Vault",
      },
    },
  ],
};
```

### Auto-Start on Boot

```bash
pm2 startup systemd -u ubuntu --hp /home/ubuntu
pm2 start config/ecosystem.cloud.config.js
pm2 save
```

## Cloud VM First-Boot Setup

### Prerequisites (already done)

- Ubuntu 24.04, user `ubuntu`, IP `141.145.146.17`
- Python 3.12.3 venv at `~/fte-env`
- Git configured, SSH key for GitHub
- Repo cloned at `~/AI_Employee_Vault`

### Remaining Setup Steps

1. **Install PM2**: `npm install -g pm2`
2. **Install Python deps in venv**: `pip install google-api-python-client google-auth-oauthlib apscheduler watchdog pyyaml`
3. **Create `.env`** with `FTE_ROLE=cloud` and minimal config
4. **Copy Gmail read-only token**: Manually copy `token.json` (one-time, read-only scoped) from local to cloud. This is the one exception — it's a read-only token, not a full credential.
5. **Create Platinum vault folders**: Run `python src/setup_vault.py`
6. **Install pre-commit hook**: Copy `hooks/pre-commit` to `.git/hooks/pre-commit`, `chmod +x`
7. **Configure PM2**: `pm2 start config/ecosystem.cloud.config.js && pm2 startup && pm2 save`
8. **Verify**: `pm2 list` shows all services running

## Testing Strategy

### Unit Tests

| Test File | What It Tests | Key Scenarios |
|-----------|---------------|---------------|
| `test_role_gate.py` | FTE_ROLE validation | Missing role → fatal, invalid value → fatal, cloud blocks sensitive, local allows all |
| `test_claim_move.py` | Claim-by-move atomicity | Successful claim, already-claimed skip, concurrent claim race |
| `test_git_sync.py` | Sync cycle | Normal cycle, push failure + retry, offline queueing |
| `test_dashboard_merger.py` | Update merging | Single update, multiple chronological, empty Updates/ |
| `test_stale_detector.py` | Stale detection | Fresh files ignored, 49h pending flagged, 8d rejected flagged |

### Integration Tests

#### End-to-End Offline Email Demo (SC-003, SC-010)

**Scenario**: Full lifecycle per User Story 1.

1. **Setup**: Local agent stopped. Cloud agent running.
2. **Trigger**: Send test email to monitored Gmail account.
3. **Cloud processes**: Gmail watcher detects → creates `Needs_Action/gmail/*.md` → orchestrator claims → drafts reply → writes `Pending_Approval/gmail/*.md` → git sync pushes.
4. **Verify cloud**: File exists in GitHub repo `Pending_Approval/gmail/`.
5. **Local reconnects**: Start local agent. Git sync pulls.
6. **Verify local**: File appears in local vault `Pending_Approval/gmail/`.
7. **User approves**: Move file to `Approved/` in Obsidian.
8. **Local executes**: Approval watcher detects → sends email via fte-email MCP → moves to `Done/`.
9. **Verify completion**: File in `Done/` with `status: done`, correlation ID in `Logs/actions.jsonl` on both machines.

**Pass criteria**: All 9 steps complete, correlation ID trail unbroken, ≤15 minutes total (SC-010), ≤3 manual steps (SC-003).

### Gold-Tier Regression Test (SC-006)

Run all existing Gold-tier test scenarios with `FTE_ROLE=local`. All must pass without modification.

### Security Test (SC-004)

```bash
# Scan all git history for secrets
git log --all --diff-filter=A --name-only | grep -E '\.(env|session|token|key|pem)$'
# Must return zero results
```

### Duplicate Prevention Test (SC-005)

Run both agents for 1 hour with 10+ incoming tasks. Verify zero files claimed by both agents (no duplicates in `In_Progress/cloud/` and `In_Progress/local/` for the same original file).

## Implementation Order (Dependency Graph)

```
Phase A: Foundation (no external effects, safe to implement first)
  1. role_gate.py + test_role_gate.py
  2. correlation.py update (8 hex chars)
  3. setup_vault.py Platinum folders
  4. vault_helpers.py agent field in logs
  5. Pre-commit hook

Phase B: Sync Infrastructure
  6. git_sync.py + test_git_sync.py
  7. claim_move.py + test_claim_move.py

Phase C: Role Gating (depends on A.1)
  8. base_server.py role enforcement
  9. email_server.py cloud draft mode
  10. odoo_server.py cloud draft mode
  11. gmail_poll.py role-aware + domain subfolders
  12. scheduler_daemon.py role field

Phase D: Platinum Workflows (depends on B + C)
  13. dashboard_merger.py + test_dashboard_merger.py
  14. approval_watcher.py
  15. rejection_handler.py
  16. stale_detector.py + test_stale_detector.py

Phase E: Cloud Deployment (depends on all above)
  17. ecosystem.cloud.config.js
  18. Cloud VM setup + PM2 startup
  19. Gmail token transfer

Phase F: Testing & Demo
  20. test_e2e_platinum.py
  21. Gold regression test
  22. Security scan
  23. Live demo rehearsal
```

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Gmail OAuth token expires on cloud VM (headless, no browser) | High | Cloud loses email triage | Circuit breaker OPEN state + `Needs_Action/manual/` for re-auth. Token is read-only scoped. |
| E2.1.Micro OOM (1GB RAM) with all services running | Medium | Cloud services crash | PM2 restart limits catch this. Reduce poll intervals. Monitor via `health.json`. |
| Git merge conflict on claim-by-move | Low | One sync cycle fails | Claim-by-move uses atomic rename; conflicts only possible if both agents commit within same second. Retry resolves. |
| `.gitignore` accidentally modified | Low | Secrets could leak | Pre-commit hook validates independently of `.gitignore` (hardcoded patterns). |

## Complexity Tracking

No constitution violations to justify. All changes are incremental extensions of existing patterns.

## Backward Compatibility (FR-029, FR-030)

- When `FTE_ROLE=local` (or unset in pre-Platinum): all Gold-tier behavior is identical
- New vault subfolders (`Needs_Action/gmail/`, etc.) are created only if `FTE_ROLE` is set
- Existing `Needs_Action/` files (flat, no domain subfolder) continue to work — `scan_needs_action()` checks both root and subfolders
- Correlation ID format change is backward-compatible: `is_valid_correlation_id()` accepts both old (4 hex) and new (8 hex) formats
- No existing API signatures change — only new guard clauses added
