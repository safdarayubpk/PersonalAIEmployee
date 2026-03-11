# Feature Specification: Platinum Tier — Cloud-Local Hybrid Operation

**Feature Branch**: `004-platinum-tier`
**Created**: 2026-03-11
**Status**: Draft
**Input**: Upgrade Personal AI Employee from Gold to Platinum tier: cloud-local hybrid operation with git-synced vault, FTE_ROLE gating, claim-by-move, and offline-tolerant 24/7 operation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Always-On Email Triage While Laptop Is Off (Priority: P1)

Safdar closes his laptop at 11 PM and goes to sleep. At 2 AM, an urgent email arrives from a client requesting a quote. The cloud agent (running 24/7 on the Oracle Cloud VM) detects the email via the Gmail watcher, classifies it as "sensitive" (requires human approval to reply), drafts a professional response, and places a structured approval request file in `Pending_Approval/gmail/`. At 8 AM, Safdar opens his laptop. The local agent syncs the vault via git, detects the pending approval, and surfaces it in the vault. Safdar reviews the draft, moves the file to `Approved/`, and the local agent sends the email using the existing fte-email MCP server. The completed task is moved to `Done/` with a full correlation ID trail in the logs.

**Why this priority**: This is the core value proposition of Platinum tier — the system works while the owner sleeps. Without this, there is no upgrade from Gold.

**Independent Test**: Drop a test email into Gmail while the local agent is stopped. Verify: cloud agent creates a `Pending_Approval/gmail/*.md` file with correct frontmatter (title, priority, correlation_id, agent: cloud, status: pending_approval). Start local agent, move file to `Approved/`, verify email is sent and task moves to `Done/`.

**Acceptance Scenarios**:

1. **Given** the cloud agent is running and the local agent is stopped, **When** a new email arrives in Gmail, **Then** the cloud agent creates a draft reply file in `Pending_Approval/gmail/` within 2 sync cycles (default: 2 minutes).
2. **Given** a draft exists in `Pending_Approval/gmail/`, **When** the local agent starts and syncs, **Then** the pending approval appears in the vault within 1 sync cycle.
3. **Given** the user moves a file from `Pending_Approval/gmail/` to `Approved/`, **When** the local agent detects the move, **Then** it executes the email send via fte-email MCP and moves the completed file to `Done/`.
4. **Given** the cloud agent has `FTE_ROLE=cloud`, **When** it processes any email, **Then** it NEVER sends the email directly — only drafts.

---

### User Story 2 — Git-Based Vault Sync Between Cloud and Local (Priority: P1)

Both agents (cloud VM and local laptop) share the same Obsidian vault via a private GitHub repository. Every 60 seconds (configurable), each agent pulls the latest changes, processes any new files relevant to its role, commits its output, and pushes. The sync is resilient to temporary disconnection — if either side is offline, it queues changes and syncs on reconnection.

**Why this priority**: Without vault sync, the two agents cannot communicate. This is the foundational infrastructure for all Platinum features.

**Independent Test**: Create a file on the cloud VM in the vault, commit and push. On the local machine, run a sync cycle and verify the file appears. Repeat in the reverse direction. Then disconnect the local machine (stop the sync cron), make changes on both sides, reconnect, and verify both sets of changes are present without data loss.

**Acceptance Scenarios**:

1. **Given** a file is committed on the cloud VM, **When** the local agent runs a sync cycle, **Then** the file appears in the local vault within the configured sync interval.
2. **Given** the local machine is offline for 4 hours, **When** it reconnects and syncs, **Then** all cloud-side changes from the 4 hours are pulled without conflict.
3. **Given** both agents commit non-overlapping files during an offline period, **When** both sync, **Then** all files from both sides are present in both vaults.
4. **Given** a git merge conflict occurs, **When** the sync script detects it, **Then** it logs the conflict to `Logs/sync-conflicts.jsonl` and creates a `Needs_Action/manual/` file for human resolution.

