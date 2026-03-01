# Feature Specification: Personal AI Employee — Gold Tier (Autonomous Employee)

**Feature Branch**: `003-gold-tier`
**Created**: 2026-03-01
**Status**: Draft
**Input**: User description: "Gold tier - Autonomous Employee: Full cross-domain integration (Personal + Business), Odoo Community ERP self-hosted with MCP server via JSON-RPC, Facebook + Instagram integration (post + summary), Twitter/X integration (post + summary), multiple MCP servers for different action types, Weekly Business & Accounting Audit with CEO Briefing, error recovery and graceful degradation, comprehensive audit logging, Ralph Wiggum loop for autonomous multi-step completion, documentation of architecture and lessons learned. All AI functionality as Agent Skills. Based on hackathon document at root."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — MCP Server Architecture for External Actions (Priority: P1)

The developer upgrades the Silver tier's direct Python function calls (`importlib`-based action executor) to proper MCP (Model Context Protocol) servers that Claude Code can invoke as first-class tools. Each domain (email, social media, calendar, documents, ERP) gets its own MCP server exposing typed tool endpoints. Claude Code's reasoning layer calls these tools directly instead of going through the skill-based action executor. All MCP servers default to dry-run mode and respect the existing HITL approval flow (routine/sensitive/critical). The developer registers MCP servers in Claude Code's configuration and can verify each server responds to tool calls independently.

**Why this priority**: MCP servers are the foundational infrastructure that every other Gold tier feature depends on. Social media posting, Odoo integration, and the CEO briefing all need MCP tool endpoints. Without this, the remaining stories have no execution mechanism.

**Independent Test**: Start the email MCP server. Use Claude Code to call the `email.draft` tool with test parameters. Verify Claude receives a structured response, the action is logged, and no email is actually sent (dry-run default). Then test `email.send` — verify it creates a `Pending_Approval` file (HITL gate) instead of sending.

**Acceptance Scenarios**:

1. **Given** the email MCP server is running and registered in Claude Code config, **When** Claude Code invokes the `email.draft` tool with recipient, subject, and body parameters, **Then** the server returns a structured JSON response containing `{status: "dry_run", action: "email.draft", detail: ...}`, logs the call to `Logs/mcp_email.jsonl`, and takes no external action.
2. **Given** the social media MCP server is running, **When** Claude Code invokes `social.post_facebook` with content and page parameters, **Then** the server checks the action's HITL classification (sensitive), creates a `Pending_Approval` file with the full action payload, and returns `{status: "pending_approval", approval_file: "<path>"}` — no post is published.
3. **Given** an MCP server receives a tool call with `--live` mode and a valid `--approval-ref` pointing to an approved file in `Approved/`, **When** the approval is verified, **Then** the server executes the real external API call, logs the result to the domain-specific JSONL file, and returns the API response.
4. **Given** an MCP server crashes or becomes unresponsive, **When** Claude Code attempts to invoke a tool on that server, **Then** Claude Code receives a connection error, logs it, and the orchestrator can retry the action via the Ralph Wiggum loop without losing the task context.
5. **Given** multiple MCP servers are running simultaneously (email, social, ERP), **When** the developer runs `claude mcp list` or equivalent, **Then** all registered servers and their available tools are displayed with health status.

---

### User Story 2 — Social Media Integration: Facebook, Instagram, Twitter/X (Priority: P2)

The developer connects the AI employee to three social media platforms. The system can compose and publish posts to Facebook Pages, Instagram Business accounts, and Twitter/X. Each platform is exposed as tools in the social media MCP server. The developer configures API credentials via `.env`, and the AI employee can: (a) draft posts and save them locally for review, (b) publish approved posts to one or all platforms, and (c) generate a weekly summary of posting activity. All posting actions are classified as "sensitive" and require HITL approval. The AI employee can also generate content suggestions based on `Business_Goals.md` and recent activity.

**Why this priority**: Social media automation is the most visible and demonstrable Gold tier feature. It directly addresses the hackathon requirement "Automatically post on LinkedIn/social about business to generate sales" and showcases cross-domain integration (Business Goals → Content → Publish).

**Independent Test**: Configure Twitter/X API credentials. Ask the AI employee to draft a business post based on `Business_Goals.md`. Verify it creates a draft in `Plans/`, then creates a `Pending_Approval` file for the publish action. Move to `Approved/`, re-trigger — verify the post appears on Twitter/X (live mode) and is logged.

