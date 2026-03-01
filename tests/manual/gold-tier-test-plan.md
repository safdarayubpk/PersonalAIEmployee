# Gold Tier Manual Test Plan

**Scope**: Comprehensive testing of the Gold tier Personal AI Employee (MCP servers, circuit breakers, CEO briefing, correlation IDs, graceful degradation).

**Duration**: 2-4 hours for full suite execution.

**Prerequisites**:
- All Bronze (9 tests) and Silver (10 tests) tier tests passing
- MCP servers built and runnable
- Odoo 19 Community running locally on `localhost:8069`
- Test data: sample Odoo invoices, sample social media accounts
- PM2 configured to start all processes

---

## Test Suite G1: MCP Server Registration and Tool Discovery

### G1-001: Email MCP Server Registration

**Objective**: Verify the email MCP server registers correctly in Claude Code.

**Steps**:
1. Start the email MCP server: `python src/mcp/email_server.py &`
2. Register in Claude Code: Add entry to `.claude/settings.json` with stdio command
3. Run: `claude mcp list`

**Expected Result**:
- Email MCP server appears in the list
- Tools visible: `email.draft`, `email.send`, `email.read`
- Server responds to `claude mcp test fte-email`

**Pass Criteria**: Server listed + tools visible + responds to test

---

### G1-002: Social Media MCP Server Registration

**Objective**: Verify social media MCP server with 3 platforms.

**Steps**:
1. Start social MCP server: `python src/mcp/social_server.py &`
2. Register in Claude Code settings
3. Run: `claude mcp list`

**Expected Result**:
- Social MCP server in list
- Tools visible: `social.post_facebook`, `social.post_instagram`, `social.post_twitter`
- Health check succeeds

**Pass Criteria**: All 3 platform tools present

---

### G1-003: Odoo ERP MCP Server Registration

**Objective**: Verify Odoo MCP server can connect to Odoo instance.

**Steps**:
1. Ensure Odoo running: `docker ps | grep odoo`
2. Start Odoo MCP server: `python src/mcp/odoo_server.py &`
3. Register in Claude Code settings
4. Run: `claude mcp test fte-odoo`

**Expected Result**:
- Odoo MCP server starts without error
- Health check shows "Connected to Odoo at localhost:8069"
- Tools visible: `odoo.list_invoices`, `odoo.create_invoice`, `odoo.financial_summary`

**Pass Criteria**: Server connected + tools present

---

### G1-004: Documents MCP Server Registration

**Objective**: Verify documents MCP server for report generation.

**Steps**:
1. Start documents MCP server: `python src/mcp/documents_server.py &`
2. Register in Claude Code settings
3. Run: `claude mcp test fte-documents`

**Expected Result**:
- Documents server starts
- Tools visible: `documents.generate_briefing`, `documents.generate_report`
- Server responds to test call

**Pass Criteria**: Server registered + tools visible

---

## Test Suite G2: Email MCP Tool Integration

### G2-001: Email Draft Tool (Dry-Run)

**Objective**: Test email draft creation in dry-run mode.

**Steps**:
1. Set `DRY_RUN=true`
2. Call email MCP: `claude invoke fte-email email.draft --params '{"to":"test@example.com","subject":"Test","body":"Hello"}'`
3. Check `Logs/mcp_email.jsonl`

**Expected Result**:
- No email sent
- Log entry with status="dry_run"
- JSONL entry contains redacted params (no password values)

**Pass Criteria**: Log shows dry_run, no external action

---

### G2-002: Email Send Tool (HITL Gate)

**Objective**: Test email send blocking until approval.

**Steps**:
1. Call email MCP (no approval): `claude invoke fte-email email.send --params '{"to":"test@example.com",...}'`
2. Check `Pending_Approval/` folder

**Expected Result**:
- File created in `Pending_Approval/` with full action payload
- Email NOT sent
- Log entry with status="pending_approval"

**Pass Criteria**: Approval file created, no email sent

---

### G2-003: Email Send with Approval

**Objective**: Test email send after HITL approval (if email configured).

**Steps**:
1. Locate approval file from G2-002
2. Move to `Approved/`: `mv Pending_Approval/* Approved/`
3. Re-trigger: `claude invoke fte-email email.send --live --approval-ref <path-to-approved-file>`
4. Check Gmail inbox (if live email configured)

**Expected Result**:
- If configured for live: Email sent to test address
- Log entry with status="success" and email metadata
- If not configured: Log shows "Would send (live mode, approval verified)"

