# Research: Silver Tier

**Date**: 2026-02-26
**Status**: Complete — all decisions pre-resolved during spec clarification

## Overview

No NEEDS CLARIFICATION items existed in the Technical Context. All technology decisions were established during Bronze tier implementation and confirmed during Silver spec clarification sessions. This document records the key decisions for traceability.

## Decisions

### R-001: Action Execution Pattern

- **Decision**: Direct Python function calls via `importlib` (action-executor)
- **Rationale**: Already implemented and working. No HTTP overhead. Simpler than MCP/FastAPI for local-only execution. Constitution IV explicitly defers MCP/FastAPI to Gold tier.
- **Alternatives considered**:
  - FastMCP server (evaluated via egyptianego17/email-mcp-server) — rejected: adds unnecessary HTTP layer, new dependencies (pydantic, aiosmtplib, FastMCP), contradicts local-first simplicity
  - Direct subprocess calls — rejected: action-executor already handles importlib, exit codes, and HITL gating

### R-002: Priority Vocabulary

- **Decision**: Use constitution-canonical `routine|sensitive|critical` in all frontmatter
- **Rationale**: Constitution defines `Needs_Action` file format with `priority: routine|sensitive|critical`. Using a different vocabulary (low/medium/high) would create cross-tier inconsistency and orchestrator misclassification.
- **Alternatives considered**:
  - Silver adopts `low|medium|high` with orchestrator mapping — rejected: adds translation complexity, risks Bronze/Silver file incompatibility
  - Dual vocabulary support — rejected: unnecessary complexity, single canonical vocabulary is cleaner

### R-003: Gmail API for Sending

- **Decision**: Reuse existing Gmail API OAuth2 credentials for `send_email` action
- **Rationale**: `gmail_poll.py` already authenticates via OAuth2 with `credentials.json` / `token.json`. Extending scopes to include `gmail.send` reuses existing auth flow. No new dependencies needed.
- **Alternatives considered**:
  - SMTP via aiosmtplib — rejected: requires separate credentials, new dependency, different auth flow
  - External email MCP server — rejected: see R-001

### R-004: Risk Keyword Centralization

- **Decision**: Single `config/risk-keywords.json` loaded by all watchers and orchestrator
- **Rationale**: Previously, 3 scripts had independently hardcoded keyword lists with inconsistencies. Centralization ensures SC-001 cross-watcher consistency. Fallback defaults retained in each script for resilience.
- **Alternatives considered**:
  - Per-script keyword lists — rejected: led to inconsistent urgency classification across watchers
  - Database/Redis — rejected: overkill for local-first, single-file JSON is sufficient

### R-005: Scheduler Implementation

- **Decision**: APScheduler `BackgroundScheduler` with `CronTrigger`, in-memory job store
- **Rationale**: Already implemented in `scheduler_daemon.py`. Supports daily, weekly, and cron expressions. `misfire_grace_time` handles missed triggers. No external cron dependency.
- **Alternatives considered**:
  - System crontab — rejected: less portable, harder to manage programmatically, no grace period
  - Celery Beat — rejected: requires Redis/RabbitMQ broker, violates no-cloud-deps constraint

### R-006: Action Stub Strategy

- **Decision**: Stubs return structured dicts matching the action executor's expected format; real implementations deferred to Gold tier where applicable
- **Rationale**: SC-002 tests the action lifecycle (dry-run, HITL, live) across all 6 actions. Stubs need to accept `**kwargs`, return `{"status": "...", ...}`, and log properly — but don't need real external integrations.
- **Alternatives considered**:
  - Skip stubs, only implement email — rejected: SC-002 explicitly names all 6 actions
  - Full implementations — rejected: exceeds Silver scope; social posting, calendar, and report generation are Gold-tier integrations