**Acceptance Scenarios**:

1. **Given** Facebook Page API credentials are configured in `.env` and the social MCP server is running, **When** the AI employee is asked to post a business update, **Then** it drafts content referencing `Business_Goals.md`, creates a `Pending_Approval` file with the draft text and target platform, and waits for approval before publishing.
2. **Given** Instagram Business credentials are configured and linked to the Facebook Page, **When** the developer approves a post for Instagram, **Then** the MCP server publishes the post via the Instagram Graph API, logs the post ID and timestamp to `Logs/mcp_social.jsonl`, and updates `Dashboard.md` with the posting activity.
3. **Given** Twitter/X API keys are configured, **When** the developer approves a tweet, **Then** the MCP server publishes via the Twitter API v2, logs the tweet ID, and handles rate limits gracefully (retry after the rate-limit reset window).
4. **Given** the developer asks to "post to all platforms", **When** the content is approved, **Then** the system publishes to Facebook, Instagram, and Twitter/X sequentially, logging each result independently. If one platform fails, the others still succeed and the failure is logged.
5. **Given** a week of posting activity exists in `Logs/mcp_social.jsonl`, **When** the weekly summary is triggered (manually or via scheduler), **Then** the system generates a `Social_Media_Summary.md` in the vault with: total posts per platform, post content snippets, and posting schedule adherence.

---

### User Story 3 — Odoo Community ERP Integration via MCP (Priority: P3)

The developer deploys Odoo 19 Community Edition locally (via Docker) and connects it to the AI employee through a dedicated Odoo MCP server that communicates via Odoo's JSON-RPC external API. The AI employee can read and write accounting records (invoices, payments, chart of accounts), manage contacts/partners, and pull financial data for audit and reporting. All write operations to Odoo are classified as "critical" (HITL gate + confirmation log). Read operations are "routine" (auto-execute). The Odoo MCP server translates Claude's tool calls into JSON-RPC method calls against the Odoo instance.

**Why this priority**: Odoo integration is the backbone of the Business Audit and CEO Briefing (US5). Without financial data from a real ERP, the CEO briefing would be based on static markdown files rather than live business data. This is the hackathon's "wow factor" — an AI that reads your actual accounting system.

**Independent Test**: Start the Odoo Docker container and the Odoo MCP server. Ask Claude Code to list all unpaid invoices via the `odoo.list_invoices` tool. Verify it returns real data from the Odoo database, logs the query, and requires no approval (read = routine).

**Acceptance Scenarios**:

1. **Given** Odoo 19 is running on `localhost:8069` with a configured database and the Odoo MCP server is running, **When** Claude Code invokes `odoo.list_invoices` with a filter for unpaid invoices, **Then** the server makes a JSON-RPC `search_read` call to `account.move`, returns the results as structured JSON, and logs the query to `Logs/mcp_odoo.jsonl`.
2. **Given** the developer asks the AI employee to create a new invoice for a client, **When** the MCP server receives the `odoo.create_invoice` tool call, **Then** it classifies the action as "critical", creates a `Pending_Approval` file with the full invoice details (partner, line items, amounts), logs to `Logs/critical_actions.jsonl`, and waits for HITL approval before writing to Odoo.
3. **Given** an approved invoice creation request, **When** the approval file is moved to `Approved/` and the action is re-triggered in live mode, **Then** the MCP server creates the invoice in Odoo via JSON-RPC `create` method on `account.move`, returns the new invoice ID, and logs the result.
4. **Given** the Odoo instance is unreachable (Docker container stopped), **When** any Odoo MCP tool is invoked, **Then** the server returns a clear connection error with the Odoo URL attempted, logs the failure, and the Ralph Wiggum loop retries with exponential backoff up to 3 attempts before escalating to a `Needs_Action` file.
5. **Given** the developer asks for a financial summary (revenue, expenses, outstanding payments for the current month), **When** Claude invokes `odoo.financial_summary`, **Then** the server queries `account.move.line` records, aggregates by account type, and returns totals for revenue, expenses, receivables, and payables — all read-only, no approval needed.

---

### User Story 4 — Error Recovery and Graceful Degradation (Priority: P4)

