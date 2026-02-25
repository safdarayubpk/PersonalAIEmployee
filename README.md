# Personal AI Employee — Bronze Tier

A local-first autonomous AI agent that watches a drop folder, triages incoming files, and routes them through an Obsidian vault — all without cloud services or external APIs. Built for the 2026 Personal AI Employee Hackathon.

## What It Does

1. **You drop a file** into `~/Desktop/DropForAI`
2. **The watcher** detects it and creates a metadata `.md` file in `Needs_Action/`
3. **Claude Code skills** classify the file by risk level, create an action plan, and route it:
   - Routine tasks → `Done/` (auto-executed)
   - Sensitive/critical tasks → `Pending_Approval/` (human review required)
4. **Dashboard.md** is updated with a processing summary

No cloud, no external APIs, no MCP servers. Everything stays on your machine.

## Features

- **Obsidian Vault** at `/home/safdarayub/Documents/AI_Employee_Vault` with 7 folders, `Dashboard.md`, and `Company_Handbook.md`
- **Filesystem Watcher** — Watchdog-based, monitors a configurable drop folder, PID lock for single-instance, 0.5s debounce, clean signal handling
- **3 Claude Code Skills**:
  - `vault-interact` — Safe read/write/append/list/move/create operations scoped to vault root
  - `process-needs-action` — Per-file triage: classify risk, create plan, execute or defer
  - `check-and-process-needs-action` — Top-level orchestrator, processes up to 5 files per run
- **JSONL Logging** — All operations logged to `Logs/vault_operations.jsonl`, errors to `Logs/errors.jsonl`, actions to `Logs/actions.jsonl`
- **Atomic Writes** — All file creation uses temp-file + rename for crash safety
- **Path Validation** — Every file operation is validated against the vault root; traversal attempts are rejected
- **PM2 Support** — `config/ecosystem.config.js` for running the watcher as a daemon
- **Idempotent Setup** — `setup_vault.py` is safe to re-run; skips existing items

## Prerequisites

- Python 3.13+
- [watchdog](https://pypi.org/project/watchdog/) (`pip install watchdog`)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 2.1.x (for running skills)
- Obsidian v1.11.x+ (optional, for viewing vault files)

## Quick Start

### 1. Initialize the vault

```bash
cd /home/safdarayub/Desktop/claude/fte
python src/setup_vault.py
```

Creates 7 folders + `Dashboard.md` + `Company_Handbook.md` in the vault. Safe to re-run.

### 2. Start the watcher

```bash
python src/file_drop_watcher.py
```

Options:

```bash
python src/file_drop_watcher.py --drop-folder ~/Desktop/DropForAI
python src/file_drop_watcher.py --vault-path /custom/vault/path
```

Or with PM2:

```bash
pm2 start config/ecosystem.config.js
```

### 3. Drop a file

```bash
cp some-document.pdf ~/Desktop/DropForAI/
```

The watcher prints `Created: Needs_Action/dropped-some-document-20260225-120000.md`.

### 4. Process with Claude Code

```bash
cd /home/safdarayub/Documents/AI_Employee_Vault
claude "check and process needs action"
```

Claude triages each file, creates plans, routes results, and updates the dashboard.

### 5. Check results

- `Done/` — Completed routine tasks with result files
- `Pending_Approval/` — Sensitive items awaiting human review
- `Dashboard.md` — Processing summary table

## How to Test

A manual test plan with 9 scenarios is at `tests/manual/bronze-tier-test-plan.md`.

Quick smoke test:

```bash
# Terminal 1: Start watcher
python src/file_drop_watcher.py

# Terminal 2: Drop a test file
echo "Test file content" > ~/Desktop/DropForAI/test-file.txt

# Wait 2 seconds, then check
ls /home/safdarayub/Documents/AI_Employee_Vault/Needs_Action/

# Process it
cd /home/safdarayub/Documents/AI_Employee_Vault
claude "check and process needs action"

# Verify routing
ls Done/
cat Dashboard.md
```

## Project Structure

```
fte/
├── src/
│   ├── vault_helpers.py         # Shared utilities (path validation, logging, atomic writes)
│   ├── setup_vault.py           # Idempotent vault initialization
│   └── file_drop_watcher.py     # Watchdog filesystem watcher
├── vault_content/
│   ├── dashboard-template.md    # Template for Dashboard.md
│   └── company-handbook.md      # Template for Company_Handbook.md (risk rules)
├── config/
│   └── ecosystem.config.js      # PM2 daemon configuration
├── tests/
│   └── manual/
│       └── bronze-tier-test-plan.md  # 9 test scenarios (SC-001 to SC-009)
├── .claude/
│   └── skills/
│       ├── vault-interact/          # Safe vault file operations
│       ├── process-needs-action/    # Per-file triage and routing
│       └── check-and-process-needs-action/  # Batch orchestrator
├── specs/
│   └── 001-bronze-tier/         # Spec, plan, tasks, contracts, research
└── .gitignore
```

## Configuration

| Setting | Default | Override |
|---------|---------|----------|
| Vault path | `/home/safdarayub/Documents/AI_Employee_Vault` | `VAULT_PATH` env var or `--vault-path` |
| Drop folder | `~/Desktop/DropForAI` | `DROP_FOLDER` env var or `--drop-folder` |

## Next Steps — Silver Tier

- Multiple watchers (Gmail, WhatsApp, calendar)
- MCP server integration for external actions
- Scheduled processing via cron/PM2
- Ralph Wiggum persistence loop for task retry
- Advanced error recovery and parallel processing
