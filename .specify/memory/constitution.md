<!--
  Sync Impact Report
  ==================
  Version change: 1.3.0 → 1.3.1 (patch: review fixes)
  Fixes applied:
    - VII intro: hardcoded IP replaced with FTE_CLOUD_HOST env var reference
    - VII 7.2: added Rejected/ folder to Platinum folder structure
    - VII 7.2.1: NEW subsection — rejection flow (move to Rejected/,
      log with correlation ID, cloud re-draft or escalate, 7-day stale flag)
    - Needs_Action format: agent/correlation_id comments changed from
      "Platinum:" to "Platinum only; omit in Bronze–Gold"
    - Vault frontmatter: clarified agent/correlation_id are optional in
      lower tiers and MUST be omitted (not empty)
  Previous version change: 1.2.1 → 1.3.0
  Modified principles:
    - NEW VII. Hybrid Cloud-Local Operation: defines cloud agent vs local
      agent responsibilities, claim-by-move concurrency, file-based IPC
      via git-synced vault, FTE_ROLE env var, correlation IDs, and
      secrets-never-in-git policy for Platinum tier
    - I. Local-First: updated to acknowledge Platinum exception — vault
      data MAY reside on cloud VM but only markdown working copies;
      secrets/sessions/tokens remain local-only
    - IV. Modularity: Platinum tier row expanded with operational detail
      referencing new Principle VII
  Updated sections:
    - Standards & Constraints > Vault: added Platinum folder structure
      (Needs_Action/<domain>/, In_Progress/cloud|local/, Updates/)
    - Standards & Constraints > Security: added .gitignore mandate for
      secrets, session files, and credential stores
    - Standards & Constraints > Logging: added correlation_id to required
      JSONL fields for cross-agent traceability
    - Success Criteria: added Platinum-tier demo scenario
    - Governance: version bumped to 1.3.0, amendment date 2026-03-10
  Previous changes (1.2.0 → 1.2.1):
    - III. Proactive Autonomy: RALPH_MAX_ITERATIONS default corrected
      25 → 15, hard cap 20 added (matches spec FR-006 and original
      hackathon document "10-20 iterations")
    - VI. Error Handling: errors.jsonl replaced with component-specific
      JSONL logs (gmail.jsonl, orchestrator.jsonl, etc.) to avoid
      duplicate logging
  Previous changes (1.1.0 → 1.2.0):
    - II. HITL Safety: added risk-level classification (routine/sensitive/critical)
    - III. Proactive Autonomy: loop default raised 10 → 25, env var named,
      exhaustion behavior defined
    - IV. Modularity: Silver tier scope updated from "MCP servers" to
      "action execution" (direct function calls); MCP/FastAPI deferred to Gold
    - Principle VI: Error Handling & Recovery added
    - Structured logging standard, vault file conventions, priority vocabulary
    - Action execution clarification (Silver = importlib, Gold = MCP/FastAPI)
  Templates requiring updates:
    - .specify/templates/plan-template.md — review for Platinum references
    - .specify/templates/spec-template.md — review for Platinum references
    - .specify/templates/tasks-template.md — review for Platinum references
  Follow-up TODOs:
    - Create specs/004-platinum-tier/spec.md for Platinum feature
    - Update .gitignore in vault repo with secrets exclusion rules
    - Add FTE_ROLE to .env.example on both cloud and local
-->

# Personal AI Employee Constitution

## Core Principles

### I. Local-First & Privacy-Centric

All user data — emails, WhatsApp sessions, bank tokens, personal and
business documents — MUST remain on-device within the vault. No user
data may be transmitted to cloud storage, external APIs (except the
Claude API for reasoning), or third-party services unless the user
explicitly approves it within Platinum tier scope.

**Platinum exception**: In Platinum tier, vault markdown working copies
(task files, drafts, reports) MAY reside on the cloud VM for processing.
However, secrets, session files, authentication tokens, and credential
stores MUST remain exclusively on the local machine. The cloud VM
operates on sanitized markdown only — never raw credentials or session
data.

**Verification**: Code review MUST confirm no outbound network calls
carry user data. The only permitted external calls in Bronze–Gold are:
Claude API (prompts only, no vault file content in raw form), pip/npm
package installs, and git operations on the project repo (not the vault).
In Platinum, git sync of the vault is permitted but `.gitignore` MUST
exclude all secrets (see Section: Security).