The developer operates the AI employee as a resilient system where individual component failures do not bring down the whole agent. When an MCP server crashes, the orchestrator marks affected tasks as "retry-pending" and continues processing other tasks. When an external API is unavailable (Gmail down, Twitter rate-limited, Odoo unreachable), the system queues the action locally and retries automatically. The system implements circuit breaker patterns: after 3 consecutive failures to a service, it stops calling that service for a cooldown period and logs a degradation notice. All error states are visible in `Dashboard.md` and `Logs/`. The developer can see at a glance which components are healthy and which are degraded.

**Why this priority**: A Gold tier "Autonomous Employee" must handle real-world failures gracefully. Without error recovery, any transient failure (network blip, API rate limit, Docker restart) breaks the entire pipeline and requires manual intervention — defeating the purpose of autonomy.

**Independent Test**: Stop the Odoo Docker container while the orchestrator is processing a batch that includes an Odoo-dependent task. Verify: the Odoo task is marked retry-pending, other tasks complete normally, the circuit breaker activates after 3 Odoo failures, `Dashboard.md` shows "Odoo: DEGRADED", and when Odoo restarts the system automatically recovers.

**Acceptance Scenarios**:

1. **Given** an MCP server (e.g., social media) becomes unresponsive during an orchestrator run, **When** the orchestrator detects the failure on a specific task, **Then** it marks that task as `status: retry_pending` in its frontmatter, logs the error with the MCP server name and error details, continues processing the remaining tasks in the batch, and the retry loop picks up the failed task in the next cycle.
2. **Given** an external API returns a rate-limit response (HTTP 429 or equivalent), **When** the MCP server receives the rate-limit error, **Then** it extracts the retry-after header (or uses a default 60-second backoff), queues the action locally in `Logs/retry_queue.jsonl`, and returns a structured response indicating the action is deferred — not failed.
3. **Given** 3 consecutive failures to the same external service within a 5-minute window, **When** the circuit breaker threshold is reached, **Then** the system marks that service as "degraded" in a health status file (`Logs/health.json`), stops sending requests to that service for a configurable cooldown period (default 5 minutes), logs the circuit-breaker activation, and updates `Dashboard.md` with the degradation notice.
4. **Given** a degraded service recovers (next health check succeeds), **When** the cooldown period expires and a probe request succeeds, **Then** the system marks the service as "healthy", resumes normal operation, processes any queued tasks for that service, and updates `Dashboard.md`.
5. **Given** multiple components are degraded simultaneously (e.g., Gmail API down + Odoo unreachable), **When** the orchestrator runs, **Then** it skips tasks dependent on degraded services, processes all other tasks normally, and the dashboard shows a clear health matrix listing each service and its status (healthy/degraded/down).

---

### User Story 5 — Weekly Business Audit and CEO Briefing (Priority: P5)

The developer configures the AI employee to produce a comprehensive weekly "Monday Morning CEO Briefing" document. Every Sunday evening (or on demand), the system autonomously: (a) queries Odoo for financial data (revenue, expenses, outstanding invoices, new payments), (b) reviews completed tasks from the `Done/` folder for the past week, (c) checks social media posting activity from logs, (d) identifies bottlenecks (tasks that took longer than expected or stalled in `Pending_Approval/`), and (e) generates proactive suggestions (e.g., "Subscription X had no activity in 30 days — cancel?"). The briefing is saved as a dated markdown file in a `Briefings/` vault folder and linked from `Dashboard.md`.

**Why this priority**: The CEO Briefing is the hackathon's "standout idea" — transforming the AI from a reactive task processor into a proactive business partner. It's the capstone feature that ties together all Gold tier integrations (Odoo, social, orchestrator) into one high-value deliverable.

**Independent Test**: Populate Odoo with sample invoices and payments for the past week. Complete 10+ tasks via the orchestrator. Run the CEO briefing generator on demand. Verify it produces a structured markdown document with accurate financial totals, task completion stats, social media activity, bottleneck identification, and at least one proactive suggestion.

**Acceptance Scenarios**:

