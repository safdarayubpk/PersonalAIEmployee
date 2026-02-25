# Data Model: Bronze Tier

**Feature**: 001-bronze-tier
**Date**: 2026-02-24

## Entities

### Vault

The root workspace container. Not a file itself — a directory with enforced structure.

| Attribute | Type | Description |
|-----------|------|-------------|
| path | absolute path | From `VAULT_PATH` env var, default `/home/safdarayub/Documents/AI_Employee_Vault` |
| initialized | boolean | True if all 7 folders and 2 files exist |

**Invariants**:
- Path MUST be absolute. Relative paths are rejected (FR-008).
- All child paths MUST resolve within this root.

### Needs_Action File

A markdown file with YAML frontmatter describing an event requiring processing.

| Field | Location | Type | Required | Constraints |
|-------|----------|------|----------|-------------|
| title | frontmatter | string | yes | Descriptive, kebab-case filename |
| created | frontmatter | ISO 8601 datetime | yes | Set at creation time |
| tier | frontmatter | enum | yes | `bronze` (fixed for this tier) |
| source | frontmatter | string | yes | Component that created it (e.g., `file-drop-watcher`) |
| priority | frontmatter | enum | yes | `routine` \| `sensitive` \| `critical` |
| status | frontmatter | enum | yes | `needs_action` → `done` \| `deferred_to_approval` |
| what_happened | body section | markdown | yes | Description of the triggering event |
| suggested_action | body section | markdown | yes | Recommended action |
| context | body section | markdown | yes | File paths, error details, references |

**Lifecycle**:
```
Created (needs_action)
    │
    ├── Classified as routine → Plan created → Executed → Moved to Done/ (done)
    │
    └── Classified as sensitive/critical/unknown → Plan created → Moved to Pending_Approval/ (deferred_to_approval)
```

**Naming convention**: `dropped-{original-filename-stem}-{YYYYMMDD-HHMMSS}.md`

### Plan

A markdown file describing the intended action for a Needs_Action file.

| Field | Location | Type | Required |
|-------|----------|------|----------|
| title | frontmatter | string | yes |
| created | frontmatter | ISO 8601 datetime | yes |
| source_file | frontmatter | string | yes (relative path to original Needs_Action file) |
| risk_level | frontmatter | enum | yes (`low` \| `high`) |
| status | frontmatter | enum | yes (`planned` → `completed` \| `pending_approval`) |
| action_plan | body section | markdown | yes |
| risk_assessment | body section | markdown | yes |
| expected_outcome | body section | markdown | yes |

**Naming convention**: `plan-{original-filename-stem}-{YYYYMMDD-HHMMSS}.md`

### Dashboard

A single markdown file providing real-time agent status.

| Section | Content | Updated by |
|---------|---------|------------|
| Header | Title, creation date, vault path | setup_vault.py (once) |
| Status overview | Current state summary | check-and-process-needs-action (each run) |
| Processing history | Timestamped summary tables | check-and-process-needs-action (appended) |

**File**: `Dashboard.md` (vault root)

### Company Handbook

A single markdown file defining action classification rules.

| Section | Content |
|---------|---------|
| Routine actions | Actions the agent auto-executes (file organization, notes, reports, summaries) |
| Sensitive actions | Actions requiring HITL approval (email, messages, social media, financial records) |
| Critical actions | Actions requiring HITL + confirmation (payments, deletions, legal, credentials) |
| Examples | At least 2 concrete examples per category |

**File**: `Company_Handbook.md` (vault root)

### Log Entry (JSONL)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| timestamp | ISO 8601 string | yes | When the action occurred |
| component | string | yes | Which component performed it (e.g., `setup-vault`, `file-drop-watcher`, `vault-interact`) |
| action | string | yes | What was done (e.g., `create_folder`, `write_file`, `move_file`) |
| status | enum | yes | `success` \| `failure` \| `skipped` |
| detail | string | yes | Human-readable description |

**Files**:
- `Logs/vault_operations.jsonl` — all vault mutations
- `Logs/actions.jsonl` — processing actions
- `Logs/errors.jsonl` — error details with stack traces

## Relationships

```
Vault (root)
├── contains → Dashboard (1)
├── contains → Company_Handbook (1)
├── contains → Needs_Action File (0..n)
│                  └── produces → Plan (1:1)
│                  └── routes to → Done/ or Pending_Approval/
├── contains → Log Entry (0..n) via JSONL files
└── monitored by → Watcher (external, via drop folder)
```
