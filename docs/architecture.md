# Personal AI Employee — System Architecture

## Overview

The Personal AI Employee is a three-tier autonomous AI assistant that monitors multiple input channels, processes tasks with human-in-the-loop safety gates, executes external actions via MCP servers, and provides proactive business insights through CEO briefings. The system is built on local-first principles with zero cloud dependencies.

### Tier Summary

| Tier | Input Sources | Action Execution | Processing | External Services |
|------|---------------|------------------|------------|-------------------|
| **Bronze** | File drop (watchdog) | None | Risk triage, routing | None |
| **Silver** | File drop + Gmail + WhatsApp | Direct Python functions (importlib) | Multi-source orchestration, retries | Gmail API, WhatsApp Web |
| **Gold** | File drop + Gmail + WhatsApp + Scheduler | MCP servers (stdio) | Same + circuit breaker, correlation IDs | Gmail, WhatsApp, 4 MCP servers, Odoo ERP |

## System Component Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                         INPUT WATCHERS                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ File Drop Watcher│  │   Gmail Watcher  │  │ WhatsApp Watcher │ │
│  │   (watchdog)     │  │  (OAuth2 polling)│  │ (Playwright)     │ │
│  │   Bronze         │  │   Silver         │  │   Silver         │ │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘ │
│           │                     │                     │             │
│           └─────────────────────┼─────────────────────┘             │
│                                 │                                   │
│  ┌──────────────────────────────┴──────────────────────────────┐   │
│  │         correlation_id: corr-YYYYMMDD-HHMMSS-XXXX          │   │
│  │    (generated at watcher level, propagated to all logs)     │   │
│  └──────────────────────────────┬──────────────────────────────┘   │
│                                 ▼                                   │
│                ┌────────────────────────────┐                       │
│                │   Scheduler Daemon (Silver)│                       │
│                │     APScheduler (in-mem)   │                       │
│                │  Creates scheduled tasks   │                       │
│                └────────────────┬───────────┘                       │
│                                 │                                   │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────────┐
        │     Needs_Action/ (vault folder)                │
        │  YAML frontmatter:                              │
        │   - title, created, tier, source                │
        │   - priority (routine|sensitive|critical)       │
        │   - correlation_id                              │
        │   - status (needs_action|processing)            │
        └──────────────────────┬──────────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────────────┐
        │         Central Orchestrator (Silver)                 │
        │  1. Scan Needs_Action/*.md                           │
        │  2. Queue by priority: critical → sensitive → routine │
        │  3. Batch process (default: 10, max: 50 files)       │
        │  4. Risk assessment (keyword scan)                    │
        │  5. Route:                                            │
        │     - Routine: Done/                                  │
        │     - Sensitive/Critical: Pending_Approval/           │
        │  6. Check action mapping (Needs_Action.type)          │
        │  7. Dispatch to action executor or MCP              │
        │  8. Update Dashboard.md + Health status               │
        └──────────────┬────────────────────────┬───────────────┘
                       │                        │
          ┌────────────┴──────────┐  ┌──────────┴──────────┐
          │                       │  │                     │
          ▼                       ▼  ▼                     ▼
    ┌────────────┐         ┌──────────────┐      ┌───────────────────┐
    │  Done/     │         │Pending_      │      │ MCP Router        │
    │(routine)   │         │Approval/     │      │ (Gold tier)       │
    │            │         │(sens/crit)   │      │                   │
    └────────────┘         └─────┬────────┘      └────────┬──────────┘
                                 │                        │
                    HUMAN        │                        │
                   REVIEW        ▼                        ▼
                                 │                  ┌─────────────────────┐
                         ┌───────┴────────┐        │  MCP Servers (Gold) │
                         │   Approved/    │        │  (stdio transport)  │
                         │  + --live flag │        └────────────────────┘
                         └───────┬────────┘        │
                                 │            ┌────┼───────┬───────┐
                                 │            │    │       │       │
                    ┌────────────┴──┐         ▼    ▼       ▼       ▼
                    │ Action         │    ┌────────┬─────┬────────┬──────┐
                    │ Executor       │    │ Email  │Social│Documents│Odoo │
                    │ (Silver)       │    │ Server │Server│ Server  │ERP  │
                    │                │    └────────┴─────┴────────┴──────┘
                    └────────────────┘        │
                          │                  │ (live mode only,
                    ┌─────┴──────┐            │  after HITL)
                    │  src/       │           │
                    │  actions/   │           ▼
                    │  *.py funcs │    ┌─────────────────────┐
                    │             │    │ External APIs       │
                    └─────────────┘    │ - Gmail API         │
                                       │ - Facebook Graph    │
                                       │ - Instagram Graph   │
                                       │ - Twitter API v2    │
                                       │ - Odoo JSON-RPC     │
                                       └─────────────────────┘
```

## Vault Folder Structure

```
/home/safdarayub/Documents/AI_Employee_Vault/
├── Needs_Action/          # Files awaiting processing
├── Done/                  # Completed routine tasks
├── Pending_Approval/      # Sensitive/critical items awaiting human review
├── Approved/              # Human-approved actions waiting execution
├── Plans/                 # Generated action plans
├── Briefings/             # CEO briefings (Gold tier)
└── Logs/
    ├── vault_operations.jsonl     # Vault read/write/move operations
    ├── errors.jsonl               # All system errors
    ├── actions.jsonl              # Action executor calls (Silver)
    ├── retry.jsonl                # Ralph Wiggum retry attempts (Silver)
    ├── scheduler.jsonl            # Scheduled task triggers (Silver)
    ├── orchestrator.jsonl         # Orchestrator routing decisions
    ├── critical_actions.jsonl     # HITL critical action confirmations (Gold)
    ├── mcp_email.jsonl            # Email MCP server calls (Gold)
    ├── mcp_social.jsonl           # Social media MCP calls (Gold)
    ├── mcp_odoo.jsonl             # Odoo ERP MCP calls (Gold)
    ├── mcp_documents.jsonl        # Documents MCP calls (Gold)
    ├── health.json                # Circuit breaker states (Gold)
    ├── *.pid                      # Process ID lock files
    └── retry_queue.jsonl          # Rate-limited/deferred actions (Gold)
```

## Data Flow Through Tiers

### Bronze Tier: File Detection → Risk Triage → Routing

```
file_drop_watcher --drop-folder ~/Desktop/DropForAI
  │ detects new file
  ├─ create Needs_Action/dropped-filename-timestamp.md
  │  frontmatter: title, created, tier, source, priority, status
  │
  └─ watcher logs to Logs/vault_operations.jsonl

check-and-process-needs-action (Claude Code skill)
  │ orchestrator logic (simplified):
  │ ├─ scan Needs_Action/*.md
  │ ├─ assess risk via keywords
  │ └─ route:
  │    ├─ routine → Done/
  │    └─ sensitive/critical → Pending_Approval/
  │
  └─ orchestrator logs to Logs/orchestrator.jsonl
```

### Silver Tier: Multi-Source Input + Action Execution + Retry + Scheduling

Extends Bronze with:

- **gmail-watcher**: Polls Gmail API every 60s, creates Needs_Action for new emails, source=gmail-watcher
- **whatsapp-watcher**: Monitors WhatsApp Web session, creates Needs_Action for messages, source=whatsapp-watcher
- **action-executor**: Called by orchestrator, loads action from `src/actions/*.py` via `importlib`, supports:
  - Dry-run mode (default) → log only, exit 0
  - HITL blocking (approval-required actions) → create Pending_Approval file, exit 2
  - Live mode with approval → call function, log result, exit 0/1
- **ralph-retry**: Wraps any command, retries on transient failures with exponential backoff (2s, 4s, 8s... capped at 300s, max 15 retries)
- **daily-scheduler**: APScheduler daemon, creates Needs_Action on schedule (daily/weekly/cron), runs as long-lived process

### Gold Tier: MCP Server Architecture + Circuit Breaker + CEO Briefing

Extends Silver with:

- **4 MCP Servers** (stdio transport, registered in Claude Code):
  1. **fte-email**: Draft/send emails via Gmail API (wraps src/actions/email.py functions)
  2. **fte-social**: Post to Facebook/Instagram/Twitter (wraps social media API clients)
  3. **fte-odoo**: Query/create invoices and financial data via Odoo JSON-RPC
  4. **fte-documents**: Generate reports, briefings (wraps document generation functions)

- **Circuit Breaker Pattern** (per-service health):
  ```
  Healthy (closed) →[3 failures in 5min]→ Degraded (open)
                                               ↓
                                    [5min cooldown]
                                               ↓
                                    Probing (half-open)
                                               ↓
                                   [probe succeeds]
                                               ↓
                                    Healthy (closed)
  ```

- **Correlation IDs**: Each task assigned unique ID `corr-YYYYMMDD-HHMMSS-XXXX` at watcher creation, propagated through all logs for end-to-end traceability

- **CEO Briefing**: Scheduled task (weekly, Sunday 8 PM) that generates `Briefings/YYYY-MM-DD_Monday_Briefing.md` with:
  - Executive Summary
  - Revenue & Expenses (from Odoo)
  - Completed Tasks (from Done/)
  - Social Media Activity (from logs)
  - Bottlenecks (stale Pending_Approval items)
  - Proactive Suggestions (idle subscriptions, missed targets)

## HITL (Human-In-The-Loop) Classification

Three risk levels, applied consistently:

| Level | Definition | Action | Gate |
|-------|-----------|--------|------|
| **Routine** | Low-risk operations (read-only, auto-processable) | Auto-execute or Done/ | None |
| **Sensitive** | Medium-risk (emails, social posts, calendar) | Create Pending_Approval/ | Human review required |
| **Critical** | High-risk (Odoo writes, payments, deletions) | Create Pending_Approval/ + log to critical_actions.jsonl | Human approval + confirmation log |

**HITL Workflow:**
1. Item created in Needs_Action/ with priority from risk keywords
2. Orchestrator routes to Done/ (routine) or Pending_Approval/ (sensitive/critical)
3. Developer manually reviews item in Pending_Approval/
4. Developer moves item to Approved/ folder
5. Action executor retries with `--live` flag and `--approval-ref <path-to-approved-file>`
6. Action executor verifies approval exists, executes real action, logs outcome

## Circuit Breaker State Machine

All external services (Gmail, WhatsApp, Odoo, social media APIs) monitored via circuit breaker:

```
State: closed (healthy)
  └─ Consecutive failures < 3: stay closed
  └─ Consecutive failures = 3 (within 5min window): → open

State: open (degraded)
  └─ Log "service is DEGRADED"
  └─ Update Logs/health.json
  └─ Update Dashboard.md
  └─ Queue dependent tasks for retry
  └─ After 5min cooldown: → half-open (probe)

State: half-open (probing)
  └─ Send single test request
  └─ If success: reset failures, → closed, resume normal
  └─ If failure: increment failures, → open (restart cooldown)

State: down (persistent failure)
  └─ Consecutive failures > 5 or repeated auth errors
  └─ Create Needs_Action: "Service X offline, manual attention required"
```

## Correlation ID Flow

Every task carries a correlation ID from creation through all processing stages:

```
Watcher creates Needs_Action file:
  ├─ frontmatter includes correlation_id: corr-YYYYMMDD-HHMMSS-XXXX
  │
  ▼
Orchestrator processes file:
  ├─ extracts correlation_id from frontmatter
  ├─ logs to orchestrator.jsonl WITH correlation_id
  │
  ├─ [if routine] → Logs/vault_operations.jsonl (move to Done/) WITH correlation_id
  │
  ├─ [if sensitive/critical] → Pending_Approval/ WITH correlation_id
  │                            (human review)
  │
  ├─ [if action needed] → Logs/actions.jsonl WITH correlation_id
  │
  └─ [if MCP call] → Logs/mcp_*.jsonl WITH correlation_id

Developer can trace entire lifecycle:
  grep "corr-20260301-120000-abcd" Logs/*.jsonl
  # outputs all steps: creation, triage, routing, execution, outcome
```

## Configuration Files

### config/risk-keywords.json
Shared across all watchers and orchestrator for consistent urgency classification.

```json
{
  "high": ["payment", "invoice", "legal", "delete", "critical"],
  "medium": ["email", "send", "meeting", "approve", "review"]
}
```

### config/actions.json (Silver)
Registry of available actions with HITL classification.

```json
{
  "actions": [
    {
      "id": "email.send_email",
      "description": "Send email via Gmail",
      "hitl": true,
      "module": "actions.email",
      "function": "send_email"
    },
    ...
  ]
}
```

### config/schedules.json (Silver)
Scheduler configuration (auto-created and maintained by scheduler daemon).

```json
{
  "tasks": [
    {
      "id": "daily_briefing",
      "description": "Generate Monday CEO briefing",
      "schedule_type": "weekly",
      "day_of_week": "sunday",
      "hour": 20,
      "minute": 0,
      "enabled": true
    }
  ]
}
```

### config/mcp-servers.json (Gold)
Registry of MCP servers and their tools.

```json
{
  "servers": [
    {
      "name": "fte-email",
      "domain": "email",
      "stdio_command": "python src/mcp/email_server.py",
      "tools": [
        {"name": "draft", "hitl": false},
        {"name": "send", "hitl": true}
      ]
    }
  ]
}
```

### config/social-platforms.json (Gold)
Platform-specific constraints and configurations.

```json
{
  "platforms": {
    "twitter": {"char_limit": 280, "rate_limit": "450/15min"},
    "facebook": {"char_limit": 63206, "rate_limit": "200/hour"},
    "instagram": {"caption_limit": 2200, "rate_limit": "200/hour"}
  }
}
```

### Logs/health.json (Gold)
Real-time circuit breaker state for all external services.

```json
{
  "services": [
    {
      "service": "odoo",
      "state": "healthy",
      "consecutive_failures": 0,
      "last_success": "2026-03-01T14:32:10",
      "last_failure": null,
      "cooldown_expires_at": null
    },
    {
      "service": "twitter",
      "state": "degraded",
      "consecutive_failures": 3,
      "last_success": "2026-03-01T14:20:00",
      "last_failure": "2026-03-01T14:35:00",
      "cooldown_expires_at": "2026-03-01T14:40:00"
    }
  ],
  "updated": "2026-03-01T14:35:30"
}
```

## MCP Servers (Gold Tier)

### fte-email Server
Exposes tools to draft and send emails via Gmail API.

| Tool | HITL | Input | Output |
|------|------|-------|--------|
| `draft` | routine | recipient, subject, body | file path in Plans/ |
| `send` | critical | recipient, subject, body | {status, message_id} or {status: pending_approval} |

### fte-social Server
Exposes tools for Facebook, Instagram, and Twitter posting.

| Tool | HITL | Input | Output |
|------|------|-------|--------|
| `post_facebook` | sensitive | page_id, content, media | {status, post_id} or {status: pending_approval} |
| `post_instagram` | sensitive | business_account_id, caption, image | {status, media_id} or {status: pending_approval} |
| `post_twitter` | sensitive | content, media | {status, tweet_id} or {status: pending_approval} |

All posting tools validate content length and format before attempting API call.

### fte-odoo Server
Exposes tools for reading and writing Odoo ERP data via JSON-RPC.

| Tool | HITL | Input | Output |
|------|------|-------|--------|
| `list_invoices` | routine | filter (unpaid, date range) | [{invoice_id, amount, status, date}] |
| `create_invoice` | critical | partner_id, lines, date | {invoice_id, status} or {status: pending_approval} |
| `financial_summary` | routine | date_range | {revenue, expenses, receivables, payables} |

### fte-documents Server
Exposes tools for generating reports and briefings.

| Tool | HITL | Input | Output |
|------|------|-------|--------|
| `generate_briefing` | routine | data_sources (list) | file path to Briefings/YYYY-MM-DD_Monday_Briefing.md |
| `generate_report` | routine | report_type, params | file path to Plans/report-timestamp.md |

## Process Management

All long-running processes managed via PM2:

```bash
# Start all components
pm2 start config/ecosystem.config.js

# Includes:
# - file_drop_watcher (Bronze)
# - gmail-watcher (Silver)
# - whatsapp-watcher (Silver)
# - daily-scheduler (Silver)
# - fte-email MCP server (Gold)
# - fte-social MCP server (Gold)
# - fte-odoo MCP server (Gold)
# - fte-documents MCP server (Gold)

# Monitor
pm2 monit

# Logs
pm2 logs
```

Each process maintains a PID lock file in `Logs/<process-name>.pid` and handles SIGTERM/SIGINT for graceful shutdown.

## Logging Strategy

All operations logged to JSONL files for audit and debugging:

| Log File | Purpose | Sample Entry |
|----------|---------|--------------|
| `vault_operations.jsonl` | All file reads/writes/moves | `{timestamp, component, action, file, status}` |
| `errors.jsonl` | System errors | `{timestamp, component, error_class, message, traceback}` |
| `actions.jsonl` | Action executor calls (Silver) | `{timestamp, action_id, status, params, result}` |
| `retry.jsonl` | Ralph Wiggum retry attempts | `{timestamp, attempt, delay, status, error}` |
| `orchestrator.jsonl` | Routing decisions | `{timestamp, file, priority, route, reason}` |
| `critical_actions.jsonl` | HITL critical approvals (Gold) | `{timestamp, action, approved_by, timestamp_approved}` |
| `mcp_email.jsonl` | Email MCP calls | `{timestamp, tool, action, status, correlation_id}` |
| `mcp_social.jsonl` | Social media MCP calls | `{timestamp, platform, content, post_id}` |
| `mcp_odoo.jsonl` | Odoo ERP MCP calls | `{timestamp, model, operation, result}` |

All entries include ISO 8601 timestamps and correlation IDs for end-to-end traceability.

## Dashboard.md Content

Updated after each orchestrator run:

```markdown
# Dashboard

## Status Summary (Last Updated: 2026-03-01 14:35:30 UTC)

### Run Statistics (Last Orchestrator Run)
| Metric | Value |
|--------|-------|
| Files Scanned | 12 |
| Files Processed | 10 |
| Actions Attempted | 2 |
| Files Pending Approval | 3 |
| Files Deferred | 2 |
| Errors | 0 |

### Per-Source Breakdown
| Source | Scanned | Processed | Done | Pending |
|--------|---------|-----------|------|---------|
| file-drop-watcher | 4 | 3 | 2 | 1 |
| gmail-watcher | 4 | 4 | 3 | 1 |
| whatsapp-watcher | 4 | 3 | 2 | 1 |

### Service Health (Gold Tier)
| Service | Status | Last Check | Failures |
|---------|--------|------------|----------|
| Email | Healthy | 14:35:15 | 0 |
| Social Media | Degraded | 14:34:00 | 3 |
| Odoo | Healthy | 14:35:25 | 0 |

### Recent CEO Briefings
| Date | Status | Data Sources | Sections |
|------|--------|--------------|----------|
| 2026-02-24 | Complete | Odoo, Tasks, Social | 6/6 |
```

## Error Handling and Recovery

**Atomic Writes**: All file operations use write-to-temp-then-rename pattern to prevent corruption.

**Stale PID Detection**: On startup, watchers check for stale PID lock files (process dead but file exists). Cleans up and restarts safely.

**Status Markers**: During processing, Needs_Action files marked with `status: processing`. On error, reset to `status: needs_action` for retry.

**Non-Retryable Errors**: PermissionError, SystemExit, KeyboardInterrupt, and authentication failures (HTTP 401) immediately stop retry loop without delay.

**Graceful Degradation**: When an external service is degraded (circuit breaker open), dependent tasks queued for later. Non-dependent tasks continue processing normally.

## Security Model

- **Local-First**: All data stays on disk. No cloud storage.
- **Credentials**: OAuth tokens and API keys stored in `.env` or `.claude/` config, never in vault or git.
- **Approval Gates**: Sensitive/critical actions blocked until human reviews Pending_Approval/ file.
- **Redaction**: All JSONL logs redact sensitive field values (password, token, secret, api_key, credential, auth) with `***REDACTED***`.
- **Audit Trail**: Every action logged with correlation ID for traceability and recovery.