1. **Given** the weekly audit is triggered (via scheduler on Sunday 8 PM or on-demand), **When** the AI employee runs the briefing generation workflow, **Then** it produces a file at `Briefings/YYYY-MM-DD_Monday_Briefing.md` containing sections: Executive Summary, Revenue & Expenses, Completed Tasks, Social Media Activity, Bottlenecks, and Proactive Suggestions.
2. **Given** Odoo contains 5 paid invoices ($500 each) and 2 unpaid invoices ($300 each) for the week, **When** the briefing queries financial data, **Then** the Revenue section shows "This Week: $2,500" and "Outstanding: $600" with a trend comparison to the previous week (up/down/flat).
3. **Given** 15 tasks were completed from `Done/` this week (5 filesystem, 6 Gmail, 4 WhatsApp), **When** the briefing compiles task stats, **Then** the Completed Tasks section shows the total count, breakdown by source, and lists the top 3 tasks by complexity (most processing steps).
4. **Given** 3 tasks sat in `Pending_Approval/` for more than 24 hours before being approved, **When** the briefing analyzes bottlenecks, **Then** the Bottlenecks section lists each delayed task with: title, time waiting, and the source that created it — helping the developer identify where the HITL gate slows things down.
5. **Given** social media logs show 4 posts published this week (2 Facebook, 1 Instagram, 1 Twitter), **When** the briefing compiles social activity, **Then** the Social Media Activity section shows post count per platform, content snippets, and a note about posting schedule adherence (e.g., "3 of 5 scheduled posts published — 2 missed due to approval delay").
6. **Given** an Odoo subscription/recurring expense has had no related activity for 30+ days, **When** the briefing scans for idle subscriptions, **Then** the Proactive Suggestions section flags it with the expense name, monthly cost, and a recommendation to review or cancel.

---

### User Story 6 — Comprehensive Audit Logging and Documentation (Priority: P6)

The developer has full visibility into every action the AI employee takes, with centralized audit trails and architecture documentation. All MCP server calls, approval decisions, retry attempts, and component health changes are logged in structured JSONL format with correlation IDs that link related events across components. The developer can trace any action from initial trigger (watcher event) through processing (orchestrator routing) to final execution (MCP call) using a single correlation ID. Additionally, the project includes comprehensive documentation: architecture overview, lessons learned, and a demo script.

**Why this priority**: Audit logging and documentation are explicit hackathon judging criteria (Security: 15%, Documentation: 10%). Complete audit trails also satisfy the constitution's requirement that "every failure MUST be visible and recoverable."

**Independent Test**: Process a single task end-to-end: Gmail watcher detects email → orchestrator routes it → MCP server sends reply. Search all JSONL log files for the correlation ID. Verify every step appears with timestamps, component names, and outcomes — forming a complete audit chain.

**Acceptance Scenarios**:

1. **Given** a task is created by any watcher, **When** the `Needs_Action` file is written, **Then** it includes a unique `correlation_id` in frontmatter (format: `corr-YYYYMMDD-HHMMSS-XXXX` where XXXX is random hex). This ID is propagated to all subsequent log entries for this task across all components.
2. **Given** a correlation ID from a completed task, **When** the developer searches across all `Logs/*.jsonl` files, **Then** they find a complete chain: watcher creation → orchestrator scan → risk assessment → routing decision → action execution (or HITL gate) → final outcome. No gaps in the chain.
3. **Given** the Gold tier is complete, **When** the developer reviews the project repository, **Then** it contains: `README.md` with architecture overview and setup instructions, `docs/architecture.md` with system diagrams and component descriptions, `docs/lessons-learned.md` with insights from building each tier, and a `docs/demo-script.md` with step-by-step instructions for a 5-10 minute demo video.
4. **Given** any JSONL log entry, **When** it is inspected, **Then** it contains at minimum: `timestamp` (ISO 8601), `component`, `correlation_id`, `action`, `status`, `detail` — and sensitive fields are redacted with `***REDACTED***`.

---

### Edge Cases