**Pass Criteria**: Live send attempted + logged + (sent if configured)

---

### G2-004: Email Redaction in Logs

**Objective**: Verify no plaintext credentials in email logs.

**Steps**:
1. Run G2-001, G2-002, G2-003
2. Examine `Logs/mcp_email.jsonl`
3. Search for `password`, `token`, `secret`, `api_key` strings

**Expected Result**:
- All sensitive fields contain `***REDACTED***`
- No plaintext credential values found
- Search: `grep -E '(password|token|secret|api_key).*[^*]' Logs/mcp_email.jsonl` returns no matches

**Pass Criteria**: Zero unredacted credentials in logs

---

## Test Suite G3: Social Media MCP Integration

### G3-001: Facebook Post Validation

**Objective**: Test content length validation before posting.

**Steps**:
1. Create message with 100,000 characters (exceeds Facebook limit)
2. Call: `claude invoke fte-social social.post_facebook --params '{"page_id":"test","content":"<100k chars>","media":[]}'`
3. Check error response

**Expected Result**:
- Validation error returned with message "Content exceeds limit (100000 > 63206)"
- No API call attempted
- Status="validation_error" in log

**Pass Criteria**: Validation prevents API call

---

### G3-002: Twitter Post (280 Character Limit)

**Objective**: Test Twitter's strict character limit.

**Steps**:
1. Create message with 281 characters
2. Call: `claude invoke fte-social social.post_twitter --params '{"content":"<281 chars>"}'`
3. Check error

**Expected Result**:
- Validation error: "Content exceeds limit (281 > 280)"
- Not submitted to Twitter API

**Pass Criteria**: Validation blocks oversized tweets

---

### G3-003: Social Post HITL Gate (Sensitive)

**Objective**: Test approval gate for social media posts.

**Steps**:
1. Call social post (any platform, valid length, no approval)
2. Check response and `Pending_Approval/`

**Expected Result**:
- Response: `{status: "pending_approval", approval_file: "<path>"}`
- File created in `Pending_Approval/`
- Log entry with status="pending_approval"

**Pass Criteria**: Post blocked, approval file created

---

### G3-004: Social Post with Approval (Live)

**Objective**: Test posting after approval (if credentials configured).

**Steps**:
1. From G3-003, move approval file to `Approved/`
2. Re-call with `--live --approval-ref <path>`
3. Check platform (Twitter, Facebook, Instagram)

**Expected Result**:
- If live: Post appears on platform
- Log entry with post_id and platform timestamp
- Dashboard updated with posting activity

**Pass Criteria**: Post appears (if configured) + logged

---

### G3-005: Rate Limit Handling

**Objective**: Test graceful handling of rate limit responses.

**Steps**:
1. Rapidly post 5 messages in quick succession
2. Monitor Logs/mcp_social.jsonl for rate limit responses
3. Monitor Logs/health.json for service status

**Expected Result**:
- One or more posts return status="rate_limited"
- Circuit breaker counts towards degradation
- System queues failed posts for retry

**Pass Criteria**: Rate limits don't crash system, queued for retry

---

## Test Suite G4: Odoo ERP Integration

### G4-001: Odoo Connection and Authentication

**Objective**: Verify Odoo MCP server connects to running instance.

**Steps**:
1. Verify Odoo running: `curl -s http://localhost:8069/ | grep -q "Odoo" && echo "UP"`
2. Check Odoo MCP logs: `tail -20 Logs/mcp_odoo.jsonl`

**Expected Result**:
- Connection succeeds
- No authentication errors
- Log shows successful connection

**Pass Criteria**: Odoo reachable, MCP connected

---

### G4-002: List Invoices (Read-Only, Routine)

**Objective**: Test querying Odoo for invoice data.

**Steps**:
1. Populate Odoo with test invoices (via Odoo web UI or API)
2. Call: `claude invoke fte-odoo odoo.list_invoices --params '{"filter_unpaid":true}'`
3. Verify results in Logs/mcp_odoo.jsonl

**Expected Result**:
- Invoices returned as JSON array
- Fields: invoice_id, partner, amount, date, status
- Log entry with status="success"
- No approval required (routine read)

**Pass Criteria**: Data returned, no approval gate

---

### G4-003: Create Invoice (Write, Critical HITL)

**Objective**: Test invoice creation with HITL critical approval.

**Steps**:
1. Call: `claude invoke fte-odoo odoo.create_invoice --params '{"partner_id":1,"lines":[...],"date":"2026-03-01"}'`
2. Check `Pending_Approval/` and `Logs/critical_actions.jsonl`