**Rationale**: A personal AI employee handles the most private aspects
of a user's digital life. Trust requires that data never leaves the
device without explicit consent.

### II. Human-in-the-Loop (HITL) Safety

Actions are classified into three risk levels:

- **Routine** (auto-execute, log only): Read vault files, create/update
  markdown notes, move files between workflow folders (e.g., `Inbox` →
  `Needs_Action`), generate reports, run watchers.
- **Sensitive** (HITL gate required): Send emails/messages, post to
  social media, modify financial records, interact with external
  services (Odoo, banks). MUST write a proposal to `Pending_Approval/`
  and halt until the user moves the file to `Approved/`.
- **Critical** (HITL gate + confirmation log): Delete files permanently,
  execute payments, submit legal documents, modify authentication
  credentials. Same gate as Sensitive, plus a timestamped entry in
  `Logs/critical_actions.jsonl` that the user MUST acknowledge.

The system MUST NOT bypass the HITL gate under any circumstance,
including retry loops or Ralph Wiggum iterations.

**Platinum clarification**: In hybrid mode, the cloud agent MUST NOT
execute Sensitive or Critical actions. It drafts proposals and places
them in `Pending_Approval/<domain>/`. Only the local agent (with
`FTE_ROLE=local`) may approve and execute. This is a hard constraint,
not a configuration option.

**Rationale**: Blanket HITL on all actions defeats autonomy. Risk-based
tiers let routine work flow while protecting high-stakes decisions.

### III. Proactive Autonomy

The agent MUST watch for filesystem events via Watchdog and act without
constant user prompting. Task persistence uses the Ralph Wiggum loop:
retry until completion or `RALPH_MAX_ITERATIONS` (default: 15, set via
`.env`; hard cap: 20 — values above 20 MUST be silently clamped with a
warning log entry). On exhaustion, the agent MUST:
1. Log the failure to `Logs/ralph_exhausted.jsonl` with task context.
2. Create a `Needs_Action` file in the vault describing what stalled.
3. Stop retrying that task (no silent infinite loops).

The agent SHOULD surface what it did and why in `Logs/`, not ask
permission for Routine-level work.

**Rationale**: The value proposition of an AI FTE is 24/7 availability
and initiative — not a tool that waits to be told every step.

### IV. Modularity & Extensibility

The system MUST follow tier-based progression:

| Tier | Scope | Cloud allowed |
|------|-------|---------------|
| Bronze | Basic vault + 1 watcher + read/write | No |
| Silver | Multiple watchers + action execution + scheduling | No |
| Gold | Full integration (Odoo, social, CEO briefing) | No |
| Platinum | Cloud hybrid + 24/7 VM + Git sync (see Principle VII) | Yes (approved) |

Each tier builds incrementally. Implementing a higher tier MUST NOT
break functionality from lower tiers. A tier is complete only when all
its test scenarios pass.

**Action execution**: Silver tier uses direct Python function calls via
`action-executor` (`importlib` dynamic import from `src/actions/`) —
no HTTP server required. Full MCP/FastAPI servers are deferred to Gold
tier if needed for external integrations.

**Platinum operation**: Platinum tier adds a cloud VM agent that shares
the vault via git sync. The cloud agent handles Routine-level work
(read, triage, draft, reason) while the local agent retains authority
over Sensitive/Critical execution. See Principle VII for full
operational rules.

**Rationale**: Incremental delivery reduces risk, enables demo-ability
at every stage, and keeps the hackathon scope manageable.

### V. Cost-Efficiency Mindset

All design decisions MUST consider cost-per-task relative to a human
FTE. The target is 85–90% cost savings. Tier demos SHOULD include a
cost comparison table (e.g., "$0.02/task vs $15/hour human equivalent")
and emphasize 24/7 availability vs human 40 h/week limitations.

**Rationale**: The hackathon thesis is that AI employees are
economically superior for routine knowledge work.

### VI. Error Handling & Recovery

Every component (watcher, orchestrator, MCP server) MUST:
1. Catch all exceptions and log them to the component's own JSONL
   log file (e.g., `Logs/gmail.jsonl`, `Logs/orchestrator.jsonl`) with
   timestamp, component name, error message, and stack trace.
2. Restart automatically via PM2/supervisord on crash (max 5 restarts
   in 60 seconds before entering stopped state).
3. Never leave vault files in an inconsistent state — use write-to-temp
   then atomic rename for all file mutations.
4. On unrecoverable failure, create a `Needs_Action` file describing
   the failure for human review.

