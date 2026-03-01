# Implementation Plan: Gold Tier (Autonomous Employee)

**Branch**: `003-gold-tier` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-gold-tier/spec.md`

## Summary

Upgrade the Silver tier Personal AI Employee to a fully autonomous Gold tier system with: (1) MCP server architecture replacing direct importlib calls for external integrations, (2) social media publishing to Facebook/Instagram/Twitter with HITL approval, (3) Odoo 19 ERP integration for accounting data via JSON-RPC, (4) circuit breaker pattern for graceful degradation, (5) weekly CEO Briefing aggregating financial + task + social data, and (6) correlation-ID-based end-to-end audit logging. All new functionality implemented as Claude Code Agent Skills. Zero breaking changes to Bronze/Silver tiers.

## Technical Context

**Language/Version**: Python 3.13+ (existing venv)
**Primary Dependencies**:
- Existing: watchdog, google-api-python-client, google-auth-oauthlib, playwright, apscheduler, fastapi, uvicorn, odoorpc
- New: `mcp` (Python MCP SDK or `fastmcp`), `tweepy` (Twitter/X API)
- Already available: `requests` (for Facebook/Instagram Graph API)
**Storage**: Filesystem — Obsidian vault at `VAULT_PATH`, JSONL logs, JSON config files, `Logs/health.json` (circuit breaker state)
**Testing**: Manual test plan (markdown checklists) + unit tests for circuit breaker and MCP tool validation
**Target Platform**: Linux (Ubuntu), single-user local machine
**Project Type**: Single project — MCP servers + Claude Code skills
**Performance Goals**: MCP tool calls <5s, Odoo queries <10s, CEO Briefing generation <60s
**Constraints**: No cloud deps (C-004), atomic writes (C-002), dry-run default (C-003), backward compat (C-010), stdio MCP transport (C-008)
**Scale/Scope**: Single user, 4 MCP servers, 3 social platforms, 1 Odoo instance, weekly briefings

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Local-First | PASS | MCP servers use stdio transport (no network). Odoo runs on localhost Docker. Social media API calls only in live mode after HITL approval. No user data transmitted without approval. |
| II. HITL Safety | PASS | Social media posts = sensitive (HITL gate). Odoo writes = critical (HITL + confirmation log). Odoo reads = routine (auto-execute). MCP servers inherit HITL classification per tool. |
| III. Proactive Autonomy | PASS | CEO Briefing triggers via scheduler autonomously. Watchers + MCP servers + orchestrator operate without prompting. Ralph Wiggum retries MCP failures. |
| IV. Modularity | PASS | Incremental on Silver — zero breaking changes (FR-014). MCP servers are additive (Silver action-executor still works). Each MCP server is independent. |
| V. Cost-Efficiency | PASS | Automated social posting, financial reporting, and task triage replace manual work. CEO Briefing replaces weekly manual audit. |
| VI. Error Handling | PASS | Circuit breaker (FR-006) prevents cascading failures. Health monitoring (FR-007). Correlation IDs (FR-010) enable tracing. Graceful degradation (FR-012). |

**Gate result**: ALL PASS. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/003-gold-tier/
├── plan.md              # This file
├── spec.md              # Feature specification (6 user stories)
├── research.md          # Phase 0 output (API research decisions)
├── data-model.md        # Phase 1 output (entities + schemas)
├── quickstart.md        # Phase 1 output (setup + run instructions)
├── contracts/           # Phase 1 output (MCP tool schemas)
│   ├── mcp-email-tools.md
│   ├── mcp-social-tools.md
│   ├── mcp-odoo-tools.md
│   └── mcp-documents-tools.md
└── tasks.md             # Phase 2 output (/sp.tasks command)
```

### Source Code (repository root)