**Expected Result**:
- Approval file created in `Pending_Approval/`
- Entry added to `Logs/critical_actions.jsonl` (critical actions log)
- Invoice NOT created in Odoo yet
- Status="pending_approval"

**Pass Criteria**: HITL gate works, critical log created

---

### G4-004: Create Invoice with Approval (Live)

**Objective**: Test creating invoice after HITL approval.

**Steps**:
1. From G4-003, move approval to `Approved/`
2. Call with `--live --approval-ref <path>`
3. Verify in Odoo web UI

**Expected Result**:
- Invoice created in Odoo (check via web UI or list_invoices)
- Log shows status="success" with invoice_id
- Dashboard updated with action summary

**Pass Criteria**: Invoice created + logged

---

### G4-005: Financial Summary Query

**Objective**: Test aggregated financial data retrieval.

**Steps**:
1. Ensure Odoo has invoices, payments, expenses
2. Call: `claude invoke fte-odoo odoo.financial_summary --params '{"month":"2026-03"}'`
3. Verify output

**Expected Result**:
- Returns JSON: `{revenue: X, expenses: Y, receivables: Z, payables: W}`
- Values match Odoo reports
- Log shows routine (no approval needed)

**Pass Criteria**: Financial totals correct + logged

---

### G4-006: Odoo Unavailable (Graceful Degradation)

**Objective**: Test system behavior when Odoo is offline.

**Steps**:
1. Stop Odoo: `docker-compose down`
2. Call any Odoo tool
3. Observe circuit breaker activation
4. Check `Logs/health.json`

**Expected Result**:
- Connection error returned (not crash)
- Health.json shows odoo service as "degraded" (after 3 failures)
- Dependent tasks queued for retry
- Dashboard shows Odoo: DEGRADED

**Pass Criteria**: Graceful degradation, health updated

---

## Test Suite G5: Circuit Breaker State Machine

### G5-001: Circuit Breaker Activation (3 Failures)

**Objective**: Test circuit breaker opening after 3 consecutive failures.

**Steps**:
1. Note initial state: `cat Logs/health.json | grep -A 5 '"service"'`
2. Trigger 3 failures to a service (e.g., call Odoo with offline instance)
3. Check health.json after each failure

**Expected Result**:
- Failure 1-2: state="healthy", failures=1-2
- Failure 3: state="degraded", failures=3
- Log: "Circuit breaker opened for service=X"

**Pass Criteria**: State transitions to degraded after 3 failures

---

### G5-002: Cooldown Period and Recovery Probe

**Objective**: Test half-open state and recovery.

**Steps**:
1. From G5-001, circuit is open (degraded)
2. Wait 5 minutes (or reduce COOLDOWN env var for faster test)
3. Attempt call to degraded service

**Expected Result**:
- First call (probe) succeeds (if service recovered)
- Health.json: state="healthy", failures=0
- If service still down: state stays "degraded", failures incremented

**Pass Criteria**: Half-open probe works, recovers on success

---

### G5-003: Multiple Degraded Services

**Objective**: Test dashboard showing multiple degraded services.

**Steps**:
1. Take down 2 services (e.g., Odoo + Twitter API mock)
2. Trigger failures to both
3. Check Dashboard.md health matrix

**Expected Result**:
- Health matrix shows multiple services with different states
- Orchestrator processes non-dependent tasks normally
- Dependent tasks queued

**Pass Criteria**: Multiple service health tracked, system stable

---

## Test Suite G6: Correlation ID End-to-End Tracing

### G6-001: Correlation ID Generation at Watcher

**Objective**: Verify correlation ID created at task origin.

**Steps**:
1. Create new task via file drop: `cp test.txt ~/Desktop/DropForAI/`
2. Wait for watcher to create Needs_Action file
3. Check frontmatter: `head -15 Needs_Action/<file>.md`

**Expected Result**:
- Frontmatter includes `correlation_id: corr-YYYYMMDD-HHMMSS-XXXX`
- Format matches pattern
- Unique ID per task

**Pass Criteria**: Correlation ID present and unique

---

### G6-002: Correlation ID Propagation Through Orchestrator

**Objective**: Verify ID appears in orchestrator logs.

**Steps**:
1. Run orchestrator on a batch of files
2. Extract correlation ID from a Needs_Action file
3. Search logs: `grep "<correlation_id>" Logs/orchestrator.jsonl`