---

### User Story 3 — Role-Based Action Gating (FTE_ROLE) (Priority: P1)

The orchestrator, watchers, and action executor on each machine check the `FTE_ROLE` environment variable before performing any action. When `FTE_ROLE=cloud`, the system refuses to execute any Sensitive or Critical action (email send, social post, payment, WhatsApp message) and instead writes a draft to `Pending_Approval/`. When `FTE_ROLE=local`, the system operates with full Gold-tier capabilities including HITL-gated execution.

**Why this priority**: Without role gating, the cloud VM could accidentally execute irreversible actions (send emails, make payments). This is the primary security boundary of Platinum tier.

**Independent Test**: Set `FTE_ROLE=cloud` and attempt to call the email send action. Verify it is blocked and a draft is created instead. Set `FTE_ROLE=local` and verify the same action executes normally (with HITL gate).

**Acceptance Scenarios**:

1. **Given** `FTE_ROLE=cloud`, **When** the action executor receives a "send_email" action, **Then** it refuses execution, logs the refusal, and creates a draft in `Pending_Approval/gmail/`.
2. **Given** `FTE_ROLE=cloud`, **When** the action executor receives a "move_file" action (Routine), **Then** it executes normally.
3. **Given** `FTE_ROLE=local`, **When** the action executor receives a "send_email" action, **Then** it proceeds through the standard HITL gate (write to `Pending_Approval/`, wait for `Approved/` move).
4. **Given** `FTE_ROLE` is not set, **When** any component starts, **Then** it refuses to start and logs a fatal error: "FTE_ROLE must be set to 'cloud' or 'local'".

---

### User Story 4 — Claim-by-Move Concurrency Control (Priority: P2)

When a new task file appears in `Needs_Action/gmail/`, the first agent to detect it moves it to `In_Progress/cloud/` or `In_Progress/local/`. The other agent, on its next cycle, sees the file is gone from `Needs_Action/` and skips it. This prevents both agents from processing the same email, social post, or task simultaneously.

**Why this priority**: Without claim-by-move, both agents could draft duplicate replies to the same email or process the same task twice. Important for correctness, but the system is still useful (with duplicates) without it, so P2.

**Independent Test**: Place a file in `Needs_Action/gmail/`. Start both agents simultaneously. Verify exactly one agent claims the file (it appears in exactly one `In_Progress/` subfolder) and the other agent's logs show "file already claimed, skipping".

**Acceptance Scenarios**:

1. **Given** a file exists in `Needs_Action/gmail/`, **When** the cloud agent claims it, **Then** it is moved to `In_Progress/cloud/` and no longer exists in `Needs_Action/gmail/`.
2. **Given** a file was claimed by the cloud agent, **When** the local agent scans `Needs_Action/gmail/`, **Then** it does not find the file and logs "skipped: already claimed".
3. **Given** both agents attempt to claim the same file within the same sync cycle, **When** git resolves the conflict, **Then** only one agent's claim survives (the first committer wins).

---

### User Story 5 — Single-Writer Dashboard Updates (Priority: P2)

The cloud agent generates incremental status updates (new emails processed, tasks triaged, drafts created) and writes them to `Updates/dashboard-update-<timestamp>.md`. The local agent, on each sync cycle, reads all pending update files from `Updates/`, merges them into `Dashboard.md`, and deletes the processed update files. This ensures `Dashboard.md` is never written by two agents simultaneously.

**Why this priority**: Dashboard consistency is important for the user's situational awareness, but the system functions without it. The user can always check individual folders directly.

**Independent Test**: Cloud agent processes 3 emails and writes 3 update files to `Updates/`. Local agent syncs, merges all 3 into `Dashboard.md`, and deletes the update files. Verify Dashboard.md contains all 3 updates and `Updates/` is empty.

**Acceptance Scenarios**:

