# Data Model: Platinum Tier — Cloud-Local Hybrid Operation

**Feature**: 004-platinum-tier | **Date**: 2026-03-11

## Entities

### 1. Task File

A markdown file with YAML frontmatter that flows through vault workflow folders.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Descriptive kebab-case title |
| `created` | ISO 8601 datetime | Yes | Creation timestamp (UTC) |
| `tier` | enum | Yes | `bronze`, `silver`, `gold`, `platinum` |
| `source` | string | Yes | Originating component (e.g., `gmail-watcher`, `daily-scheduler`) |
| `priority` | enum | Yes | `routine`, `sensitive`, `critical` |
| `status` | enum | Yes | Current lifecycle status (see State Transitions) |
| `agent` | enum | Platinum only | `cloud` or `local` — which agent created/owns the file |
| `correlation_id` | string | Platinum only | Format: `corr-YYYY-MM-DD-XXXXXXXX` |
| `gmail_id` | string | Gmail tasks only | Gmail message ID for deduplication |
| `rejection_reason` | string | Rejected files only | Why the draft was rejected |

**State Transitions**:

```
needs_action → in_progress → pending_approval → approved → done
                                    ↓
                                rejected → (re-draft → needs_action)
                                         → (escalate → needs_action/manual/)
```

| Status | Folder | Who Sets |
|--------|--------|----------|
| `needs_action` | `Needs_Action/<domain>/` | Watcher or scheduler |
| `in_progress` | `In_Progress/<role>/` | Claiming agent (via claim-by-move) |
| `pending_approval` | `Pending_Approval/<domain>/` | Processing agent (cloud drafts here) |
| `approved` | `Approved/` | User (manual move in Obsidian) |
| `rejected` | `Rejected/` | Local agent (with rejection_reason) |
| `done` | `Done/` | Executing agent (after successful action) |

**Validation Rules**:
- `title` must be kebab-case, no spaces or uppercase
- `created` must be valid ISO 8601 (YYYY-MM-DDTHH:MM:SS)
- `tier` must match current operational tier
- `priority` must be one of the canonical values (routine/sensitive/critical)
- `agent` and `correlation_id` MUST be present for Platinum tier, MUST be omitted for Bronze–Gold
- `correlation_id` must match `corr-YYYY-MM-DD-XXXXXXXX` pattern (or legacy `corr-YYYYMMDD-HHMMSS-XXXX`)

---

### 2. Update File

A timestamped markdown file in `Updates/` containing incremental status changes from the cloud agent.

**Fields** (in frontmatter):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | `dashboard-update-<ISO-timestamp>` |
| `created` | ISO 8601 datetime | Yes | Creation timestamp |
| `agent` | enum | Yes | Always `cloud` (only cloud writes updates) |
| `source` | string | Yes | Component that generated the update |
| `update_type` | string | Yes | `email_triage`, `task_complete`, `draft_created`, `health_status` |

**Body**: Free-form markdown summarizing what happened.

**Lifecycle**: Created by cloud → synced via git → read and merged by local → deleted after merge.

---

### 3. Sync State

Tracked in `Logs/sync.jsonl` as JSONL entries.

**Log Entry Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 | When the sync cycle ran |
| `component` | string | Always `git-sync` |
| `agent` | enum | `cloud` or `local` |
| `action` | string | `pull`, `commit`, `push`, `conflict`, `retry`, `offline` |
| `status` | enum | `success`, `failure`, `skipped` |
| `detail` | string | Human-readable description |
| `files_changed` | int | Number of files in this sync |
| `retry_count` | int | Number of push retries (0 if first attempt succeeded) |

---

### 4. Agent Role

Runtime configuration entity (not persisted as a file).

| Property | Type | Description |
|----------|------|-------------|
| `role` | enum | `cloud` or `local` (from `FTE_ROLE` env var) |
| `permitted_risk_levels` | list | Cloud: `[routine]`. Local: `[routine, sensitive, critical]` |
| `writable_targets` | list | Cloud: `In_Progress/cloud/`, `Updates/`, `Pending_Approval/*/` (drafts). Local: everything. |
| `read_only_targets` | list | Cloud: `Dashboard.md`, `Company_Handbook.md`, `Logs/critical_actions.jsonl` |

---

### 5. Circuit Breaker State (existing, extended)

Persisted in `Logs/health.json`.

**Extended for Platinum**:

| Field | Type | Description |
|-------|------|-------------|
| `agent` | enum | NEW: Which agent's circuit breaker state this is |
| `service` | string | Service name (e.g., `gmail`, `odoo`, `git-sync`) |
| `state` | enum | `healthy`, `degraded`, `down` |
| `failure_count` | int | Consecutive failures |
| `last_failure` | ISO 8601 | Timestamp of last failure |
| `cooldown_until` | ISO 8601 | When to retry |

## Relationships

```
Task File 1──∞ JSONL Log Entries (linked by correlation_id)
Task File 1──0..∞ Update Files (cloud generates updates about task progress)
Agent Role 1──∞ Task Files (agent field in frontmatter)
Circuit Breaker 1──1 Service (per-service state)
```

## Folder-Domain Mapping

| Domain | Needs_Action Subfolder | Pending_Approval Subfolder | Source Watcher |
|--------|----------------------|---------------------------|----------------|
| Gmail | `gmail/` | `gmail/` | `gmail-watcher` |
| WhatsApp | `whatsapp/` | N/A (local-only) | `whatsapp-watcher` |
| Scheduler | `scheduler/` | `general/` | `daily-scheduler` |
| Manual | `manual/` | `general/` | User or escalation |
| Social | N/A | `social/` | Orchestrator |
| Odoo | N/A | `odoo/` | Orchestrator |