**Expected Result**:
- Log entry for that file with same correlation_id
- Action (scan, assess, route, etc.)
- Status (success/pending_approval/retry)

**Pass Criteria**: ID present in orchestrator log

---

### G6-003: Correlation ID Through MCP Server to Action

**Objective**: Verify ID propagates to final action execution.

**Steps**:
1. Create task with known correlation_id
2. Route to action execution
3. Search: `grep "<correlation_id>" Logs/mcp_*.jsonl`

**Expected Result**:
- Log entry in `Logs/mcp_<domain>.jsonl` with same correlation_id
- Tool call details, result, status
- End-to-end chain complete

**Pass Criteria**: ID visible across all logs

---

### G6-004: Complete Audit Trail via Correlation ID

**Objective**: Trace full task lifecycle.

**Steps**:
1. Pick a correlation_id from a completed task
2. Run: `grep -h "<correlation_id>" Logs/*.jsonl | python3 analyze.py` (pretty-print timestamps)
3. Verify timeline

**Expected Result**:
- Watcher creation (Logs/vault_operations.jsonl)
- Orchestrator scan (Logs/orchestrator.jsonl)
- Risk assessment (Logs/orchestrator.jsonl)
- Action execution (Logs/actions.jsonl or Logs/mcp_*.jsonl)
- Final outcome (Logs/vault_operations.jsonl move to Done/Pending_Approval/)
- All entries within reasonable time window (seconds to minutes)

**Pass Criteria**: Complete timeline visible, no gaps

---

## Test Suite G7: CEO Briefing Generation

### G7-001: Briefing Generation on Demand

**Objective**: Manually trigger CEO briefing generation.

**Steps**:
1. Ensure sample data exists (invoices in Odoo, tasks in Done/, social posts in logs)
2. Run: `claude "generate ceo briefing"`
3. Check `Briefings/` folder

**Expected Result**:
- File created: `Briefings/YYYY-MM-DD_Monday_Briefing.md`
- Frontmatter: generated, period, data_sources, incomplete
- File has 6 sections (see G7-002)

**Pass Criteria**: Briefing created with correct structure

---

### G7-002: Briefing Sections and Content

**Objective**: Verify all briefing sections are populated.

**Steps**:
1. From G7-001, open the generated briefing
2. Check for each section:

| Section | Expected Content |
|---------|-----------------|
| Executive Summary | 2-3 sentence overview |
| Revenue & Expenses | "This Week: $X" with trend |
| Completed Tasks | Count by source, top 3 by complexity |
| Social Media Activity | Posts per platform with links |
| Bottlenecks | Pending items >24h old |
| Proactive Suggestions | Idle subscriptions, missed targets |

**Expected Result**:
- All 6 sections present
- Data accurate (matches source systems)
- Markdown formatting correct

**Pass Criteria**: All sections present and populated

---

### G7-003: Briefing with Unavailable Data Source

**Objective**: Test graceful degradation when a data source is unavailable.

**Steps**:
1. Stop Odoo: `docker-compose down`
2. Generate briefing: `claude "generate ceo briefing"`
3. Check briefing content and frontmatter

**Expected Result**:
- Briefing still generated
- Financial section shows: "Financial data unavailable — Odoo connection failed at [timestamp]. Showing task and social media data only."
- Frontmatter: `incomplete: true`
- Other sections (tasks, social) still populated

**Pass Criteria**: Partial briefing generated, incomplete flag set

---

### G7-004: Scheduled Briefing Trigger

**Objective**: Test that CEO briefing runs automatically on schedule.

**Steps**:
1. Configure schedule: Sunday 20:00 UTC (or adjust for current time + 2 min)
2. Verify in `config/schedules.json`: briefing task exists, enabled=true
3. Wait for scheduled time (or advance system clock if testing)
4. Check `Logs/scheduler.jsonl` for trigger event

**Expected Result**:
- Scheduler creates Needs_Action file at scheduled time
- Orchestrator processes it
- Briefing generated automatically
- Log shows trigger + generation event

**Pass Criteria**: Scheduled trigger works, briefing auto-generated

---

## Test Suite G8: Backward Compatibility with Bronze/Silver

### G8-001: Bronze Tier Filesystem Watcher Still Works

**Objective**: Verify Bronze file drop detection unchanged.

**Steps**:
1. Drop a test file: `cp test.txt ~/Desktop/DropForAI/test-bronze-compat.txt`
2. Wait 5 seconds
3. Check Needs_Action folder

**Expected Result**:
- File created: `Needs_Action/dropped-test-bronze-compat-*.md`
- Frontmatter has source=file-drop-watcher
- Works identically to Bronze tier