Orphaned `Pending_Approval/` files older than 48 hours MUST be flagged
in `Dashboard.md` as stale.

**Rationale**: An autonomous agent that fails silently is worse than no
agent. Every failure MUST be visible and recoverable.

### VII. Hybrid Cloud-Local Operation (Platinum)

Platinum tier introduces a two-agent architecture: a **cloud agent**
running on the Oracle Cloud VM (`FTE_CLOUD_HOST` env var; currently
141.145.146.17 — may change on stop/start without a reserved IP) and a
**local agent**
running on the user's laptop. Both share state exclusively through
git-synced vault folders.

#### 7.1 Agent Roles

| Capability | Cloud Agent (`FTE_ROLE=cloud`) | Local Agent (`FTE_ROLE=local`) |
|---|---|---|
| Read/triage vault files | Yes | Yes |
| Draft responses & reports | Yes | Yes |
| Reason & classify tasks | Yes | Yes |
| Execute Routine actions | Yes (vault file ops only) | Yes |
| Execute Sensitive actions | **NEVER** — draft only | Yes (with HITL gate) |
| Execute Critical actions | **NEVER** — draft only | Yes (with HITL gate + confirmation) |
| Send emails/messages | **NEVER** | Yes |
| Post to social media | **NEVER** | Yes |
| Execute payments | **NEVER** | Yes |
| Send WhatsApp messages | **NEVER** | Yes |
| Access .session files | **NEVER** | Yes |
| Access banking/payment tokens | **NEVER** | Yes |
| Modify Dashboard.md directly | **NEVER** — append to `/Updates/` | Yes (single-writer authority) |

The `FTE_ROLE` environment variable (`cloud` or `local`) MUST be set in
`.env` on each machine. The orchestrator, watchers, and action executor
MUST check `FTE_ROLE` before executing any action and refuse
Sensitive/Critical execution when `FTE_ROLE=cloud`.

#### 7.2 Inter-Agent Communication

All communication between cloud and local agents MUST be file-based via
the git-synced Obsidian vault. No direct network calls, APIs, SSH
tunnels, or message queues between agents.

**Vault folder structure for Platinum**:

```
Needs_Action/
  gmail/          # Gmail watcher drops files here
  whatsapp/       # WhatsApp watcher drops files here
  scheduler/      # Scheduled tasks land here
  manual/         # User-created tasks
In_Progress/
  cloud/          # Cloud agent's active work
  local/          # Local agent's active work
Pending_Approval/
  gmail/          # Email drafts awaiting approval
  social/         # Social media posts awaiting approval
  odoo/           # Financial actions awaiting approval
  general/        # Other actions awaiting approval
Updates/            # Cloud agent appends incremental updates here
Approved/           # User-approved actions ready for execution
Rejected/           # Local agent rejected drafts (with reason in frontmatter)
Done/               # Completed tasks (both agents move here)
```

#### 7.2.1 Rejection Flow

When the local agent rejects a draft from `Pending_Approval/<domain>/`:

1. Move the file to `Rejected/` with `status: rejected` and a
   `rejection_reason` field added to frontmatter.
2. Log the rejection to `Logs/actions.jsonl` with the correlation ID.
3. The cloud agent MAY pick up rejected files on its next cycle to
   re-draft (if the rejection reason is actionable) or escalate to
   `Needs_Action/manual/` for human re-specification.
4. Files in `Rejected/` older than 7 days without re-processing MUST
   be flagged in `Dashboard.md` as stale.

#### 7.3 Claim-by-Move Rule

To prevent both agents from processing the same task:

1. An agent MUST atomically move a file from `Needs_Action/<domain>/`
   to `In_Progress/<agent-name>/` before beginning work.
2. The move constitutes ownership — the other agent MUST ignore files
   in another agent's `In_Progress/` folder.
3. If a move fails (file already gone), the agent MUST assume the other
   agent claimed it and skip silently.
4. Git conflicts on claim moves MUST be resolved by keeping the first
   mover's claim (check commit timestamps).

#### 7.4 Single-Writer Authority

The **local agent** has single-writer authority on shared mutable state:

- `Dashboard.md` — only the local agent writes directly. The cloud
  agent MUST write incremental updates to `Updates/dashboard-update-
  <ISO-timestamp>.md` which the local agent merges on its next cycle.
- `Company_Handbook.md` — local-only modifications.
- `Logs/critical_actions.jsonl` — local-only writes.