```text
# Existing Bronze/Silver infrastructure (unchanged)
src/
├── setup_vault.py           # Vault initialization (Bronze)
├── file_drop_watcher.py     # Filesystem watcher (Bronze)
├── vault_helpers.py         # Shared vault utilities (Bronze/Silver)
├── circuit_breaker.py       # NEW — Circuit breaker state machine
├── correlation.py           # NEW — Correlation ID generation + propagation
├── actions/                 # Silver action modules (unchanged)
│   ├── __init__.py
│   ├── email.py
│   ├── social.py
│   ├── calendar_actions.py
│   └── documents.py
└── mcp/                     # NEW — MCP server implementations
    ├── __init__.py
    ├── base_server.py        # Shared MCP server utilities (HITL, logging, dry-run)
    ├── email_server.py       # Email MCP server (wraps src/actions/email.py)
    ├── social_server.py      # Social media MCP server (Facebook, Instagram, Twitter)
    ├── odoo_server.py        # Odoo ERP MCP server (JSON-RPC via odoorpc)
    └── documents_server.py   # Documents MCP server (reports, briefings)

# Skills (Claude Code skill bundles)
.claude/skills/
├── vault-interact/                    # Bronze (unchanged)
├── process-needs-action/              # Bronze (unchanged)
├── check-and-process-needs-action/    # Bronze (unchanged, add correlation_id support)
├── skill-creator/                     # Bronze (unchanged)
├── gmail-watcher/                     # Silver (update: add correlation_id to files)
├── whatsapp-watcher/                  # Silver (update: add correlation_id to files)
├── action-executor/                   # Silver (update: add MCP dispatch mode)
├── ralph-retry/                       # Silver (unchanged)
├── daily-scheduler/                   # Silver (unchanged, add CEO briefing schedule)
├── central-orchestrator/              # Silver (update: MCP routing, circuit breaker, correlation_id)
├── social-media-poster/               # NEW — Draft + publish + weekly summary
├── odoo-connector/                    # NEW — ERP read/write via MCP
├── ceo-briefing/                      # NEW — Weekly Monday Morning Briefing
└── health-monitor/                    # NEW — Circuit breaker + service health

# Configuration
config/
├── ecosystem.config.js   # PM2 config (extend for MCP servers)
├── risk-keywords.json     # Shared risk keywords (unchanged)
├── actions.json           # Action registry (unchanged, backward compat)
├── schedules.json         # Scheduler config (add CEO briefing entry)
├── mcp-servers.json       # NEW — MCP server registry (name, domain, tools, HITL per tool)
└── social-platforms.json  # NEW — Platform configs (char limits, API versions, rate limits)

# MCP Registration (Claude Code)
.claude/settings.json      # UPDATE — Register 4 MCP servers

# Documentation
docs/                      # NEW
├── architecture.md         # System diagrams and component descriptions
├── lessons-learned.md      # Development insights from all 3 tiers
└── demo-script.md          # 5-10 minute demo walkthrough

# Tests
tests/
├── manual/
│   ├── bronze-tier-test-plan.md   # exists
│   ├── silver-tier-test-plan.md   # exists
│   └── gold-tier-test-plan.md     # NEW
└── unit/
    ├── test_ralph_retry.py         # exists
    ├── test_action_executor.py     # exists
    ├── test_circuit_breaker.py     # NEW
    ├── test_correlation.py         # NEW
    └── test_content_validator.py   # NEW
```

**Structure Decision**: Single project with MCP servers as Python scripts in `src/mcp/`. Each MCP server is a standalone stdio process registered in Claude Code settings. Skills orchestrate MCP tool calls. No web framework needed for MCP (stdio transport). PM2 manages MCP server processes.

## Architecture

### Component Interaction Flow (Gold Tier)