**Pass Criteria**: File detected + formatted correctly

---

### G8-002: Silver Tier Action Executor Still Works

**Objective**: Verify action executor via importlib still functional.

**Steps**:
1. Create task with `type: action`, `action: email.draft_email`
2. Run orchestrator
3. Check Plans/ for draft result

**Expected Result**:
- Silver action executor called (not MCP)
- Result in Plans/
- Log in Logs/actions.jsonl

**Pass Criteria**: Silver actions still execute

---

### G8-003: All Bronze Tests Pass

**Objective**: Run full Bronze tier test plan to verify no regression.

**Steps**:
1. Execute: `tests/manual/bronze-tier-test-plan.md` (all 9 tests)

**Expected Result**:
- All 9 Bronze tests pass
- No new failures

**Pass Criteria**: SC-001 through SC-009 from Bronze all pass

---

### G8-004: All Silver Tests Pass

**Objective**: Run full Silver tier test plan to verify no regression.

**Steps**:
1. Execute: `tests/manual/silver-tier-test-plan.md` (all 10 tests)

**Expected Result**:
- All 10 Silver tests pass
- Multi-watcher coordination works
- Action execution + retry + scheduling all work

**Pass Criteria**: SC-001 through SC-010 from Silver all pass

---

## Test Suite G9: Extended Stability and Stress Testing

### G9-001: 30-Minute Continuous Operation

**Objective**: Run all components together for extended period.

**Steps**:
1. Start all processes: `pm2 start config/ecosystem.config.js`
2. Create a test loop: every 30 seconds, drop a new test file
3. Run for 30 minutes
4. Monitor: `pm2 monit`

**Expected Result**:
- All processes stable (no crashes, auto-restarts)
- All files processed (no accumulation in Needs_Action)
- Dashboard updates correctly after each orchestrator run
- Logs grow at expected rate (no memory leaks)
- Zero unhandled exceptions

**Pass Criteria**: 30+ minutes without crashes, clean shutdown

---

### G9-002: Large Batch Processing

**Objective**: Test orchestrator with maximum batch size.

**Steps**:
1. Create 50 Needs_Action files
2. Run orchestrator with batch size = 50 (max)
3. Monitor processing time and memory

**Expected Result**:
- All 50 files processed in one batch
- Completes within 5 minutes
- Memory usage <500MB
- All files correctly routed

**Pass Criteria**: Large batch processed efficiently

---

## Test Summary

| Suite | Tests | Pass | Fail | Duration |
|-------|-------|------|------|----------|
| G1: MCP Registration | 4 | - | - | 5 min |
| G2: Email Integration | 4 | - | - | 10 min |
| G3: Social Media | 5 | - | - | 15 min |
| G4: Odoo ERP | 6 | - | - | 15 min |
| G5: Circuit Breaker | 3 | - | - | 10+ min |
| G6: Correlation IDs | 4 | - | - | 5 min |
| G7: CEO Briefing | 4 | - | - | 10 min |
| G8: Backward Compat | 4 | - | - | 20 min |
| G9: Stability | 2 | - | - | 35+ min |
| **TOTAL** | **36 tests** | - | - | **2-4 hours** |

---

## Regression Checklist

Before marking Gold tier complete:

- [ ] All 36 Gold tests pass
- [ ] All 9 Bronze tests pass (no regression)
- [ ] All 10 Silver tests pass (no regression)
- [ ] Zero unhandled exceptions in 30-minute run
- [ ] Dashboard accurate after each run
- [ ] Correlation IDs complete in all logs
- [ ] No unredacted credentials in JSONL logs
- [ ] MCP servers respond within 5 seconds
- [ ] Circuit breaker activates/recovers correctly
- [ ] CEO briefing contains all 6 sections
- [ ] Graceful degradation tested (service down)
- [ ] Documentation complete (architecture.md, lessons-learned.md, demo-script.md)

---

## Notes for Testers

1. **Isolation**: Each test should be independent. Reset vault state between suites if needed.
2. **Debugging**: Use `grep -r "<correlation_id>" Logs/` to trace any failure end-to-end.
3. **Performance**: Tuning batch sizes and polling intervals may be needed based on machine specs.
4. **External Services**: Actual email/social/Odoo integration requires API credentials. Mock endpoints can be used for testing.
5. **Flakiness**: Network-dependent tests (email, social, Odoo) may occasionally fail due to API latency. Retry once before marking failed.
