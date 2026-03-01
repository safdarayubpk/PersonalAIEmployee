# Data Model: Gold Tier

**Date**: 2026-03-01
**Source**: [spec.md](spec.md) Key Entities section

## Entities

### 1. Needs_Action File (Extended)

**Storage**: Markdown file in `{VAULT_PATH}/Needs_Action/`
**Changes from Silver**: Added `correlation_id` field

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| title | string | YES | kebab-case, descriptive |
| created | string | YES | ISO 8601 `YYYY-MM-DDTHH:MM:SS` |
| tier | enum | YES | `bronze\|silver\|gold\|platinum` |
| source | string | YES | One of: `file-drop-watcher`, `gmail-watcher`, `whatsapp-watcher`, `daily-scheduler` |
| priority | enum | YES | `routine\|sensitive\|critical` |
| status | enum | YES | `needs_action\|processing\|done\|error\|retry_pending` |
| correlation_id | string | YES (Gold+) | Format: `corr-YYYYMMDD-HHMMSS-XXXX` |

**New status value**: `retry_pending` — task failed but queued for retry via circuit breaker recovery.

### 2. MCP Server Registry

**Storage**: JSON file at `config/mcp-servers.json`
**Identity**: `name` field (unique)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| name | string | YES | Unique server name (e.g., `fte-email`) |
| domain | string | YES | `email\|social\|erp\|documents` |
| command | string | YES | Python executable path |
| args | array | YES | Script path (e.g., `["src/mcp/email_server.py"]`) |
| tools | array | YES | List of tool definitions |

**Tool definition within registry**:

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| name | string | YES | Tool name (e.g., `email.send`) |
| description | string | YES | Human-readable |
| hitl_level | enum | YES | `routine\|sensitive\|critical` |
| params | object | YES | JSON Schema for input parameters |

### 3. Social Media Post

**Storage**: Markdown file in `{VAULT_PATH}/Plans/` (draft) or `{VAULT_PATH}/Pending_Approval/` (awaiting approval)
**Identity**: Filename: `social-{platform}-{YYYYMMDD-HHMMSS}.md`

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| title | string | YES | Post description |
| created | string | YES | ISO 8601 |
| type | string | YES | `social-media-post` |
| platform | enum | YES | `facebook\|instagram\|twitter\|all` |
| content | string | YES | Post text |
| char_count | integer | YES | Validated against platform limit |
| status | enum | YES | `draft\|pending_approval\|approved\|published\|failed` |
| correlation_id | string | YES | Inherited from triggering task |
| post_id | string | NO | Platform-specific ID (set after publishing) |
| published_at | string | NO | ISO 8601 (set after publishing) |

**Platform character limits**:

| Platform | Max Characters |
|----------|---------------|
| Facebook | 63,206 |
| Instagram | 2,200 |
| Twitter | 280 |

### 4. Odoo Record Proxy

**Not stored in vault** — queried live from Odoo via MCP.

**account.move (Invoices)**:

| Field | Odoo Type | Description |
|-------|-----------|-------------|
| id | Integer | Record ID |
| name | Char | Invoice number (e.g., `INV/2026/001`) |
| partner_id | Many2one | Customer/vendor |
| move_type | Selection | `out_invoice\|out_refund\|in_invoice\|in_refund` |
| state | Selection | `draft\|posted\|cancelled` |
| amount_total | Float | Total including tax |
| amount_residual | Float | Amount still due |
| payment_state | Selection | `not_paid\|partial\|paid\|reversed` |
| invoice_date | Date | Invoice date |
| invoice_date_due | Date | Due date |

**res.partner (Contacts)**:

| Field | Odoo Type | Description |
|-------|-----------|-------------|
| id | Integer | Partner ID |
| name | Char | Name |
| email | Char | Email |
| phone | Char | Phone |
| is_company | Boolean | Company vs individual |
| customer_rank | Integer | >0 = customer |

### 5. Circuit Breaker State