The cloud agent has write authority on:
- Files within `In_Progress/cloud/`
- Files within `Updates/`
- Component-specific logs (`Logs/cloud-orchestrator.jsonl`, etc.)

#### 7.5 Correlation IDs

Every task that crosses the cloud-local boundary MUST carry a
correlation ID for audit trail:

- Format: `corr-<ISO-date>-<8-char-hex>` (e.g., `corr-2026-03-10-a1b2c3d4`)
- The originating agent generates the ID when creating the task file.
- The ID MUST appear in the file's YAML frontmatter (`correlation_id`
  field) and in every related JSONL log entry.
- The local agent MUST reference the same correlation ID when approving,
  executing, or completing the task.

#### 7.6 Git Sync Protocol

- Both agents run `git pull --rebase` before reading and `git add . &&
  git commit && git push` after writing.
- Sync frequency: configurable via `GIT_SYNC_INTERVAL_SECONDS` env var
  (default: 60 seconds).
- Merge conflicts MUST be resolved automatically where possible
  (claim-by-move prevents most conflicts). Unresolvable conflicts MUST
  be logged and a `Needs_Action` file created for human review.
- The vault git remote MUST be a private repository.

#### 7.7 Offline Tolerance

- If the cloud VM cannot reach git remote, it MUST continue local
  processing and queue commits for the next successful sync.
- If the local agent is offline (laptop closed), the cloud agent
  continues triaging and drafting. Sensitive/Critical items accumulate
  in `Pending_Approval/` until the local agent comes online.
- Neither agent may assume the other is online. All coordination is
  asynchronous via vault files.

#### 7.8 Safety Preservation

Platinum tier MUST preserve ALL safety mechanisms from Gold tier:

- HITL gates (Sensitive/Critical) — enforced by local agent only
- Risk-based routing (routine/sensitive/critical classification)
- Ralph Wiggum retries with max iteration caps
- Circuit breakers (`Logs/health.json`)
- Health monitoring for all external services
- No autonomous money, emotional, or legal actions by any agent
- `--dry-run` default for all external-facing actions

The cloud agent adds a **fourth safety layer**: it is structurally
incapable of executing irreversible actions because it lacks access to
credentials, session files, and the `--live` flag is disabled when
`FTE_ROLE=cloud`.

**Rationale**: Splitting responsibilities between cloud (always-on
triage and drafting) and local (approval and execution) achieves 24/7
coverage while maintaining the trust guarantees of local-first
operation. The user's laptop remains the single point of authority for
anything that affects the outside world.

## Standards & Constraints

### Tech Stack

Python 3.13+ | Claude Code 2.1.x (reasoning) | Obsidian v1.11.x+
(vault UI) | Playwright (browser automation) | Watchdog (filesystem) |
Action executor (direct function calls via `importlib`; Silver tier) |
MCP/FastAPI servers (Gold tier, if needed) | PM2/supervisord (process
management) | Git (vault sync; Platinum tier) | OCI CLI (VM management;
Platinum tier).

### Vault

- **Path**: `VAULT_PATH` env var, defaulting to
  `/home/safdarayub/Documents/AI_Employee_Vault` (local) or
  `/home/ubuntu/AI_Employee_Vault` (cloud VM).
- All file operations MUST use absolute paths resolved from
  `VAULT_PATH`. Log an error and abort if a relative path is detected.
- **File naming**: `kebab-case.md` for all vault files. No spaces, no
  uppercase in filenames.
- **Frontmatter**: Every vault markdown file MUST include YAML
  frontmatter with at minimum: `title`, `created`, `tier`, `status`.
  Platinum-tier files MUST additionally include `agent` (cloud|local)
  and `correlation_id`. These fields are optional in Bronze–Gold and
  MUST be omitted rather than set to empty strings.

### Needs_Action File Format

**Priority vocabulary**: The canonical frontmatter values are
`routine`, `sensitive`, and `critical`. These MUST be used in all
persisted `Needs_Action` files. Watchers MAY use an internal mapping
scale (e.g., low/medium/high for keyword matching) but MUST convert
to the canonical values before writing frontmatter.

```yaml
---
title: "<descriptive title>"
created: "YYYY-MM-DDTHH:MM:SS"
tier: bronze|silver|gold|platinum
source: "<watcher or component name>"
priority: routine|sensitive|critical
status: needs_action
agent: cloud|local            # Platinum only; omit in Bronze–Gold
correlation_id: "corr-..."    # Platinum only; omit in Bronze–Gold
---

## What happened
<description of the event or trigger>

## Suggested action
<what the agent recommends doing>

## Context
<relevant file paths, error details, or data references>
```