- What happens when the Odoo Docker container is not running at briefing generation time? The system MUST generate a partial briefing with a clear notice: "Financial data unavailable — Odoo connection failed at [timestamp]. Showing task and social media data only." The briefing is still saved but marked `incomplete: true` in frontmatter.
- What happens when a social media API permanently rejects credentials (HTTP 401 Unauthorized, not transient)? The system MUST classify this as a non-retryable error, immediately stop the circuit breaker for that service, log the authentication failure, create a `Needs_Action` file requesting the developer to re-authenticate, and update `Dashboard.md` with "Twitter: AUTH_FAILED".
- What happens when the developer approves a social media post but the content exceeds platform character limits (Twitter: 280 chars)? The MCP server MUST validate content length before attempting to post, return a validation error with the character count and limit, and suggest truncation — not silently truncate or fail at the API level.
- What happens when two MCP servers try to update `Dashboard.md` simultaneously? Dashboard updates MUST be serialized through a single writer (the orchestrator or a dedicated dashboard-update function). MCP servers write to their domain-specific logs; dashboard aggregation happens in one place.
- What happens when the Odoo database has no data (fresh install)? The CEO briefing MUST handle empty query results gracefully, showing "$0" for revenue/expenses and "No invoices found" rather than crashing on empty result sets.
- What happens when the weekly scheduler fires but the previous week's briefing is still being generated? The system MUST detect the in-progress briefing (via a lock file or status check), skip the duplicate trigger, and log "Briefing generation already in progress — skipping duplicate trigger."
- What happens when an MCP server receives a tool call with invalid parameters (missing required fields, wrong types)? The server MUST return a structured validation error listing the invalid fields and expected types, log the validation failure, and not attempt the external API call.
- What happens when the correlation ID is missing from a `Needs_Action` file (legacy Bronze/Silver files)? The system MUST generate a correlation ID retroactively when first processing the file and log a warning: "Missing correlation_id — generated retroactively for [filename]."

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide MCP servers for at least 4 domains (email, social media, ERP/accounting, documents) that Claude Code can invoke as tools. Each server MUST expose typed tool endpoints, default to dry-run mode, and respect the HITL classification (routine/sensitive/critical).
- **FR-002**: System MUST integrate with Facebook Pages API allowing the AI employee to draft and publish posts to a configured Facebook Page, with all publish actions classified as "sensitive" requiring HITL approval.
- **FR-003**: System MUST integrate with Instagram Graph API (via Facebook Page linkage) allowing the AI employee to publish image/text posts to a configured Instagram Business account, with publish actions classified as "sensitive."
- **FR-004**: System MUST integrate with Twitter/X API v2 allowing the AI employee to compose and publish tweets, handle rate limits (HTTP 429 with retry-after), with publish actions classified as "sensitive."
- **FR-005**: System MUST integrate with a self-hosted Odoo 19 Community instance via JSON-RPC external API. Read operations (list invoices, financial summary, contacts) are classified as "routine." Write operations (create invoice, register payment) are classified as "critical" (HITL + confirmation log).
- **FR-006**: System MUST implement a circuit breaker pattern for all external service calls: after 3 consecutive failures within 5 minutes, stop calling that service for a cooldown period (default 5 minutes), log the activation, and update health status.
- **FR-007**: System MUST maintain a health status file (`Logs/health.json`) tracking each external service's state (healthy/degraded/down), last successful call timestamp, consecutive failure count, and cooldown expiry time. Dashboard MUST reflect current health status.
- **FR-008**: System MUST generate a "Monday Morning CEO Briefing" document containing: executive summary, revenue and expenses (from Odoo), completed tasks (from `Done/`), social media activity (from logs), bottlenecks (stale `Pending_Approval/` items), and proactive suggestions (idle subscriptions, missed targets).
- **FR-009**: System MUST create a `Briefings/` folder in the vault and save each briefing as `YYYY-MM-DD_Monday_Briefing.md` with YAML frontmatter including `generated`, `period`, `data_sources` (list of services queried), and `incomplete` flag if any data source was unavailable.
- **FR-010**: System MUST assign a unique correlation ID (format: `corr-YYYYMMDD-HHMMSS-XXXX`) to every task at creation time and propagate it through all log entries across all components for end-to-end traceability.
- **FR-011**: System MUST validate social media content against platform constraints (Twitter: 280 chars, Facebook: 63,206 chars, Instagram: 2,200 chars for captions) before attempting to publish and return a validation error if content exceeds limits.
- **FR-012**: System MUST handle graceful degradation: when one or more external services are unavailable, the system continues processing tasks that don't depend on degraded services. Dependent tasks are queued for retry.
- **FR-013**: System MUST produce a weekly social media summary report (`Social_Media_Summary.md`) showing posts per platform, content snippets, and schedule adherence.
- **FR-014**: System MUST maintain backward compatibility with all Bronze and Silver tier functionality. Zero breaking changes to existing vault structure, file formats, skill interfaces, or action executor behavior.
- **FR-015**: System MUST log all MCP server calls to domain-specific JSONL files (`Logs/mcp_email.jsonl`, `Logs/mcp_social.jsonl`, `Logs/mcp_odoo.jsonl`) with correlation IDs, tool names, parameters (redacted), and results.
- **FR-016**: System MUST include project documentation: `README.md` (updated with Gold tier features), `docs/architecture.md` (system diagrams), `docs/lessons-learned.md` (development insights), and `docs/demo-script.md` (5-10 minute demo guide).
- **FR-017**: System MUST serialize all `Dashboard.md` writes through a single writer function to prevent concurrent update corruption from multiple MCP servers or components.
- **FR-018**: System MUST implement all new AI functionality as Claude Code Agent Skills, consistent with Bronze and Silver tier patterns.