```text
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ file_drop_watcher│  │   gmail_poll     │  │whatsapp_monitor  │  │scheduler_daemon  │
│   (Bronze)       │  │   (Silver)       │  │   (Silver)       │  │   (Silver)       │
│  +correlation_id │  │  +correlation_id │  │  +correlation_id │  │  +correlation_id │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │                     │
         ▼                     ▼                     ▼                     ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                    Needs_Action/ (vault folder)                         │
    │  Each file: YAML frontmatter + correlation_id + body                   │
    └────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                    central-orchestrator (UPDATED)                       │
    │  1. Scan Needs_Action/*.md (skip .moved, skip status:processing)       │
    │  2. Queue by priority (critical → sensitive → routine)                 │
    │  3. For each file in batch:                                            │
    │     a. Mark status:processing, propagate correlation_id                │
    │     b. Assess risk (keyword scan)                                      │
    │     c. Check circuit breaker for target service                        │
    │     d. Route: MCP tool call OR HITL gate OR Done/                     │
    │  4. Update Dashboard.md + health status                                │
    └──────────┬──────────────┬──────────────┬──────────────┬───────────────┘
               │              │              │              │
               ▼              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  MCP Email   │ │  MCP Social  │ │  MCP Odoo    │ │ MCP Documents│
    │  Server      │ │  Server      │ │  Server      │ │ Server       │
    │  (stdio)     │ │  (stdio)     │ │  (stdio)     │ │ (stdio)      │
    ├──────────────┤ ├──────────────┤ ├──────────────┤ ├──────────────┤
    │email.send    │ │social.post_fb│ │odoo.list_inv │ │docs.report   │
    │email.draft   │ │social.post_ig│ │odoo.create_iv│ │docs.briefing │
    │email.search  │ │social.post_tw│ │odoo.payment  │ │              │
    │              │ │social.summary│ │odoo.fin_summ │ │              │
    │              │ │              │ │odoo.partners │ │              │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                │                │
           ▼                ▼                ▼                ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    Circuit Breaker Layer                        │
    │  Per-service: failure count → open/closed/half-open state      │
    │  Health file: Logs/health.json                                  │
    │  Cooldown: 300s default, probe on half-open                    │
    └──────────┬──────────────────────────────────────────────────────┘
               │
               ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    External Services                            │
    │  Gmail API │ Facebook API │ Instagram API │ Twitter API │ Odoo │
    └─────────────────────────────────────────────────────────────────┘
```

### MCP Server Architecture

```text
Each MCP server is a standalone Python process using stdio transport:

Claude Code ──stdio──▶ src/mcp/email_server.py
Claude Code ──stdio──▶ src/mcp/social_server.py
Claude Code ──stdio──▶ src/mcp/odoo_server.py
Claude Code ──stdio──▶ src/mcp/documents_server.py

Registration in .claude/settings.json:
{
  "mcpServers": {
    "fte-email": {
      "command": "python",
      "args": ["src/mcp/email_server.py"],
      "env": {"VAULT_PATH": "...", "DRY_RUN": "true"}
    },
    "fte-social": { ... },
    "fte-odoo": { ... },
    "fte-documents": { ... }
  }
}

Each server:
  ├── Exposes tools via @server.tool() decorator
  ├── Defaults to dry-run (reads DRY_RUN env var)
  ├── Respects HITL classification per tool
  ├── Logs to domain-specific JSONL (Logs/mcp_<domain>.jsonl)
  ├── Propagates correlation_id in all log entries
  └── Reports errors to circuit breaker via health.json
```

### HITL Classification per MCP Tool

```text
ROUTINE (auto-execute, log only):
  email.draft         → Draft email locally, no send
  email.search        → Search inbox (read-only)
  odoo.list_invoices  → Read unpaid invoices
  odoo.financial_summary → Aggregate GL entries
  odoo.list_partners  → Read contacts
  docs.generate_report → Generate markdown report

SENSITIVE (HITL gate required):
  email.send          → Send email via Gmail API
  social.post_facebook → Publish to Facebook Page
  social.post_instagram → Publish to Instagram
  social.post_twitter  → Publish tweet

CRITICAL (HITL gate + confirmation log):
  odoo.create_invoice → Create invoice in Odoo
  odoo.register_payment → Register payment in Odoo
```

### CEO Briefing Data Flow

```text
ceo-briefing skill (triggered by scheduler or on-demand)
  │
  ├── 1. Query Odoo MCP: odoo.financial_summary (routine, auto-execute)
  │     └── Returns: revenue, expenses, receivables, payables for period
  │
  ├── 2. Read Done/ folder: count files by source, list top tasks
  │     └── Returns: total completed, by-source breakdown, task list
  │
  ├── 3. Read Logs/mcp_social.jsonl: count posts by platform
  │     └── Returns: posts per platform, content snippets
  │
  ├── 4. Read Pending_Approval/: find stale items (>24h)
  │     └── Returns: bottleneck list with wait times
  │
  ├── 5. Read Business_Goals.md: compare targets vs actuals
  │     └── Returns: target vs actual, trend direction
  │
  └── 6. Generate Briefings/YYYY-MM-DD_Monday_Briefing.md
        └── Sections: Executive Summary, Revenue, Tasks, Social, Bottlenecks, Suggestions
```

