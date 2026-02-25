# Implementation Plan: Bronze Tier

**Branch**: `001-bronze-tier` | **Date**: 2026-02-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-bronze-tier/spec.md`

## Summary

Implement the Bronze tier of the Personal AI Employee: an idempotent vault setup script, a Watchdog-based filesystem watcher that creates Needs_Action metadata files, and end-to-end integration with three existing Claude Code skills (vault-interact, process-needs-action, check-and-process-needs-action). All operations are local-first, dry-run only, and log every mutation to JSONL files.

## Technical Context

**Language/Version**: Python 3.13+
**Primary Dependencies**: watchdog (filesystem events), pathlib (path operations), json (JSONL logging), datetime (ISO 8601 timestamps), signal/os (PID lock management)
**Storage**: Local filesystem — markdown files with YAML frontmatter in Obsidian vault at `/home/safdarayub/Documents/AI_Employee_Vault`
**Testing**: Manual end-to-end test scenarios (drop file → watcher → process → verify). No automated test framework required for Bronze.
**Target Platform**: Linux (Ubuntu 22.04+), single-user local machine
**Project Type**: Single project — two Python scripts + vault content files + existing Claude Code skills
**Performance Goals**: Watcher detection <5s, single file E2E <60s, 5-file batch <5min, 10-min stability run
**Constraints**: Local-only (no cloud/network for user data), dry-run mode only, max 5 files per batch, single watcher instance (PID lock), no file deletion (`.moved` rename pattern)
**Scale/Scope**: Single user, single watcher, <100 vault files, hackathon demo scope

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Post-design re-check: ✅ ALL GATES PASS (2026-02-24). JSONL standardization confirmed in all 4 contract files.*

| Principle | Gate | Status | Evidence |
|-----------|------|--------|----------|
| I. Local-First | No user data leaves device | ✅ PASS | All ops scoped to vault path. No network calls. Claude API used for reasoning only (no raw vault content). |
| II. HITL Safety | High-risk actions require Pending_Approval gate | ✅ PASS | FR-009/FR-011: sensitive/critical/unknown → Pending_Approval/. FR-018: dry-run mode enforced. |
| III. Proactive Autonomy | Agent watches for events without prompting | ✅ PASS | Watchdog watcher monitors drop folder. Ralph Wiggum loop explicitly out of scope for Bronze (manual trigger). |
| IV. Modularity | Bronze tier only, no higher-tier dependencies | ✅ PASS | Not in Scope explicitly excludes Silver/Gold/Platinum features. |
| V. Cost-Efficiency | Design supports cost tracking | ✅ PASS | Dashboard summaries enable cost-per-task analysis. Log entries are countable. |
| VI. Error Handling | All failures logged and visible | ✅ PASS | FR-019: PID lock. FR-012/FR-013: mutation logging. Edge cases: atomic writes, error logging, graceful exit. |
| Vault conventions | kebab-case, YAML frontmatter, absolute paths | ✅ PASS | FR-005: frontmatter fields defined. FR-008: path validation. Constitution naming convention applied. |
| Log format | All logs use JSONL | ✅ PASS | Resolved: all skills (vault-interact, check-and-process) and spec updated from `.log` to `.jsonl`. All log files use JSONL with required fields: timestamp, component, action, status, detail. |

**Gate result**: PASS (1 minor inconsistency resolved in-plan)

## Project Structure

### Documentation (this feature)

```text
specs/001-bronze-tier/
├── plan.md              # This file
├── research.md          # Phase 0: technology decisions
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: setup and usage guide
├── contracts/           # Phase 1: file format contracts
│   ├── needs-action-format.md
│   ├── plan-format.md
│   ├── dashboard-format.md
│   └── log-formats.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
src/
├── setup_vault.py           # Idempotent vault initialization (FR-001 to FR-003, FR-017)
├── file_drop_watcher.py     # Watchdog-based filesystem watcher (FR-004, FR-005, FR-019)
└── vault_helpers.py         # Shared utilities: path validation, JSONL logging, frontmatter generation

vault_content/
├── dashboard-template.md    # Template for Dashboard.md (FR-002)
└── company-handbook.md      # Template for Company_Handbook.md (FR-003)

