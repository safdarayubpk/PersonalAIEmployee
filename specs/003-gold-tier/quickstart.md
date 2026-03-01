# Gold Tier Quickstart Guide

## Prerequisites

1. **Bronze + Silver tiers operational** — all 12 skills working, vault structure intact
2. **Python venv active** with existing deps + `tweepy` installed
3. **Odoo 19 Community** running on Docker (`localhost:8069`) with admin DB created
4. **Social media API credentials** in `.env`:
   - Facebook: `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN`
   - Instagram: `INSTAGRAM_BUSINESS_ID` (uses same Facebook token)
   - Twitter: `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET`
5. **Odoo credentials** in `.env`:
   - `ODOO_HOST=localhost`, `ODOO_PORT=8069`, `ODOO_DB=<your-db>`, `ODOO_USER=admin`, `ODOO_PASSWORD=<your-password>`

## Setup

```bash
# 1. Install new dependency
source .venv/bin/activate
pip install tweepy mcp  # or fastmcp

# 2. Start Odoo (if not running)
cd ~/odoo-docker && docker compose up -d

# 3. Create Briefings folder in vault
python src/setup_vault.py

# 4. Start MCP servers via PM2
pm2 start config/ecosystem.config.js

# 5. Verify MCP servers registered
claude mcp list
```

## Verify Installation

```bash
# Test Odoo connection
python -c "import odoorpc; o=odoorpc.ODOO('localhost',port=8069); o.login('your-db','admin','pw'); print(o.version)"

# Test Twitter auth
python -c "import tweepy; c=tweepy.Client(consumer_key='...'); print('OK')"

# Test MCP email server
# (Claude Code should see fte-email tools)
```

## Daily Usage

1. **Watchers run continuously** (filesystem, Gmail, WhatsApp) — creating `Needs_Action` files
2. **Run orchestrator** — processes tasks, routes to MCP servers or HITL gate
3. **Approve sensitive actions** — move files from `Pending_Approval/` to `Approved/`
4. **CEO Briefing** — auto-generates every Sunday 8 PM (or run `ceo-briefing` skill manually)
5. **Check health** — `Dashboard.md` shows service health status
