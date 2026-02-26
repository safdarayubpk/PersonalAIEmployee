# Data Model: Silver Tier

**Date**: 2026-02-26
**Source**: [spec.md](spec.md) Key Entities section

## Entities

### 1. Needs_Action File

**Storage**: Markdown file in `{VAULT_PATH}/Needs_Action/`
**Identity**: Filename (unique, generated: `{source-prefix}-{slug}-{YYYYMMDD-HHMMSS}.md`)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| title | string | YES | kebab-case, descriptive |
| created | string | YES | ISO 8601 `YYYY-MM-DDTHH:MM:SS` (UTC) |
| tier | enum | YES | `bronze\|silver\|gold\|platinum` |
| source | string | YES | One of: `file-drop-watcher`, `gmail-watcher`, `whatsapp-watcher`, `daily-scheduler` |
| priority | enum | YES | `routine\|sensitive\|critical` (constitution-canonical) |
| status | enum | YES | `needs_action\|processing\|done\|error` |

**Source-specific fields**:

| Source | Extra Fields |
|--------|-------------|
| gmail-watcher | `gmail_id` (string) |
| whatsapp-watcher | `chat_type` (string: `direct\|group`) |
| daily-scheduler | `type` (string: `scheduled`), `task` (string: job ID), `schedule` (string) |
| file-drop-watcher | None (Bronze format) |

**State Transitions**:

```text
needs_action → processing → done          (routine, successful)
needs_action → processing → pending_approval → approved → done  (sensitive/critical)
needs_action → processing → needs_action   (error, reset for retry)
```

### 2. Action Registry Entry

**Storage**: JSON object in `config/actions.json`
**Identity**: `action_id` (format: `{domain}.{function}`, unique)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| action_id | string | YES | Format: `domain.function_name` |
| description | string | YES | Human-readable |
| hitl_required | boolean | YES | `true` = approval gate, `false` = exempt |
| module | string | YES | Python module path relative to `src/` (e.g., `actions.email`) |
| function | string | YES | Function name in module (e.g., `send_email`) |

**Registry contents** (6 actions, 4 domains):

| action_id | domain | hitl_required | module | function |
|-----------|--------|---------------|--------|----------|
| email.send_email | email | true | actions.email | send_email |
| email.draft_email | email | false | actions.email | draft_email |
| social.post_social | social | true | actions.social | post_social |
| calendar.create_event | calendar | true | actions.calendar_actions | create_event |
| calendar.list_events | calendar | false | actions.calendar_actions | list_events |
| documents.generate_report | documents | false | actions.documents | generate_report |

### 3. Pending Approval File

**Storage**: Markdown file in `{VAULT_PATH}/Pending_Approval/`
**Identity**: Filename (format: `pending-{action_id}-{request_id}-{YYYYMMDD-HHMMSS}.md`)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| title | string | YES | `pending-{action_id}` |
| created | string | YES | ISO 8601 UTC |
| type | string | YES | `pending-action` |
| action_id | string | YES | Must match registry entry |
| request_id | string | YES | UUID or timestamp-based unique ID |
| status | string | YES | `pending_approval` |

**Body contains**: action parameters (JSON), approval instructions, dry-run result preview.

### 4. Scheduled Task (Job Config)

**Storage**: JSON object in `config/schedules.json` → `jobs[]` array
**Identity**: `id` field (unique string, kebab-case)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| id | string | YES | Unique, kebab-case |
| description | string | YES | Human-readable |
| interval | enum | NO | `daily\|weekly` (if no `cron`) |
| day | string | NO | Day of week (weekly jobs only) |
| time | string | NO | `HH:MM` format, hour 0-23, minute 0-59 |
| cron | string | NO | Cron expression (overrides interval) |
| timezone | string | YES | IANA timezone (default: `Asia/Karachi`) |
| priority | enum | YES | `routine\|sensitive\|critical` (default: `sensitive`) |
| enabled | boolean | YES | `true\|false` |

### 5. Retry Attempt Log Entry

**Storage**: JSONL entry in `{VAULT_PATH}/Logs/retry.jsonl`
**Identity**: Combination of `task_id` + `attempt`

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| timestamp | string | YES | ISO 8601 UTC |
| component | string | YES | `ralph-retry` |
| action | string | YES | `attempt\|success\|failure\|abort` |
| status | string | YES | `success\|failure` |
| task_id | string | YES | Description of retried task |
| attempt | integer | YES | 1-based attempt number |
| delay_seconds | float | NO | Backoff delay before this attempt |
| error | string | NO | Error message (on failure) |
| detail | string | YES | Human-readable summary |

### 6. Orchestrator Run Summary

**Storage**: JSONL entry in `{VAULT_PATH}/Logs/orchestrator.jsonl` + Dashboard.md append
**Identity**: `run_id` (format: `orch-YYYYMMDD-HHMMSS`)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| run_id | string | YES | `orch-{timestamp}` |
| scanned | integer | YES | Total files found in Needs_Action/ |
| processed | integer | YES | Files moved to Done/ |
| action_calls | integer | YES | Dry-run action attempts |
| pending_approval | integer | YES | Files moved to Pending_Approval/ |
| deferred | integer | YES | Files exceeding batch size |
| errors | integer | YES | Processing errors |
| by_source | object | YES | `{source_name: count}` breakdown |

### 7. JSONL Log Entry (Shared Format)

**Storage**: Various `{VAULT_PATH}/Logs/*.jsonl` files
**Identity**: None (append-only)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| timestamp | string | YES | ISO 8601 UTC |
| component | string | YES | Component name (e.g., `gmail-watcher`) |
| action | string | YES | Action performed |
| status | string | YES | `success\|failure\|skipped` |
| detail | string | YES | Human-readable description |

**Redaction rule (FR-016)**: Any key containing `password`, `token`, `secret`, `api_key`, `credential`, or `auth` → value replaced with `***REDACTED***`.

**Critical action log** (`Logs/critical_actions.jsonl`): Uses shared JSONL format plus additional fields: `action_id`, `request_id`, `approval_ref`, `acknowledgment_required` (boolean). Per constitution II, critical-risk actions that complete live execution MUST append an entry here.

## Relationships

```text
Watcher ──creates──▶ Needs_Action File
Scheduler ──creates──▶ Needs_Action File
Orchestrator ──reads──▶ Needs_Action File
Orchestrator ──routes──▶ Done/ or Pending_Approval/
Orchestrator ──calls──▶ Action Executor (dry-run)
Action Executor ──reads──▶ Action Registry
Action Executor ──imports──▶ src/actions/*.py
Action Executor ──creates──▶ Pending Approval File (if HITL)
User ──moves──▶ Pending Approval File → Approved/
Action Executor ──reads──▶ Approved/ (with --approval-ref)
All Components ──write──▶ JSONL Log Entries
Orchestrator ──appends──▶ Dashboard.md
```