1. **Given** `FTE_ROLE=cloud`, **When** the cloud agent completes a task, **Then** it writes an update file to `Updates/` (never modifies `Dashboard.md` directly).
2. **Given** `FTE_ROLE=local`, **When** the local agent detects files in `Updates/`, **Then** it merges them into `Dashboard.md` and removes the processed update files.
3. **Given** the local agent is offline for 12 hours, **When** it reconnects, **Then** it processes all accumulated update files in chronological order.

---

### User Story 6 — Secrets Isolation and .gitignore Enforcement (Priority: P1)

The vault's `.gitignore` prevents all secrets, session files, tokens, and credentials from being committed to git. A pre-commit hook validates that no file matching the exclusion patterns is staged. The cloud VM never has access to `.env`, `*.session`, `*.token`, `*.key`, `*.pem`, or `credentials/` directories.

**Why this priority**: Security is non-negotiable. If secrets leak to git (and thus to the cloud VM), the entire trust model breaks. This must be in place before any syncing begins.

**Independent Test**: Attempt to `git add .env` and `git commit`. Verify the pre-commit hook rejects the commit with a clear error message. Verify the cloud VM's vault directory does not contain any secret files after a full sync.

**Acceptance Scenarios**:

1. **Given** a `.env` file exists in the vault, **When** a user runs `git add .env && git commit`, **Then** the pre-commit hook blocks the commit and prints "BLOCKED: .env matches secrets exclusion pattern".
2. **Given** a `*.session` file exists locally, **When** a full `git push` is executed, **Then** the session file is not present in the remote repository.
3. **Given** the cloud VM runs `git pull`, **When** it lists vault contents, **Then** no files matching `.env`, `*.session`, `*.token`, `*.key`, `*.pem`, or `credentials/` are present.

---

### User Story 7 — Correlation ID Tracking Across Agents (Priority: P3)

Every task that crosses the cloud-local boundary carries a correlation ID (`corr-<ISO-date>-<8-char-hex>`). The ID is generated when the task is first created and persists through every stage: `Needs_Action` → `In_Progress` → `Pending_Approval` → `Approved` → `Done`. Every JSONL log entry related to the task includes the correlation ID, enabling end-to-end audit trails across both agents.

**Why this priority**: Audit trail is important for debugging and compliance, but the system functions without it. Existing Gold-tier correlation ID infrastructure can be extended.

**Independent Test**: Process an email through the full lifecycle (cloud triage → draft → local approve → send → done). Grep the JSONL logs on both cloud and local for the correlation ID. Verify every stage is logged with the same ID.

**Acceptance Scenarios**:

1. **Given** the cloud agent creates a task, **When** it writes the `Needs_Action` file, **Then** the YAML frontmatter includes `correlation_id: corr-<date>-<hex>`.
2. **Given** a task with correlation ID moves through all stages, **When** logs are queried by correlation ID, **Then** every stage (created, claimed, drafted, approved, executed, done) appears in chronological order.
3. **Given** a task crosses from cloud to local, **When** the local agent processes it, **Then** it preserves and references the original correlation ID (does not generate a new one).

---

### User Story 8 — Cloud VM 24/7 Daemon Operation (Priority: P2)

The cloud agent runs as a set of PM2-managed daemons on the Oracle Cloud VM: git-sync service, gmail-watcher (cloud mode), and scheduler. These 3 processes start automatically on VM boot, restart on crash (max 5 restarts per 60 seconds), and log to component-specific JSONL files. The health monitor tracks service status in `Logs/health.json`. (Note: a dedicated cloud orchestrator is excluded to conserve memory on E2.1.Micro — see ADR-0014. Cloud processing is handled directly by watchers and scheduler.)

**Why this priority**: Daemon management is infrastructure. The system can be demo'd with manual starts, but 24/7 reliability requires PM2/systemd management.

**Independent Test**: SSH into the cloud VM. Verify all 3 processes are running via `pm2 list`. Kill one process manually. Verify it restarts within 5 seconds. Check `Logs/health.json` for current service status.