### Circuit Breaker State Machine

```text
CLOSED (healthy)
  │
  ├── Success → reset failure count, stay CLOSED
  │
  └── Failure → increment failure count
        │
        ├── count < threshold (3) → stay CLOSED
        │
        └── count >= threshold → transition to OPEN
              │
              ▼
OPEN (degraded)
  │
  ├── All calls immediately rejected (no API call made)
  ├── Log "circuit open for <service>"
  ├── Update health.json: state=degraded
  │
  └── After cooldown (300s) → transition to HALF-OPEN
              │
              ▼
HALF-OPEN (probing)
  │
  ├── Allow ONE probe request through
  │
  ├── Probe succeeds → transition to CLOSED, reset count
  │     └── Update health.json: state=healthy
  │
  └── Probe fails → transition to OPEN, restart cooldown
        └── Update health.json: state=down
```

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| MCP framework | `fastmcp` / `mcp` Python SDK, stdio transport | Claude Code native support; local-first; no HTTP ports |
| Social media — Facebook | `requests` + Graph API v19.0 | Simple REST; no heavy SDK needed |
| Social media — Instagram | `requests` + Graph API (two-step) | Same auth as Facebook; requires container→publish pattern |
| Social media — Twitter | `tweepy` + API v2, OAuth 1.0a | De facto Python library; built-in rate limit handling |
| Odoo integration | `odoorpc` (v0.10.1, already installed) | High-level ORM access; JSON-RPC protocol; session management |
| Circuit breaker | Custom `src/circuit_breaker.py` | ~50 lines; no external dependency for simple state machine |
| Correlation IDs | `corr-YYYYMMDD-HHMMSS-XXXX` in frontmatter | Readable, sortable, assigned at watcher level |
| CEO Briefing data | MCP tools + vault file reads + log parsing | Each source already produces structured output |
| Dashboard serialization | Single-writer function in orchestrator | Prevents concurrent write corruption (FR-017) |
| Backward compat | MCP servers additive; Silver action-executor unchanged | config/actions.json still works; orchestrator routes to MCP OR importlib |

## Phases

### Phase 1: Foundation & Infrastructure (estimated: 3-4 hours)

- Create `src/circuit_breaker.py` — state machine (closed/open/half-open)
- Create `src/correlation.py` — ID generation and propagation helpers
- Create `src/mcp/base_server.py` — shared MCP server utilities (HITL check, logging, dry-run wrapper)
- Create `config/mcp-servers.json` — MCP server registry
- Create `config/social-platforms.json` — platform character limits and API config
- Create `Briefings/` folder in vault via `setup_vault.py` update
- Update `src/vault_helpers.py` — add `generate_correlation_id()` function
- Write unit tests: `tests/unit/test_circuit_breaker.py`, `tests/unit/test_correlation.py`

### Phase 2: MCP Email Server (estimated: 2-3 hours)

- Create `src/mcp/email_server.py` — wraps existing `src/actions/email.py`
- Expose tools: `email.send` (sensitive), `email.draft` (routine), `email.search` (routine)
- Register in `.claude/settings.json` as `fte-email`
- Add to PM2 ecosystem config
- Log all calls to `Logs/mcp_email.jsonl` with correlation IDs
- Test: dry-run tool call, HITL gate for send, live send with approval

### Phase 3: MCP Social Media Server (estimated: 4-5 hours)

- Create `src/mcp/social_server.py` — Facebook, Instagram, Twitter integration
- Implement content validator (character limits per platform)
- Expose tools:
  - `social.post_facebook` (sensitive) — POST to Page feed
  - `social.post_instagram` (sensitive) — two-step container→publish
  - `social.post_twitter` (sensitive) — tweepy create_tweet
  - `social.weekly_summary` (routine) — parse logs, generate summary
