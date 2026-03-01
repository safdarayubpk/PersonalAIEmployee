# Personal AI Employee

A local-first autonomous AI agent that monitors multiple sources (filesystem, Gmail, WhatsApp), processes tasks through an Obsidian vault pipeline, and executes actions via MCP servers with human-in-the-loop safety gates. Built for the 2026 Personal AI Employee Hackathon.

## Tiers

### Bronze — File Watcher + Vault Processing
- Filesystem watcher (Watchdog) monitors `~/Desktop/DropForAI`
- Creates metadata `.md` files in `Needs_Action/` with YAML frontmatter
- 3 Claude Code skills: `vault-interact`, `process-needs-action`, `check-and-process-needs-action`
- Routes by risk: routine → `Done/`, sensitive/critical → `Pending_Approval/`

### Silver — Multi-Source Orchestration
- 4 watchers: filesystem, Gmail (OAuth2), WhatsApp (Playwright), daily scheduler (APScheduler)
- Central orchestrator: priority queue, batch processing, HITL routing
- Action executor: importlib-based function dispatch with approval gates
- Ralph Wiggum retry loop: exponential backoff for fault tolerance
- PM2 process management

### Gold — MCP Servers + External Integrations
- 4 MCP servers via FastMCP (stdio transport):
  - `fte-email` — Gmail draft/send/search (sensitive HITL)
  - `fte-social` — Facebook/Instagram/Twitter posting (sensitive HITL)
  - `fte-odoo` — Odoo 19 ERP invoices/payments/financials (critical HITL)
  - `fte-documents` — Reports and CEO Briefing generation
- Circuit breaker pattern: per-service state machine (3 failures → 300s cooldown)
- Correlation IDs: `corr-YYYYMMDD-HHMMSS-XXXX` from watcher through execution
- CEO Briefing: weekly aggregation from Odoo + tasks + social + bottlenecks
- Health monitoring: `Logs/health.json` with real-time service states

## Prerequisites

- Python 3.13+ with venv
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- Obsidian v1.11.x+ (optional, for vault viewing)

```bash
pip install watchdog pyyaml apscheduler mcp tweepy
pip install google-api-python-client google-auth-oauthlib  # Gmail
pip install playwright && playwright install chromium       # WhatsApp
pip install odoorpc                                        # Odoo ERP
```

## Quick Start

```bash
# 1. Initialize vault
python src/setup_vault.py

# 2. Start file watcher
python src/file_drop_watcher.py

# 3. Drop a file and process
cp document.pdf ~/Desktop/DropForAI/
claude "check and process needs action"

# 4. Start Gmail watcher (requires credentials.json)
python .claude/skills/gmail-watcher/scripts/gmail_poll.py

# 5. Start scheduler daemon
python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py

# 6. Run central orchestrator
python .claude/skills/central-orchestrator/scripts/orchestrator.py

# 7. Generate CEO briefing
claude "generate CEO briefing"
```

## MCP Servers

Registered in `.claude/settings.json`. All default to `DRY_RUN=true`.

| Server | Tools | HITL Level |
|--------|-------|------------|
| fte-email | email.draft, email.send, email.search | routine/sensitive |
| fte-social | social.post_facebook, social.post_instagram, social.post_twitter, social.weekly_summary | sensitive/routine |
| fte-odoo | odoo.list_invoices, odoo.create_invoice, odoo.register_payment, odoo.financial_summary, odoo.list_partners | routine/critical |
| fte-documents | docs.generate_report, docs.generate_briefing | routine |

## Project Structure

```
fte/
├── src/
│   ├── vault_helpers.py           # Shared utilities
│   ├── setup_vault.py             # Vault initialization
│   ├── file_drop_watcher.py       # Filesystem watcher
│   ├── correlation.py             # Correlation ID generation
│   ├── circuit_breaker.py         # Circuit breaker state machine
│   └── mcp/
│       ├── base_server.py         # Shared MCP server utilities
│       ├── email_server.py        # Email MCP server
│       ├── social_server.py       # Social media MCP server
│       ├── odoo_server.py         # Odoo ERP MCP server
│       └── documents_server.py    # Documents/Briefing MCP server
├── config/
│   ├── mcp-servers.json           # MCP server registry
│   ├── social-platforms.json      # Platform character limits
│   ├── schedules.json             # Scheduled task definitions
│   ├── actions.json               # Action registry
│   └── ecosystem.config.js        # PM2 configuration
├── .claude/
│   ├── settings.json              # MCP server registration
│   └── skills/                    # 12 Claude Code skills
│       ├── vault-interact/
│       ├── process-needs-action/
│       ├── check-and-process-needs-action/
│       ├── central-orchestrator/
│       ├── action-executor/
│       ├── gmail-watcher/
│       ├── whatsapp-watcher/
│       ├── daily-scheduler/
│       ├── ralph-retry/
│       ├── social-media-poster/
│       ├── odoo-connector/
│       ├── ceo-briefing/
│       └── health-monitor/
├── docs/
│   ├── architecture.md            # System architecture
│   ├── lessons-learned.md         # Development insights
│   └── demo-script.md             # 5-10 min demo walkthrough
├── tests/
│   ├── unit/                      # Unit tests
│   └── manual/                    # Manual test plans
└── specs/                         # Feature specifications
```

## Configuration

| Setting | Default | Override |
|---------|---------|----------|
| Vault path | `/home/safdarayub/Documents/AI_Employee_Vault` | `VAULT_PATH` env |
| Drop folder | `~/Desktop/DropForAI` | `DROP_FOLDER` env |
| Dry-run mode | `true` | `DRY_RUN` env |
| Odoo host | `localhost:8069` | `ODOO_HOST`, `ODOO_PORT` env |

## External Service Setup

- **Gmail**: Create OAuth2 credentials in Google Cloud Console, save `credentials.json` in project root
- **WhatsApp**: First run requires QR code scan in browser
- **Facebook/Instagram**: Page Access Token via Meta Developer Portal
- **Twitter/X**: API keys via Twitter Developer Portal (OAuth 1.0a)
- **Odoo**: Self-hosted Odoo 19 Community, set `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD` env vars

## Documentation

- [Architecture](docs/architecture.md) — System diagrams and component descriptions
- [Lessons Learned](docs/lessons-learned.md) — Development insights across tiers
- [Demo Script](docs/demo-script.md) — 5-10 minute demo walkthrough
- [Gold Tier Test Plan](tests/manual/gold-tier-test-plan.md) — Manual test checklists