**Storage**: JSON file at `{VAULT_PATH}/Logs/health.json`
**Identity**: `service` field (unique per external service)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| service | string | YES | Service name (e.g., `odoo`, `twitter`, `facebook`, `instagram`, `gmail`) |
| state | enum | YES | `healthy\|degraded\|down` |
| consecutive_failures | integer | YES | 0-N |
| failure_threshold | integer | YES | Default: 3 |
| cooldown_seconds | integer | YES | Default: 300, range: 60-3600 |
| cooldown_expires_at | string | NO | ISO 8601 (set when state=degraded/down) |
| last_success | string | NO | ISO 8601 |
| last_failure | string | NO | ISO 8601 |
| last_error | string | NO | Truncated error message |

**State mapping**:
- `healthy` = circuit breaker CLOSED (normal operation)
- `degraded` = circuit breaker OPEN (calls rejected, in cooldown)
- `down` = circuit breaker OPEN after half-open probe failure

### 6. CEO Briefing

**Storage**: Markdown file in `{VAULT_PATH}/Briefings/`
**Identity**: Filename: `YYYY-MM-DD_Monday_Briefing.md`

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| generated | string | YES | ISO 8601 |
| period | string | YES | `YYYY-MM-DD to YYYY-MM-DD` (7-day range) |
| data_sources | array | YES | List of sources queried (e.g., `["odoo", "vault", "social_logs"]`) |
| incomplete | boolean | YES | `true` if any data source unavailable |
| correlation_id | string | YES | Unique ID for this briefing run |

**Sections (body)**:
1. Executive Summary (2-3 sentences)
2. Revenue & Expenses (from Odoo)
3. Completed Tasks (from Done/ folder)
4. Social Media Activity (from mcp_social.jsonl)
5. Bottlenecks (stale Pending_Approval/ items)
6. Proactive Suggestions (idle subscriptions, missed targets)

### 7. MCP Tool Call Log Entry

**Storage**: JSONL in `{VAULT_PATH}/Logs/mcp_<domain>.jsonl`
**Identity**: None (append-only)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| timestamp | string | YES | ISO 8601 |
| component | string | YES | MCP server name (e.g., `fte-social`) |
| correlation_id | string | YES | Propagated from task |
| tool | string | YES | Tool name (e.g., `social.post_twitter`) |
| action | string | YES | `call\|success\|failure\|dry_run\|hitl_blocked` |
| status | string | YES | `success\|failure\|skipped` |
| params | object | YES | Tool parameters (redacted) |
| result | object | NO | Tool return value |
| detail | string | YES | Human-readable summary |

### 8. Correlation ID

**Not stored separately** — embedded in frontmatter of all files and log entries.

| Attribute | Value |
|-----------|-------|
| Format | `corr-YYYYMMDD-HHMMSS-XXXX` |
| XXXX | 4 random hex characters |
| Generated by | Watcher at file creation time |
| Propagated to | Frontmatter, all JSONL log entries, MCP tool params, Dashboard |
| Legacy handling | Generated retroactively on first processing if missing |

## Relationships

```text
Watcher ──creates──▶ Needs_Action File (with correlation_id)
Scheduler ──creates──▶ Needs_Action File (with correlation_id)
Orchestrator ──reads──▶ Needs_Action File
Orchestrator ──checks──▶ Circuit Breaker State (health.json)
Orchestrator ──routes──▶ MCP Server OR Done/ OR Pending_Approval/
MCP Server ──exposes──▶ Tools (with HITL classification)
MCP Server ──calls──▶ External APIs (Facebook, Instagram, Twitter, Odoo, Gmail)
MCP Server ──reports──▶ Circuit Breaker State (on success/failure)
MCP Server ──logs──▶ MCP Tool Call Log Entry (with correlation_id)
Social MCP ──creates──▶ Social Media Post (draft → approval → published)
Odoo MCP ──queries──▶ Odoo Record Proxy (account.move, res.partner)
CEO Briefing ──reads──▶ Odoo MCP (financial_summary), Done/, Logs/mcp_social.jsonl, Pending_Approval/
CEO Briefing ──creates──▶ Briefings/YYYY-MM-DD_Monday_Briefing.md
Health Monitor ──reads/writes──▶ Circuit Breaker State (health.json)
All Components ──propagate──▶ Correlation ID
```