config/
└── ecosystem.config.js          # PM2 config for file_drop_watcher.py (FR-019, Reproducibility)

tests/
└── manual/
    └── bronze-tier-test-plan.md  # Manual test scenarios for SC-001 through SC-009
```

**Structure Decision**: Single project with flat `src/` directory. Only two Python scripts needed — complexity does not warrant subdirectories. `vault_content/` holds templates that `setup_vault.py` copies into the vault. Claude Code skills (already in `.claude/skills/`) handle all processing logic.

## Design Decisions

### D1: Two Python scripts, not one monolith

The watcher (`file_drop_watcher.py`) runs as a long-lived daemon. The setup (`setup_vault.py`) runs once and exits. Separating them means the setup can be re-run without restarting the watcher, and the watcher can be managed independently via PM2.

### D2: Claude Code skills handle all processing logic

The three existing skills (vault-interact, process-needs-action, check-and-process-needs-action) are Claude Code prompt-based skills, not Python scripts. They guide Claude's behavior using its native Read/Write/Glob tools. The Python scripts only handle: (a) vault initialization and (b) filesystem watching + Needs_Action file creation. All triage, routing, and dashboard updates happen through Claude Code skill invocation.

### D3: JSONL for all logs (constitution alignment)

The constitution mandates JSONL format for all logs. The vault-interact skill currently references `vault_operations.log` (plain text). **Resolution**: All log files use `.jsonl` extension and JSON Lines format with required fields: `timestamp`, `component`, `action`, `status`, `detail`. The vault-interact skill will be updated to reference `vault_operations.jsonl`.

### D4: Atomic writes via temp-file + rename

Per constitution Principle VI, all file mutations use write-to-temp then `os.rename()` to prevent partial writes if the process crashes mid-write. This applies to: Needs_Action file creation by the watcher, and any vault file write by setup_vault.py.

### D5: Watcher creates metadata only, leaves originals untouched

The watcher does NOT move or modify the dropped file. It only creates a metadata `.md` file in `Needs_Action/` referencing the original. This follows the constitution's "no file deletion" rule and keeps the drop folder simple.

## Component Mapping

| Component | Type | Implements | Depends on |
|-----------|------|-----------|------------|
| `setup_vault.py` | Python script | FR-001, FR-002, FR-003, FR-017 | vault_helpers.py |
| `file_drop_watcher.py` | Python script | FR-004, FR-005, FR-019 | watchdog, vault_helpers.py |
| `vault_helpers.py` | Python module | FR-008, FR-012 (shared utilities) | pathlib, json, datetime |
| vault-interact skill | Claude Code skill | FR-006, FR-007, FR-008, FR-012, FR-016 | Claude native tools |
| process-needs-action skill | Claude Code skill | FR-009, FR-010, FR-011, FR-013 | vault-interact |
| check-and-process skill | Claude Code skill | FR-014, FR-015, FR-018 | vault-interact, process-needs-action |
| Dashboard.md | Vault file | FR-002, FR-014 | Created by setup_vault.py |
| Company_Handbook.md | Vault file | FR-003, FR-009 | Created by setup_vault.py |

## Complexity Tracking

> No Constitution Check violations to justify. All gates pass.

| Area | Decision | Rationale |
|------|----------|-----------|
| Log format standardization | Changed `.log` → `.jsonl` | Constitution mandates JSONL; minor skill update needed |
| `critical_actions.jsonl` | Deferred (not implemented in Bronze) | Constitution II requires critical actions log to `Logs/critical_actions.jsonl` with user acknowledgment. In Bronze tier, dry-run mode (FR-018) prevents any action from executing — critical files route to `Pending_Approval/` with a proposal but never execute. The log would have zero entries. Will implement in Silver tier when live mode becomes available. |
| Stale Pending_Approval detection | Deferred (not implemented in Bronze) | Constitution VI requires orphaned `Pending_Approval/` files older than 48h to be flagged in Dashboard.md. Bronze uses manual trigger only (no scheduled runs), so staleness detection has no automated trigger. Will implement in Silver tier alongside scheduling. |