### Key Entities

- **MCP Server**: A long-running process exposing domain-specific tools to Claude Code via the Model Context Protocol. Key attributes: server name, domain (email/social/erp/documents), list of tool endpoints, health status, port or stdio transport, HITL classification per tool. At least 4 servers for Gold tier.
- **Social Media Post**: A content unit targeting one or more platforms. Key attributes: content text, target platforms (facebook/instagram/twitter), media attachments (optional), character count, approval status, publish timestamp, platform-specific post ID after publishing.
- **Odoo Record**: A business object in the Odoo ERP (invoice, payment, partner, account). Key attributes: model name (e.g., `account.move`), record ID, key fields, operation type (read/create/update), HITL classification (read=routine, write=critical).
- **CEO Briefing**: A periodic summary document aggregating data from multiple sources. Key attributes: report period (date range), data sources queried, completeness flag, sections (revenue, tasks, social, bottlenecks, suggestions), generated timestamp.
- **Circuit Breaker**: A resilience mechanism per external service. Key attributes: service name, failure count, failure threshold (3), cooldown period (300 seconds), current state (closed/open/half-open), last state change timestamp.
- **Health Status**: A real-time snapshot of all external service states. Key attributes: service name, state (healthy/degraded/down), last success timestamp, consecutive failures, cooldown expiry.
- **Correlation ID**: A unique identifier assigned at task creation time that propagates through all processing stages. Format: `corr-YYYYMMDD-HHMMSS-XXXX` (XXXX = 4 hex chars). Links watcher events, orchestrator decisions, MCP calls, and outcomes.

### Assumptions

