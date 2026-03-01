# Tasks: Gold Tier (Autonomous Employee)

**Input**: Design documents from `/specs/003-gold-tier/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/
**Branch**: `003-gold-tier`
**Date**: 2026-03-01

**Tests**: Unit tests included for circuit breaker, correlation IDs, and content validator as specified in plan.md.

**Organization**: Tasks grouped by user story (P1-P6) for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create project structure, config files, and shared utilities that all user stories depend on

- [X] T001 Create MCP server directory structure: `src/mcp/__init__.py`
- [X] T002 [P] Create `config/mcp-servers.json` — MCP server registry with 4 server entries (fte-email, fte-social, fte-odoo, fte-documents) per data-model.md Entity 2
- [X] T003 [P] Create `config/social-platforms.json` — platform character limits and API config (Facebook: 63206, Instagram: 2200, Twitter: 280) per data-model.md Entity 3
- [X] T004 [P] Update `src/setup_vault.py` — add `Briefings/` folder creation to vault initialization
- [X] T005 [P] Create `docs/` directory structure: `docs/architecture.md`, `docs/lessons-learned.md`, `docs/demo-script.md` (placeholder files)

**Checkpoint**: Project structure ready — all directories and config files exist

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Create `src/correlation.py` — correlation ID generation (`corr-YYYYMMDD-HHMMSS-XXXX` format) and propagation helpers per data-model.md Entity 8
- [X] T007 [P] Create `src/circuit_breaker.py` — state machine (closed/open/half-open) with failure threshold (3), cooldown (300s), health.json persistence per data-model.md Entity 5
- [X] T008 [P] Create `tests/unit/test_correlation.py` — test ID format validation, uniqueness, generation function
- [X] T009 [P] Create `tests/unit/test_circuit_breaker.py` — test state transitions (closed→open after 3 failures, open→half-open after cooldown, half-open→closed on success, half-open→open on failure), health.json writes
- [X] T010 Create `src/mcp/base_server.py` — shared MCP server utilities: HITL classification check, dry-run wrapper, JSONL logging with correlation ID, error response formatting. Uses `fastmcp` or `mcp` SDK with stdio transport per research R-001
- [X] T011 Register 4 MCP servers in `.claude/settings.json` under `mcpServers` key: fte-email, fte-social, fte-odoo, fte-documents with `command: "python"` and args pointing to `src/mcp/<server>.py`, env including `VAULT_PATH` and `DRY_RUN=true`
- [X] T012 Update `src/vault_helpers.py` — add `generate_correlation_id()` function that imports from `src/correlation.py`

**Checkpoint**: Foundation ready — circuit breaker, correlation IDs, MCP base server, and registration complete. User story implementation can begin.

---

## Phase 3: User Story 1 — MCP Server Architecture (Priority: P1) MVP

**Goal**: Replace importlib-based action executor with MCP servers that Claude Code invokes as first-class tools. Start with email server as proof of architecture.

**Independent Test**: Start email MCP server. Call `email.draft` via Claude Code — verify structured JSON response and JSONL log entry. Call `email.send` — verify HITL gate creates `Pending_Approval` file.

### Implementation for User Story 1

- [X] T013 [US1] Create `src/mcp/email_server.py` — MCP email server wrapping `src/actions/email.py`. Expose 3 tools per contract `mcp-email-tools.md`: `email.send` (sensitive), `email.draft` (routine), `email.search` (routine). Use base_server.py utilities for HITL check, dry-run, and logging
- [X] T014 [US1] Implement `email.draft` tool in `src/mcp/email_server.py` — create draft markdown file in `{VAULT_PATH}/Plans/email-draft-<timestamp>.md`, log to `Logs/mcp_email.jsonl`, return structured JSON response
- [X] T015 [US1] Implement `email.send` tool in `src/mcp/email_server.py` — check HITL classification (sensitive), in dry-run return dry_run status, in live mode without approval create `Pending_Approval` file, in live mode with approval call Gmail API via `src/actions/email.py`
- [X] T016 [US1] Implement `email.search` tool in `src/mcp/email_server.py` — query Gmail API for emails matching criteria, return structured results, log to `Logs/mcp_email.jsonl`
- [X] T017 [US1] Verify MCP email server end-to-end: run `claude mcp list` to confirm fte-email registered, invoke `email.draft` tool, check JSONL log entry contains correlation_id and all required fields per data-model.md Entity 7
- [X] T018 [US1] Update PM2 `config/ecosystem.config.js` — add fte-email server entry (optional, since Claude Code manages stdio servers directly)

**Checkpoint**: Email MCP server fully functional. Claude Code can invoke email tools as first-class MCP tools. HITL gate works for sensitive actions. Architecture pattern validated for remaining servers.

---

## Phase 4: User Story 2 — Social Media Integration (Priority: P2)

**Goal**: Enable AI employee to draft and publish posts to Facebook, Instagram, and Twitter/X via social media MCP server with HITL approval.

**Independent Test**: Configure Twitter API credentials. Ask AI employee to draft a business post. Verify draft saved in `Plans/`, then `Pending_Approval` file created for publish. Approve and verify post appears on Twitter/X.

### Implementation for User Story 2

- [X] T019 [US2] Create `src/mcp/social_server.py` — MCP social media server skeleton using base_server.py, import `requests` for Facebook/Instagram and `tweepy` for Twitter per research R-002/R-003/R-004
- [X] T020 [US2] Implement content validator in `src/mcp/social_server.py` — validate content against platform character limits from `config/social-platforms.json` (Twitter: 280, Facebook: 63206, Instagram: 2200), return validation error with char count if exceeded per FR-011
- [X] T021 [P] [US2] Create `tests/unit/test_content_validator.py` — test validation for each platform limit, test edge cases (exact limit, one over, empty content)
- [X] T022 [US2] Implement `social.post_facebook` tool in `src/mcp/social_server.py` — validate content, HITL check (sensitive), dry-run returns preview, live mode POSTs to `graph.facebook.com/v19.0/{page_id}/feed` with Page Access Token, log to `Logs/mcp_social.jsonl`
- [X] T023 [US2] Implement `social.post_instagram` tool in `src/mcp/social_server.py` — validate caption (2200 chars), require `image_url`, two-step: create media container then publish, HITL check (sensitive), log to `Logs/mcp_social.jsonl` per research R-003
- [X] T024 [US2] Implement `social.post_twitter` tool in `src/mcp/social_server.py` — validate content (280 chars), use `tweepy.Client.create_tweet()` with OAuth 1.0a, handle rate limit (429/TooManyRequests with retry_after), HITL check (sensitive), log to `Logs/mcp_social.jsonl`
- [X] T025 [US2] Implement `social.weekly_summary` tool in `src/mcp/social_server.py` — parse `Logs/mcp_social.jsonl` for past N days, count posts per platform, generate `Social_Media_Summary.md` in vault, return stats per contract
- [X] T026 [US2] Create `social-media-poster` skill — create `.claude/skills/social-media-poster/SKILL.md` with skill definition: triggers on "post to social media", "draft social post", "social media summary"; references `src/mcp/social_server.py` tools
- [X] T027 [US2] Verify social media MCP server end-to-end: run `claude mcp list` to confirm fte-social registered, test dry-run post to each platform, verify HITL gate for publish actions, verify JSONL logging with correlation_id

**Checkpoint**: Social media MCP server fully functional. All 3 platforms supported. Content validation prevents invalid posts. HITL approval required for all publish actions.

---

## Phase 5: User Story 3 — Odoo ERP Integration (Priority: P3)

**Goal**: Connect AI employee to self-hosted Odoo 19 Community via JSON-RPC MCP server for reading financial data and creating invoices/payments with HITL approval.

**Independent Test**: Start Odoo Docker container. Call `odoo.list_invoices` via Claude Code — verify real data returned from Odoo database. Call `odoo.create_invoice` — verify HITL gate (critical) creates `Pending_Approval` file with invoice details.

### Implementation for User Story 3

- [X] T028 [US3] Create `src/mcp/odoo_server.py` — MCP Odoo server skeleton using base_server.py, import `odoorpc` (v0.10.1), establish connection to `localhost:8069` via JSON-RPC, handle `odoorpc.error.RPCError` and connection errors per research R-005
- [X] T029 [US3] Implement `odoo.list_invoices` tool in `src/mcp/odoo_server.py` — `search_read` on `account.move` model, filter by `payment_state` and `partner_id`, return structured JSON with invoice fields per contract, HITL: routine (auto-execute), log to `Logs/mcp_odoo.jsonl`
- [X] T030 [US3] Implement `odoo.create_invoice` tool in `src/mcp/odoo_server.py` — HITL: critical (approval + confirmation log), validate partner_id and line items, in dry-run return preview, in live mode create `account.move` with line items via JSON-RPC `create`, log to `Logs/mcp_odoo.jsonl` and `Logs/critical_actions.jsonl`
- [X] T031 [US3] Implement `odoo.register_payment` tool in `src/mcp/odoo_server.py` — HITL: critical, validate invoice_id and amount, register payment against invoice, update payment_state, log to both JSONL files per contract
- [X] T032 [US3] Implement `odoo.financial_summary` tool in `src/mcp/odoo_server.py` — query `account.move.line` records, aggregate by account type (revenue, expenses, receivables, payables), return totals for date range, HITL: routine, log to `Logs/mcp_odoo.jsonl`
- [X] T033 [US3] Implement `odoo.list_partners` tool in `src/mcp/odoo_server.py` — `search_read` on `res.partner` model, filter by `customer_rank > 0` when `customer_only=true`, optional name search, HITL: routine, log to `Logs/mcp_odoo.jsonl`
- [X] T034 [US3] Create `odoo-connector` skill — create `.claude/skills/odoo-connector/SKILL.md` with skill definition: triggers on "list invoices", "create invoice", "register payment", "financial summary", "odoo", "ERP"; references `src/mcp/odoo_server.py` tools
- [X] T035 [US3] Verify Odoo MCP server end-to-end: start Odoo Docker, run `claude mcp list` to confirm fte-odoo registered, test `odoo.list_invoices` returns real data, test `odoo.create_invoice` triggers HITL gate, verify JSONL logging

**Checkpoint**: Odoo MCP server fully functional. Read operations auto-execute. Write operations require HITL approval + confirmation log. Financial data accessible for CEO Briefing.

---

## Phase 6: User Story 4 — Error Recovery & Graceful Degradation (Priority: P4)

**Goal**: Integrate circuit breaker into all MCP servers, create health monitoring skill, ensure orchestrator skips degraded services and processes healthy tasks normally.

**Independent Test**: Stop Odoo Docker container. Trigger 3 Odoo calls — verify circuit breaker activates, `health.json` shows "degraded", `Dashboard.md` reflects degradation. Restart Odoo, wait for cooldown, verify auto-recovery.

### Implementation for User Story 4

- [X] T036 [US4] Integrate circuit breaker into `src/mcp/email_server.py` — wrap Gmail API calls with circuit breaker check/report, update `Logs/health.json` on success/failure
- [X] T037 [P] [US4] Integrate circuit breaker into `src/mcp/social_server.py` — wrap Facebook/Instagram/Twitter API calls (separate circuit per platform), handle non-retryable errors (401 Unauthorized) by immediately opening circuit and creating `Needs_Action` file per edge case
- [X] T038 [P] [US4] Integrate circuit breaker into `src/mcp/odoo_server.py` — wrap OdooRPC calls, handle connection errors and `RPCError`, update `Logs/health.json`
- [X] T039 [US4] Create `health-monitor` skill — create `.claude/skills/health-monitor/SKILL.md` with skill definition: triggers on "check health", "service status", "health monitor", "circuit breaker status"; reads `Logs/health.json` and reports service states
- [X] T040 [US4] Update `central-orchestrator` skill — add circuit breaker check before routing to MCP servers: read `Logs/health.json`, skip tasks targeting degraded services (mark as `retry_pending`), process all other tasks normally per FR-006/FR-012
- [X] T041 [US4] Update `Dashboard.md` template — add health status section showing each service (Gmail, Facebook, Instagram, Twitter, Odoo) with state (healthy/degraded/down), last success timestamp, and cooldown expiry per FR-007
- [X] T042 [US4] Handle rate-limit responses — in social MCP server, detect HTTP 429 (Twitter) and rate-limit responses (Facebook/Instagram), extract retry-after, queue action in `Logs/retry_queue.jsonl`, return deferred status per edge case

**Checkpoint**: Circuit breaker active on all MCP servers. Health monitoring shows real-time service status. Orchestrator gracefully degrades — processes healthy tasks, queues degraded ones.

---

## Phase 7: User Story 5 — CEO Briefing (Priority: P5)

**Goal**: Generate comprehensive weekly "Monday Morning CEO Briefing" aggregating Odoo financial data, completed tasks, social media activity, bottlenecks, and proactive suggestions.

**Independent Test**: Populate Odoo with sample invoices. Complete 10+ tasks. Run CEO briefing on demand. Verify `Briefings/YYYY-MM-DD_Monday_Briefing.md` contains all 6 sections with accurate data.

### Implementation for User Story 5

- [X] T043 [US5] Create `src/mcp/documents_server.py` — MCP documents server skeleton using base_server.py, expose 2 tools per contract `mcp-documents-tools.md`: `docs.generate_report` (routine), `docs.generate_briefing` (routine)
- [X] T044 [US5] Implement `docs.generate_report` tool in `src/mcp/documents_server.py` — generate markdown report from vault data for given report_type (task_summary, social_summary, health_status, custom), save to `Plans/report-<type>-<timestamp>.md`
- [X] T045 [US5] Implement `docs.generate_briefing` tool in `src/mcp/documents_server.py` — aggregate data from 5 sources per plan CEO Briefing Data Flow:
  1. Query Odoo MCP `odoo.financial_summary` for revenue/expenses
  2. Read `Done/` folder for completed task stats by source
  3. Read `Logs/mcp_social.jsonl` for social media activity
  4. Read `Pending_Approval/` for stale items (>24h = bottleneck)
  5. Read `Business_Goals.md` for target vs actual comparison
  Generate `Briefings/YYYY-MM-DD_Monday_Briefing.md` with all 6 sections per data-model.md Entity 6
- [X] T046 [US5] Handle partial briefing — when Odoo is unavailable (circuit breaker open), generate briefing with `incomplete: true` in frontmatter, skip Revenue & Expenses section, show "Financial data unavailable" notice per edge case
- [X] T047 [US5] Create `ceo-briefing` skill — create `.claude/skills/ceo-briefing/SKILL.md` with skill definition: triggers on "CEO briefing", "Monday briefing", "weekly audit", "business summary"; references `src/mcp/documents_server.py` tools
- [X] T048 [US5] Update `config/schedules.json` — add CEO briefing schedule entry: Sunday 8 PM trigger, creates `Needs_Action` file that routes to `docs.generate_briefing` tool
- [X] T049 [US5] Verify CEO briefing end-to-end: populate Odoo with sample data, complete tasks, run briefing on demand, verify all 6 sections present with accurate data matching sources

**Checkpoint**: CEO Briefing generates complete, accurate weekly report. Handles Odoo unavailability gracefully. Scheduled for automatic weekly generation.

---

## Phase 8: User Story 6 — Audit Logging & Documentation (Priority: P6)

**Goal**: Ensure end-to-end correlation ID traceability across all components, comprehensive JSONL audit logging, and complete project documentation.

**Independent Test**: Process one task end-to-end (Gmail watcher → orchestrator → MCP server). Search all JSONL files for correlation ID. Verify complete audit chain with no gaps.

### Implementation for User Story 6

- [X] T050 [US6] Update `gmail-watcher` skill — add `correlation_id` generation (import from `src/correlation.py`) to every `Needs_Action` file created by Gmail polling
- [X] T051 [P] [US6] Update `whatsapp-watcher` skill — add `correlation_id` generation to every `Needs_Action` file created by WhatsApp monitoring
- [X] T052 [P] [US6] Update `file_drop_watcher` (`src/file_drop_watcher.py`) — add `correlation_id` generation to every `Needs_Action` file created by filesystem watcher
- [X] T053 [P] [US6] Update `daily-scheduler` skill — add `correlation_id` generation to every `Needs_Action` file created by scheduled tasks
- [X] T054 [US6] Update `central-orchestrator` skill — propagate `correlation_id` from `Needs_Action` file through all orchestrator log entries, pass to MCP tool calls, include in routing decisions log
- [X] T055 [US6] Update `action-executor` skill — add MCP dispatch mode alongside existing importlib mode. When action maps to an MCP tool, invoke via MCP; otherwise fall back to importlib. Propagate `correlation_id` in both paths per FR-014 backward compatibility
- [X] T056 [US6] Handle legacy files without correlation_id — in orchestrator, detect missing `correlation_id` in `Needs_Action` files, generate retroactively, log warning "Missing correlation_id — generated retroactively for [filename]" per edge case
- [X] T057 [US6] Verify audit chain end-to-end: process one task from watcher to execution, search all `Logs/*.jsonl` files for correlation_id, verify complete chain: watcher creation → orchestrator scan → risk assessment → routing decision → action execution → outcome per SC-006
- [X] T058 [US6] Ensure all JSONL log entries contain minimum fields: `timestamp` (ISO 8601), `component`, `correlation_id`, `action`, `status`, `detail` — and sensitive fields redacted with `***REDACTED***` per spec acceptance scenario US6.4

**Checkpoint**: All components propagate correlation IDs. Complete audit chain traceable from watcher to execution. Backward compatible with Bronze/Silver files.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, testing, regression verification, and stability

- [X] T059 [P] Write `docs/architecture.md` — system diagrams (component flow, MCP server layout, HITL classification, circuit breaker state machine from plan.md), component descriptions, data flow per FR-016
- [X] T060 [P] Write `docs/lessons-learned.md` — development insights from Bronze (single watcher, vault), Silver (multi-watcher, orchestrator, scheduling), Gold (MCP servers, external APIs, circuit breakers) per FR-016
- [X] T061 [P] Write `docs/demo-script.md` — 5-10 minute demo walkthrough: start MCP servers, show email draft, approve social post, query Odoo, trigger CEO briefing, show health dashboard per FR-016
- [X] T062 Update `README.md` — add Gold tier features, MCP server list, setup instructions (Odoo Docker, social API creds, pip install), architecture overview per FR-016
- [X] T063 Create `tests/manual/gold-tier-test-plan.md` — manual test checklists for SC-001 through SC-010, covering all 6 user stories and edge cases
- [X] T064 Verify backward compatibility — run Bronze tier test plan (9 success criteria) and Silver tier test plan (10 success criteria), confirm zero regressions per SC-008/FR-014
- [X] T065 Dashboard serialization — ensure `Dashboard.md` writes are serialized through single-writer function in orchestrator, MCP servers write only to domain-specific JSONL logs per FR-017
- [X] T066 Run 30-minute stability test — all MCP servers active, at least one scheduled briefing trigger, 20+ events processed, zero unhandled exceptions per SC-010

**Checkpoint**: All documentation complete. All regression tests pass. System stable under 30-minute endurance test.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 MCP Architecture (Phase 3)**: Depends on Phase 2 — validates MCP pattern for all other servers
- **US2 Social Media (Phase 4)**: Depends on Phase 2 (can start after T010 base_server.py)
- **US3 Odoo ERP (Phase 5)**: Depends on Phase 2 (can start after T010 base_server.py)
- **US4 Error Recovery (Phase 6)**: Depends on Phases 3-5 (needs MCP servers to integrate circuit breaker)
- **US5 CEO Briefing (Phase 7)**: Depends on Phase 5 (needs Odoo MCP for financial data)
- **US6 Audit Logging (Phase 8)**: Depends on Phase 2 (correlation.py), can start in parallel with US2-US4
- **Polish (Phase 9)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Foundation only — MVP, validates architecture
- **US2 (P2)**: Foundation + base_server.py — independent of US1 (different MCP server)
- **US3 (P3)**: Foundation + base_server.py — independent of US1/US2
- **US4 (P4)**: Requires US1 + US2 + US3 MCP servers to exist (integrates circuit breaker into them)
- **US5 (P5)**: Requires US3 Odoo MCP (financial data source) + US4 circuit breaker (graceful degradation)
- **US6 (P6)**: Foundation + correlation.py — can progress in parallel with US2/US3; final verification after all servers exist

### Critical Path

```
Phase 1 → Phase 2 → Phase 3 (US1 MVP) → Phase 5 (US3 Odoo) → Phase 7 (US5 CEO Briefing) → Phase 9 (Polish)
                  ↘ Phase 4 (US2 Social) ↘
                                           Phase 6 (US4 Error Recovery)
                  ↘ Phase 8 (US6 Audit) ──────────────────────────────↗
```

### Parallel Opportunities

- **Within Phase 1**: T002, T003, T004, T005 all work on different files — full parallel
- **Within Phase 2**: T007, T008, T009 can run in parallel (different files); T010 depends on T006
- **After Phase 2**: US2 (Social) and US3 (Odoo) can start in parallel after base_server.py complete
- **Within US2**: T021 (test) can run parallel with T019 (skeleton)
- **Within US4**: T036, T037, T038 (circuit breaker integration) modify different MCP server files — parallel
- **Within US6**: T050, T051, T052, T053 (watcher updates) modify different files — parallel

---

## Parallel Example: User Story 2

```bash
# Launch content validator test alongside server skeleton:
Task: "Create tests/unit/test_content_validator.py"  # T021
Task: "Create src/mcp/social_server.py skeleton"      # T019

# After skeleton ready, implement all 3 platform tools sequentially (same file):
Task: "Implement social.post_facebook"                 # T022
Task: "Implement social.post_instagram"                # T023
Task: "Implement social.post_twitter"                  # T024

# Then summary + skill creation in parallel:
Task: "Implement social.weekly_summary"                # T025
Task: "Create social-media-poster skill"               # T026
```

---

## Implementation Strategy

### MVP First (User Story 1: MCP Architecture)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T012)
3. Complete Phase 3: US1 Email MCP Server (T013-T018)
4. **STOP and VALIDATE**: Test email MCP server independently — verify Claude Code invokes tools, HITL works, JSONL logging with correlation IDs
5. This validates the entire MCP architecture pattern before building remaining servers

### Incremental Delivery

1. Setup + Foundational → MCP infrastructure ready
2. US1 Email MCP → Architecture validated (MVP)
3. US2 Social Media → Cross-platform posting capability
4. US3 Odoo ERP → Financial data access
5. US4 Error Recovery → Production resilience
6. US5 CEO Briefing → Capstone feature (ties everything together)
7. US6 Audit Logging → End-to-end traceability
8. Polish → Documentation, regression, stability

### Suggested MVP Scope

**US1 only** (T001-T018, 18 tasks). Validates MCP architecture, HITL integration, and JSONL logging pattern. All subsequent MCP servers follow the same pattern.

---

## Summary

| Phase | User Story | Task Range | Task Count | Parallel Tasks |
|-------|-----------|------------|------------|----------------|
| 1     | Setup     | T001-T005  | 5          | 4              |
| 2     | Foundation| T006-T012  | 7          | 4              |
| 3     | US1 MCP   | T013-T018  | 6          | 0              |
| 4     | US2 Social| T019-T027  | 9          | 1              |
| 5     | US3 Odoo  | T028-T035  | 8          | 0              |
| 6     | US4 Errors| T036-T042  | 7          | 2              |
| 7     | US5 CEO   | T043-T049  | 7          | 0              |
| 8     | US6 Audit | T050-T058  | 9          | 4              |
| 9     | Polish    | T059-T066  | 8          | 3              |
| **Total** |       |            | **66**     | **18**         |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All MCP servers default to dry-run mode (DRY_RUN=true in env)
- All HITL classifications follow constitution principle II (HITL Safety)
- Backward compatibility: Silver action-executor and config/actions.json remain functional