**Acceptance Scenarios**:

1. **Given** the cloud VM boots, **When** PM2 starts, **Then** all cloud-mode services (git-sync, gmail-watcher, scheduler) are running within 30 seconds.
2. **Given** a cloud service crashes, **When** PM2 detects the crash, **Then** it restarts the process within 5 seconds and logs the crash to the service's JSONL log file.
3. **Given** a service crashes 6 times in 60 seconds, **When** PM2 hits the restart limit, **Then** it stops the service and creates a `Needs_Action/manual/` file describing the failure.

---

### Edge Cases

- What happens when both agents are offline simultaneously? Tasks accumulate in `Needs_Action/` on GitHub; first agent to come online processes them.
- How does the system handle a git push conflict where both agents commit at the same time? The second pusher's `git push` fails; the sync script retries with `git pull --rebase` then re-pushes.
- What if the cloud VM runs out of disk space? Health monitor detects low disk via `Logs/health.json`; creates `Needs_Action/manual/` alert.
- What if the user rejects a draft in `Pending_Approval/`? File is moved to `Rejected/` per constitution v1.3.1 Section 7.2.1; cloud may re-draft or escalate.
- What if the Gmail API token expires on the cloud VM? Cloud agent logs the failure to `Logs/gmail.jsonl`, creates `Needs_Action/manual/` for human to re-authenticate on local machine, and enters circuit breaker OPEN state for Gmail.
- What if the vault `.gitignore` is accidentally modified to remove secret exclusions? The pre-commit hook independently validates against a hardcoded exclusion list; the commit is blocked regardless of `.gitignore` content.

## Requirements *(mandatory)*

### Functional Requirements

**Git Sync Engine**

- **FR-001**: System MUST provide a `git-sync` service that runs `git pull --rebase` → process → `git add . && git commit && git push` on a configurable interval (`GIT_SYNC_INTERVAL_SECONDS`, default: 60).
- **FR-002**: System MUST handle `git push` failures by retrying with `git pull --rebase` up to 3 times before logging to `Logs/sync-conflicts.jsonl` and creating a `Needs_Action/manual/` file.
- **FR-003**: System MUST queue commits when offline and push all queued changes on the next successful sync.
- **FR-004**: System MUST NOT sync files matching the vault `.gitignore` patterns (`.env`, `*.session`, `*.token`, `*.key`, `*.pem`, `credentials/`, `secrets/`).

**Role Gating**

- **FR-005**: System MUST read `FTE_ROLE` from `.env` at startup. Valid values: `cloud`, `local`. Any other value or missing variable MUST cause a fatal startup error.
- **FR-006**: When `FTE_ROLE=cloud`, the action executor MUST refuse all Sensitive and Critical actions. It MUST instead create a draft file in `Pending_Approval/<domain>/` with full context for human review.
- **FR-007**: When `FTE_ROLE=local`, the action executor MUST operate identically to Gold tier (full HITL-gated execution).
- **FR-008**: The `FTE_ROLE` check MUST be enforced at the action executor level, not just the orchestrator, to prevent bypasses.

**Claim-by-Move**

- **FR-009**: Before processing a file in `Needs_Action/<domain>/`, the agent MUST atomically move it to `In_Progress/<role>/` (where role is `cloud` or `local`).
- **FR-010**: If the source file no longer exists when attempting the move, the agent MUST log "file already claimed" and skip processing.
- **FR-011**: After completing work on a claimed file, the agent MUST move it to the appropriate next folder (`Pending_Approval/`, `Done/`, or `Rejected/`).

**Single-Writer Dashboard**

- **FR-012**: When `FTE_ROLE=cloud`, the agent MUST write status updates to `Updates/dashboard-update-<ISO-timestamp>.md` and MUST NOT modify `Dashboard.md` directly.
- **FR-013**: When `FTE_ROLE=local`, the agent MUST process all files in `Updates/` and merge them into `Dashboard.md` on each cycle, then delete the processed update files.