- Register in `.claude/settings.json` as `fte-social`
- Create `social-media-poster` skill (SKILL.md + references)
- Test: dry-run posts, HITL approval flow, live post to each platform
- Write `tests/unit/test_content_validator.py`

### Phase 4: MCP Odoo Server (estimated: 3-4 hours)

- Create `src/mcp/odoo_server.py` — OdooRPC-based JSON-RPC bridge
- Expose tools:
  - `odoo.list_invoices` (routine) — search_read account.move
  - `odoo.create_invoice` (critical) — create account.move + HITL + confirmation log
  - `odoo.register_payment` (critical) — update payment state + HITL
  - `odoo.financial_summary` (routine) — aggregate account.move.line
  - `odoo.list_partners` (routine) — search_read res.partner
- Register in `.claude/settings.json` as `fte-odoo`
- Create `odoo-connector` skill (SKILL.md + references)
- Test: list invoices from Odoo, create invoice with approval, financial summary

### Phase 5: Error Recovery & Health Monitoring (estimated: 2-3 hours)

- Integrate circuit breaker into all MCP servers (wrap external API calls)
- Create `Logs/health.json` — service health state file
- Create `health-monitor` skill (SKILL.md)
- Update `central-orchestrator` — check circuit breaker before routing to MCP, skip degraded services
- Update `Dashboard.md` template — add health status section
- Test: stop Odoo container → verify circuit breaker activates, restart → verify recovery

### Phase 6: CEO Briefing (estimated: 3-4 hours)

- Create `src/mcp/documents_server.py` — report and briefing generation
- Expose tools:
  - `docs.generate_report` (routine) — generic markdown report
  - `docs.generate_briefing` (routine) — CEO Briefing with all 6 sections
- Create `ceo-briefing` skill (SKILL.md)
- Add weekly schedule entry to `config/schedules.json` (Sunday 8 PM)
- Create `Briefings/` vault folder (via setup_vault.py)
- Test: trigger briefing with sample Odoo data + completed tasks + social logs

### Phase 7: Orchestrator Updates & Integration (estimated: 2-3 hours)

- Update `central-orchestrator` — MCP routing mode (alongside importlib)
- Add correlation_id propagation to all watchers (gmail, whatsapp, filesystem, scheduler)
- Update action-executor — add MCP dispatch mode
- Wire circuit breaker health checks into orchestrator routing decisions
- Test: end-to-end pipeline with MCP servers, correlation ID tracing

### Phase 8: Documentation & Testing (estimated: 3-4 hours)

- Create `docs/architecture.md` — system diagrams, component descriptions
- Create `docs/lessons-learned.md` — insights from Bronze/Silver/Gold
- Create `docs/demo-script.md` — 5-10 minute demo walkthrough
- Update `README.md` — Gold tier features, setup instructions
- Create `tests/manual/gold-tier-test-plan.md` — SC-001 through SC-010
- Run full regression: Bronze test plan, Silver test plan, Gold test plan
- Run 30-minute stability test with all MCP servers active

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| MCP SDK compatibility with Claude Code version | Servers fail to register | Test with `claude mcp list` early in Phase 1; fallback to raw stdio JSON-RPC if SDK incompatible |
| Odoo Docker container instability | Financial queries fail | Circuit breaker auto-degrades; CEO briefing generates partial report with `incomplete: true` |
| Social media API credential expiry | Posts fail silently | Circuit breaker detects 401 as non-retryable; creates Needs_Action file for re-authentication |
| Twitter rate limit (450/15min) | Burst posting blocked | Rate limit handler in social MCP server; tweepy `wait_on_rate_limit=True` auto-handles |
| Instagram two-step publish failure | Container created but not published | Status polling before publish step; cleanup orphaned containers |
| Concurrent Dashboard.md writes | File corruption | Single-writer function (FR-017); MCP servers write to domain logs only |
| Correlation ID missing on legacy files | Broken audit chain | Retroactive generation on first processing (edge case in spec) |
| MCP server crashes during orchestrator run | Task stuck in processing | Ralph Wiggum retry picks up; circuit breaker marks service degraded |

## Complexity Tracking

No constitution violations. No complexity justifications needed.
