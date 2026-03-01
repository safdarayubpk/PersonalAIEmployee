# Research: Gold Tier

**Date**: 2026-03-01
**Status**: Complete — all decisions resolved via research

## Overview

Gold tier introduces 4 major integration domains: MCP servers, social media APIs, Odoo ERP, and resilience patterns. Each required research to resolve technology choices and API patterns.

## Decisions

### R-001: MCP Server Framework

- **Decision**: Use `fastmcp` (Python) with stdio transport for all MCP servers
- **Rationale**: Claude Code natively supports MCP via stdio transport. The `mcp` Python SDK (or `fastmcp` wrapper) provides a decorator-based tool definition pattern matching Claude Code's expectations. Stdio transport keeps everything local-first (no HTTP ports), consistent with constitution I.
- **Alternatives considered**:
  - FastAPI HTTP servers — rejected: adds HTTP layer, port management, CORS; Claude Code prefers stdio for local servers
  - Node.js MCP servers — rejected: project is Python-based; adding Node would fragment the stack
  - Streamable HTTP transport — rejected: designed for remote servers; our servers are local

**Key patterns**:
- Tool definition: `@server.tool()` decorator with typed parameters and docstrings
- Registration: Add server to `.claude/settings.json` or project-level MCP config
- Transport: stdio (stdin/stdout JSON-RPC 2.0)
- Health: Server responds to `tools/list` for discovery

### R-002: Social Media — Facebook Pages API

- **Decision**: Use `requests` library with Graph API v19.0, Page Access Token auth
- **Rationale**: No dedicated Python SDK needed; REST API is simple enough for direct `requests` calls. Page Access Token is obtained once from Meta Developer Portal.
- **Alternatives considered**:
  - facebook-sdk Python package — rejected: outdated, low maintenance
  - Meta Business SDK — rejected: heavy, designed for ad management

**Key details**:
- Endpoint: `POST https://graph.facebook.com/v19.0/{page_id}/feed`
- Auth: Page Access Token (long-lived, obtained via OAuth 2.0)
- Permissions: `pages_manage_posts`, `pages_read_engagement`
- Rate limit: 200 calls/hour per page
- Character limit: 63,206 characters
- Error handling: HTTP status codes (429=rate limit, 401=auth, 400=validation)

### R-003: Social Media — Instagram Graph API

- **Decision**: Use `requests` with two-step media container flow
- **Rationale**: Instagram Graph API requires Facebook Page linkage and a create→publish pattern. No shortcut available.
- **Alternatives considered**:
  - instagrapi (unofficial) — rejected: violates Instagram TOS, uses private API
  - Meta Business SDK — rejected: same as R-002

**Key details**:
- Step 1: `POST https://graph.instagram.com/v19.0/{ig_user_id}/media` (create container)
- Step 2: `POST https://graph.instagram.com/v19.0/{ig_user_id}/media_publish` (publish)
- Auth: Same Page Access Token as Facebook
- Permissions: `instagram_basic`, `instagram_content_publishing`
- Rate limit: 200 calls/hour + 25 posts/day account limit
- Caption limit: 2,200 characters
- Image: JPG/PNG, max 8MB

### R-004: Social Media — Twitter/X API v2

- **Decision**: Use `tweepy` library with OAuth 1.0a User Context
- **Rationale**: Tweepy is the de facto Python library for Twitter, handles OAuth and rate limits built-in. `wait_on_rate_limit=True` auto-handles 429 responses.
- **Alternatives considered**:
  - Raw requests with OAuth — rejected: OAuth 1.0a signing is complex; tweepy handles it
  - python-twitter — rejected: less maintained than tweepy

**Key details**:
- Endpoint: `POST /2/tweets` (via `client.create_tweet()`)
- Auth: OAuth 1.0a (API Key + Secret + Access Token + Secret)
- Rate limit: 450 posts/15 minutes
- Character limit: 280 characters
- Key errors: 429 (TooManyRequests), 401 (Unauthorized), 403 (Forbidden)

### R-005: Odoo Integration via OdooRPC

- **Decision**: Use `odoorpc` Python package (already installed, v0.10.1) with JSON-RPC protocol
- **Rationale**: OdooRPC provides high-level ORM-like access to Odoo models via JSON-RPC. Already installed in venv. Abstracts authentication, model access, and session management.
- **Alternatives considered**:
  - Raw JSON-RPC via requests — rejected: OdooRPC already abstracts this cleanly
  - XML-RPC — rejected: JSON-RPC is the modern Odoo protocol
  - Odoo MCP server (third-party) — rejected: would add external dependency; we build our own

**Key models and operations**:
- `account.move` (invoices): search_read for unpaid, create for new invoices
- `account.move.line` (GL entries): aggregate for financial summaries (debit/credit by account_type)
- `res.partner` (contacts): search_read for customers/vendors
- Error types: `odoorpc.error.RPCError` (server errors), `odoorpc.error.InternalError` (client errors), connection errors

### R-006: Circuit Breaker Pattern

- **Decision**: Custom lightweight implementation in `src/circuit_breaker.py` using state machine (closed→open→half-open)
- **Rationale**: No external dependency needed. The pattern is simple: count consecutive failures, open circuit after threshold, probe after cooldown.
- **Alternatives considered**:
  - pybreaker library — rejected: adds dependency for ~50 lines of logic
  - tenacity with custom retry — rejected: tenacity handles retries but not circuit breaking per se

**Key parameters**:
- Failure threshold: 3 consecutive failures
- Cooldown: 300 seconds (configurable 60-3600)
- States: closed (healthy), open (degraded/down), half-open (probing)
- Health file: `Logs/health.json` updated on every state change

### R-007: Correlation ID Strategy

- **Decision**: Generate at watcher level (first touch), propagate via frontmatter field `correlation_id`
- **Rationale**: Watchers are the entry point for all tasks. Assigning correlation ID at creation ensures every downstream component can trace back to the source event.
- **Alternatives considered**:
  - Orchestrator assigns ID — rejected: loses watcher-level tracing
  - UUID format — rejected: `corr-YYYYMMDD-HHMMSS-XXXX` is more readable and sortable

**Format**: `corr-YYYYMMDD-HHMMSS-XXXX` (XXXX = 4 random hex chars)
**Propagation**: frontmatter → orchestrator log → MCP tool params → action log → dashboard

### R-008: CEO Briefing Data Aggregation

- **Decision**: Briefing skill queries Odoo MCP for financial data, reads `Done/` folder for task stats, reads `Logs/mcp_social.jsonl` for social activity, reads `Pending_Approval/` for bottlenecks
- **Rationale**: Each data source is already producing structured output. The briefing aggregates rather than re-computes.
- **Alternatives considered**:
  - Briefing queries Odoo directly (not via MCP) — rejected: would bypass HITL classification and logging
  - Briefing reads raw vault files only (no Odoo) — rejected: financial data from Odoo is the key Gold tier differentiator