**Secrets Isolation**

- **FR-014**: The vault repository MUST include a `.gitignore` with the patterns defined in constitution v1.3.1 Section: Security.
- **FR-015**: A pre-commit hook MUST validate that no staged file matches the secrets exclusion patterns. Commits violating this MUST be rejected.
- **FR-016**: The cloud VM MUST NOT have access to any file matching secrets patterns. If such a file is detected on the cloud VM, it MUST be logged as a critical security event.

**Correlation IDs**

- **FR-017**: Every task file created by any agent MUST include a `correlation_id` field in YAML frontmatter, formatted as `corr-<ISO-date>-<8-char-hex>`.
- **FR-018**: Every JSONL log entry related to a cross-agent task MUST include the `correlation_id` field.
- **FR-019**: When a task is claimed, moved, or completed, the correlation ID MUST be preserved (never regenerated).

**Vault Folder Structure**

- **FR-020**: The vault MUST contain the Platinum folder structure as defined in constitution v1.3.1 Section 7.2: `Needs_Action/<domain>/`, `In_Progress/cloud/`, `In_Progress/local/`, `Pending_Approval/<domain>/`, `Updates/`, `Approved/`, `Rejected/`, `Done/`.
- **FR-021**: Domain subfolders under `Needs_Action/` MUST include at minimum: `gmail/`, `whatsapp/`, `scheduler/`, `manual/`.
- **FR-022**: Domain subfolders under `Pending_Approval/` MUST include at minimum: `gmail/`, `social/`, `odoo/`, `general/`.

**Cloud Daemon Management**

- **FR-023**: The cloud VM MUST run cloud-mode services (git-sync, gmail-watcher, orchestrator, scheduler) as PM2-managed daemons.
- **FR-024**: PM2 configuration MUST limit restarts to 5 per 60-second window. On exhaustion, the service enters stopped state and a `Needs_Action/manual/` file is created.
- **FR-025**: All cloud services MUST start automatically on VM boot via PM2 startup configuration.

**Approval Flow**

- **FR-026**: When the local agent detects a file moved to `Approved/`, it MUST execute the action described in the file using the appropriate Gold-tier MCP server (fte-email, fte-social, fte-odoo, fte-documents).
- **FR-027**: After successful execution, the local agent MUST move the file to `Done/` with `status: done` and an execution timestamp in frontmatter.
- **FR-028**: If execution fails, the local agent MUST move the file back to `Needs_Action/manual/` with failure details appended.

**Rejection Flow**

- **FR-031**: When the local agent moves a file from `Pending_Approval/<domain>/` to `Rejected/`, it MUST add `status: rejected` and `rejection_reason` to frontmatter and log the rejection with correlation ID to `Logs/actions.jsonl`.
- **FR-032**: The cloud agent MAY pick up files in `Rejected/` on its next cycle to re-draft (if the rejection reason is actionable) or escalate to `Needs_Action/manual/` for human re-specification.
- **FR-033**: Files in `Rejected/` older than 7 days without re-processing MUST be flagged in `Dashboard.md` as stale.

**Single-Writer Enforcement**

- **FR-034**: When `FTE_ROLE=cloud`, the agent MUST NOT modify `Company_Handbook.md` or `Logs/critical_actions.jsonl`. These are local-only write targets per constitution Section 7.4.

**Stale File Detection**

- **FR-035**: The local agent MUST flag `Pending_Approval/` files older than 48 hours and `Rejected/` files older than 7 days as stale in `Dashboard.md`.

**Gold-Tier Backward Compatibility**

- **FR-029**: All Gold-tier features (watchers, orchestrator, CEO briefing, health monitoring, Ralph Wiggum retries, circuit breakers) MUST continue functioning in Platinum mode.
- **FR-030**: Setting `FTE_ROLE=local` on the laptop MUST result in identical behavior to Gold tier for all existing workflows, with the addition of vault sync and approval processing.