### Security

- No secrets in vault or git. Use `.env` + OS keychain.
- All external-facing actions (email, social, payments) MUST default to
  `--dry-run` mode. Live mode requires `--live` flag AND Sensitive/
  Critical HITL approval.
- API keys MUST be loaded from environment variables, never hardcoded.
- **Platinum secrets exclusion**: The vault `.gitignore` MUST include at
  minimum:
  ```
  .env
  *.session
  *.token
  *.key
  *.pem
  credentials/
  secrets/
  __pycache__/
  ```
  These patterns MUST NOT be removed or overridden. Any commit
  containing files matching these patterns MUST be rejected by a
  pre-commit hook.

### Logging & Auditability

All logs use JSON Lines (`.jsonl`) format in the `Logs/` vault folder:
- **Required fields**: `timestamp` (ISO 8601), `component`, `action`,
  `status` (success|failure|skipped), `detail`, `correlation_id`
  (Platinum: required for cross-agent tasks; Bronze–Gold: optional).
- **Agent field** (Platinum): `agent` (cloud|local) MUST be included
  in every log entry to identify which agent performed the action.
- **Retention**: Logs older than 30 days MAY be archived to
  `Logs/archive/` but MUST NOT be deleted without user approval.
- **Action log**: Every vault file create/update/move/delete MUST be
  logged to `Logs/actions.jsonl`.

### No User Data in Cloud (Bronze–Gold)

External cloud dependencies for *user data storage or transmission* are
prohibited in Bronze, Silver, and Gold tiers. The following are
permitted in all tiers: pip/npm package installs, Claude API calls
(prompts only), git operations on the project repo, and system updates.

**Platinum exception**: Vault markdown files (not secrets) are synced to
the cloud VM via git for processing. This is explicitly approved under
Principle VII constraints.

### Reproducibility

All watchers, orchestrators, and MCP servers MUST be daemonizable and
restartable. Each component MUST include a PM2 ecosystem config or
systemd unit file example.

## Development Workflow

- **Incremental delivery**: Implement one tier at a time. A tier MUST
  pass all its test scenarios before the next tier begins.
- **Testing rigor**: Each tier MUST include at least one end-to-end test
  scenario (e.g., drop file → watcher detects → `Needs_Action` created
  → Claude processes → result moved to `Done/`).
- **Commit discipline**: Commit after each completed task. Messages
  MUST follow format: `<tier>: <description>` (e.g.,
  `bronze: add inbox watcher with Needs_Action output`).

## Success Criteria

- [ ] Vault contains `Dashboard.md`, `Company_Handbook.md`, and
  tier-specific folders.
- [ ] At least one watcher creates `Needs_Action` files on events.
- [ ] Claude Code can read/write vault files via `VAULT_PATH`.
- [ ] HITL flow works: `Pending_Approval/` → move to `Approved/`
  triggers action.
- [ ] No unhandled exceptions after a 10-minute watcher test run.
- [ ] Each tier passes without breaking previous tier functionality.
- [ ] Gold tier produces Monday Morning CEO Briefing autonomously.
- [ ] **Platinum demo**: Cloud agent triages incoming Gmail, drafts a
  reply, places it in `Pending_Approval/gmail/`. Local agent comes
  online, reviews the draft, approves it (moves to `Approved/`), and
  the local agent sends the email. Full cycle tracked by correlation
  ID in logs. Works even if cloud or local was temporarily offline.

## Governance

- This constitution is the authoritative source for all project
  decisions. It supersedes conflicting guidance in other documents.
- **Amendments**: Any principle change MUST be documented with rationale
  and propagated to dependent templates via Sync Impact Report.
- **Versioning**: MAJOR.MINOR.PATCH — MAJOR for principle removals or
  redefinitions, MINOR for new principles or material expansions,
  PATCH for clarifications and wording fixes.
- **Compliance review**: Before merging any feature branch, verify
  tier boundaries, HITL gates, and local-first data constraints.
  Platinum branches MUST additionally verify: `FTE_ROLE` gating on all
  action executors, `.gitignore` coverage, and correlation ID presence.

**Version**: 1.3.1 | **Ratified**: 2026-02-24 | **Last Amended**: 2026-03-11