- Silver tier is fully operational: all 12 skills work, 3 watchers create `Needs_Action` files, action executor handles 6 actions, Ralph Wiggum retry loop persists through failures, scheduler creates recurring tasks, and central orchestrator routes files correctly.
- The developer will self-host Odoo 19 Community via Docker (`docker compose up`) with PostgreSQL. The Odoo MCP server communicates via `localhost:8069` JSON-RPC. Initial Odoo database setup (admin user, chart of accounts) is done manually by the developer through the Odoo web UI.
- Facebook/Instagram API credentials (Page Access Token, Instagram Business Account ID) are obtained by the developer from the Meta Developer Portal and stored in `.env`. The developer has a Facebook Page linked to an Instagram Business account.
- Twitter/X API credentials (API Key, API Secret, Access Token, Access Token Secret) are obtained by the developer from the X Developer Portal and stored in `.env`. The app has Read+Write permissions.
- MCP servers use stdio transport (same as Claude Code's native MCP integration) rather than HTTP — keeping the architecture local-first and consistent with Claude Code's MCP pattern.
- The existing `config/actions.json` action registry continues to work for Silver tier backward compatibility. Gold tier MCP servers are an additional layer, not a replacement.
- Sample/seed data in Odoo (a few invoices, payments, contacts) is created by the developer for demo purposes. The CEO briefing works with real Odoo data, not mock data.
- PM2 is used for process management of all MCP servers (extending the existing `config/ecosystem.config.js`).

### Constraints

- **C-001**: All vault operations remain scoped to `VAULT_PATH`. MCP servers write only to `Logs/` and vault workflow folders — never outside the vault.
- **C-002**: All file writes use atomic write pattern (temp + rename). MCP servers follow the same pattern for log writes.
- **C-003**: Dry-run mode remains the default for all MCP server tool calls. Live mode requires explicit `--live` flag AND satisfied HITL approval.
- **C-004**: No user data leaves the machine except through explicitly approved actions (social media posts, emails, Odoo writes). MCP servers make external API calls only in live mode after HITL approval.
- **C-005**: Odoo instance runs locally via Docker. No cloud-hosted Odoo. No data synced to external Odoo servers.
- **C-006**: Maximum 3 social media platforms (Facebook, Instagram, Twitter/X). No LinkedIn, TikTok, or other platforms in Gold tier scope.
- **C-007**: CEO Briefing generates markdown reports only. No PDF generation, no email delivery of briefings (that would be a separate approved action).
- **C-008**: All MCP servers must be registerable in Claude Code's MCP configuration and invocable as tools. No custom agent protocols — standard MCP only.
- **C-009**: Circuit breaker cooldown minimum is 60 seconds, maximum is 3600 seconds (1 hour). Default is 300 seconds (5 minutes).
- **C-010**: Backward compatibility: all Bronze (4 user stories) and Silver (5 user stories) test scenarios must continue passing. Zero regressions.
- **C-011**: All credentials stored in `.env` (never in vault, never committed to git). MCP servers read credentials from environment variables.

### Not in Scope

- Cloud deployment, remote VM hosting, or Git-based vault synchronization (Platinum tier).
- LinkedIn integration (mentioned in hackathon doc but not in Gold tier requirements list).
- Real-time notifications or push alerts (webhooks, mobile push). Developer checks dashboard.
- Payment execution through banking APIs (mentioned in hackathon doc under "Finance Watcher" but too high-risk for hackathon scope without proper banking sandbox).
- AI model training, fine-tuning, or custom model deployment.
- Odoo module development or custom Odoo addons — only standard external API usage.
- Multi-user access or role-based permissions. Single developer/operator.
- Automated invoice PDF generation from Odoo (use Odoo's built-in PDF export manually).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 4 MCP servers are running and registered in Claude Code config (email, social, ERP, documents). Each server responds to tool calls within 5 seconds. Claude Code can list all available tools across all servers. Verified by invoking one tool per server in dry-run mode and receiving valid structured responses.
- **SC-002**: Social media posting works end-to-end for all 3 platforms: draft content → approve → publish. Verified by publishing one test post to each platform (Facebook, Instagram, Twitter/X) in live mode after HITL approval. Each post appears on the platform and the post ID is logged in `Logs/mcp_social.jsonl`.
- **SC-003**: Odoo integration reads and writes data correctly. Verified by: (a) listing unpaid invoices from Odoo and receiving accurate results matching the Odoo web UI; (b) creating an invoice via approved MCP call and confirming it appears in Odoo's invoice list; (c) pulling a financial summary and verifying revenue/expense totals match Odoo reports.
- **SC-004**: Circuit breaker activates after 3 consecutive failures. Verified by: stopping an MCP server, triggering 3 calls to it, confirming `Logs/health.json` shows "degraded" status and `Dashboard.md` reflects the degradation. Restart the server, wait for cooldown expiry, confirm auto-recovery to "healthy" status.
- **SC-005**: CEO Briefing generates a complete, accurate document. Verified by: populating Odoo with sample financial data, completing 10+ tasks through the pipeline, publishing 3+ social media posts, then triggering the briefing generator. The resulting `Briefings/YYYY-MM-DD_Monday_Briefing.md` contains all 6 sections (Executive Summary, Revenue, Tasks, Social, Bottlenecks, Suggestions) with data matching the source systems.
- **SC-006**: Correlation IDs provide end-to-end traceability. Verified by: processing one task from watcher creation to final action execution, then searching all JSONL files for its correlation ID. Every step appears in the logs with the same ID — no gaps in the audit chain.
- **SC-007**: Graceful degradation works under multi-failure conditions. Verified by: stopping Odoo and the social MCP server, then running the orchestrator on a batch of 10 tasks (mix of sources and action types). Tasks not dependent on degraded services complete normally. Dependent tasks are queued for retry. Dashboard shows accurate health status for all services.
- **SC-008**: All Bronze (9 success criteria) and Silver (10 success criteria) test scenarios pass without modification after Gold tier implementation. Zero regressions.
- **SC-009**: Project documentation is complete: `README.md` updated, `docs/architecture.md` contains system diagram and component descriptions, `docs/lessons-learned.md` has insights from all 3 tiers, `docs/demo-script.md` provides a 5-10 minute walkthrough script.
- **SC-010**: Full system runs for 30 minutes with all MCP servers active, at least one scheduled briefing trigger, 20+ events processed through the full pipeline, and zero unhandled exceptions. Dashboard reflects accurate state at end of run.