### Key Entities

- **Task File**: A markdown file with YAML frontmatter that flows through vault folders. Key attributes: `title`, `created`, `tier`, `source`, `priority`, `status`, `agent`, `correlation_id`. Statuses: `needs_action` → `in_progress` → `pending_approval` → `approved` → `done` (or `rejected`).
- **Update File**: A timestamped markdown file in `Updates/` containing incremental status changes from the cloud agent. Consumed and deleted by the local agent during dashboard merge.
- **Sync State**: The git repository state on each machine. Tracks last sync timestamp, pending commits, and conflict history in `Logs/sync.jsonl`.
- **Agent Role**: Determined by `FTE_ROLE` env var. Constrains which actions the agent can perform. Immutable for the lifetime of a process.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The system continues processing new events (email, scheduled tasks) for at least 8 continuous hours while the local laptop is completely powered off.
- **SC-002**: An email arriving while the local agent is offline results in a draft approval file committed to the git remote within 3 minutes of email receipt (2 sync cycles at default 60s interval), without any human intervention on the cloud side.
- **SC-003**: End-to-end demo (email arrives → cloud drafts → local approves → email sent → task done) completes in under 10 minutes with no more than 3 manual steps (open laptop, review draft, move file to Approved).
- **SC-004**: Zero secrets (`.env`, session files, tokens, keys) are present in the git repository history at any point. Verified by scanning all commits.
- **SC-005**: When both agents are running simultaneously, zero duplicate task processing occurs over a 1-hour test period with 10+ incoming tasks.
- **SC-006**: All Gold-tier test scenarios continue to pass without modification when `FTE_ROLE=local` is set.
- **SC-007**: Cloud agent health monitor reports all services healthy (`Logs/health.json`) for 90%+ uptime over a 24-hour test period on E2.1.Micro (1 OCPU/1GB RAM). Target increases to 99%+ on A1.Flex (4 OCPU/24GB) when available.
- **SC-008**: Every cross-agent task has a complete correlation ID audit trail — greppable in JSONL logs with no gaps between stages.
- **SC-009**: Git sync recovers automatically from temporary network outages lasting up to 30 minutes without data loss.
- **SC-010**: Hackathon judges can observe the full offline-tolerant email workflow in a live demo under 15 minutes.

## Assumptions

- The private GitHub repository for vault sync is already created (`safdarayubpk/PersonalAIEmployee`).
- Gmail API credentials are configured on the cloud VM (OAuth token for read-only access; full send credentials remain local-only). **Risk**: Gmail OAuth refresh tokens on the headless cloud VM may expire and require browser-based re-authentication on the local machine. The cloud agent MUST enter circuit breaker OPEN state for Gmail when token refresh fails and create a `Needs_Action/manual/` file prompting human re-authentication.
- The existing Gold-tier codebase is stable and all Gold-tier tests pass on the `main` branch.
- The cloud VM has sufficient resources (E2.1.Micro: 1 OCPU, 1 GB RAM) to run the git-sync service, Gmail watcher in read-only mode, orchestrator in cloud mode, and scheduler concurrently.
- PM2 is installed or will be installed on the cloud VM as part of Platinum implementation.
- The user has basic familiarity with Obsidian vault folder navigation for the approval flow (move files between folders).

## Non-Goals

- Multi-cloud or Kubernetes/Dapr/Ray scaling.
- Advanced git conflict auto-resolution beyond basic `pull --rebase`.
- New Obsidian UI/dashboard plugins or views.
- Full production monitoring/alerting beyond `health.json`.
- New watchers or MCP servers — only extending existing ones with role awareness.
- A2A direct messaging or WebSocket communication between agents.
- WhatsApp watcher on cloud VM (requires local `.session` files).
- Odoo write operations from cloud agent (cloud creates draft records only; local approves and posts).
