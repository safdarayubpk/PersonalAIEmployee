---
id: "0002"
title: "Gold Tier Architecture Plan"
stage: plan
date: 2026-03-01
surface: agent
model: claude-opus-4-6
feature: 003-gold-tier
branch: 003-gold-tier
user: safdarayub
command: /sp.plan
labels: ["gold-tier", "plan", "mcp-servers", "architecture", "odoo", "social-media", "circuit-breaker"]
links:
  spec: specs/003-gold-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/003-gold-tier/plan.md
  - specs/003-gold-tier/research.md
  - specs/003-gold-tier/data-model.md
  - specs/003-gold-tier/quickstart.md
  - specs/003-gold-tier/contracts/mcp-email-tools.md
  - specs/003-gold-tier/contracts/mcp-social-tools.md
  - specs/003-gold-tier/contracts/mcp-odoo-tools.md
  - specs/003-gold-tier/contracts/mcp-documents-tools.md
tests:
  - "Constitution check: all 6 principles PASS"
---

## Prompt

Gold tier - Autonomous Employee: MCP server architecture, social media integration (Facebook/Instagram/Twitter), Odoo ERP via JSON-RPC, error recovery with circuit breakers, CEO Briefing, audit logging with correlation IDs, 4 new skills + 4 MCP servers + 3 skill updates. Feature: 003-gold-tier

## Response snapshot

Created complete Gold tier architecture plan with 8 phases. Phase 0 research resolved 8 decisions (MCP framework, social media APIs, Odoo integration, circuit breaker, correlation IDs). Phase 1 design produced data-model.md (8 entities), 4 MCP tool contracts (15 tools total), and quickstart.md. Architecture: 4 stdio MCP servers (email, social, odoo, documents) registered in Claude Code, circuit breaker per external service, correlation IDs propagated from watchers through all components. Constitution check: all 6 principles PASS.

## Outcome

- Impact: Complete architecture blueprint for Gold tier — ready for /sp.tasks
- Tests: Constitution check all PASS, no violations
- Files: plan.md, research.md, data-model.md, quickstart.md, 4 contract files
- Next prompts: /sp.tasks to generate implementation checklist
- Reflection: MCP stdio transport is the key architecture decision — keeps local-first while giving Claude Code native tool access. Circuit breaker pattern ensures resilience without over-engineering.

## Evaluation notes (flywheel)

- Failure modes observed: Social media research agent denied WebSearch — used knowledge-based reference instead
- Graders run and results (PASS/FAIL): Constitution check PASS (6/6)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Verify MCP SDK compatibility with Claude Code v2.1.x before Phase 2
