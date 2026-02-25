<!--
  Sync Impact Report
  ==================
  Version change: 1.0.0 → 1.1.0
  Modified principles:
    - II. HITL Safety: added risk-level classification (routine/sensitive/critical)
    - III. Proactive Autonomy: loop default raised 10 → 25, env var named,
      exhaustion behavior defined
  Added sections:
    - Principle VI: Error Handling & Recovery
    - Structured logging standard (JSON lines, required fields)
    - Vault file conventions (naming, frontmatter, Needs_Action format)
  Removed sections: None
  Clarifications:
    - "No cloud" scoped to user data transmission (not package mgmt)
    - Redundant vault-path / dry-run / loop-limit mentions consolidated
  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ no changes needed
    - .specify/templates/spec-template.md ✅ no changes needed
    - .specify/templates/tasks-template.md ✅ no changes needed
  Follow-up TODOs: None
-->

# Personal AI Employee Constitution

## Core Principles

### I. Local-First & Privacy-Centric

All user data — emails, WhatsApp sessions, bank tokens, personal and
business documents — MUST remain on-device within the vault. No user
data may be transmitted to cloud storage, external APIs (except the
Claude API for reasoning), or third-party services unless the user
explicitly approves it within Platinum tier scope.

**Verification**: Code review MUST confirm no outbound network calls
carry user data. The only permitted external calls in Bronze–Gold are:
Claude API (prompts only, no vault file content in raw form), pip/npm
package installs, and git operations on the project repo (not the vault).

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

**Rationale**: Blanket HITL on all actions defeats autonomy. Risk-based
tiers let routine work flow while protecting high-stakes decisions.

### III. Proactive Autonomy

The agent MUST watch for filesystem events via Watchdog and act without
constant user prompting. Task persistence uses the Ralph Wiggum loop:
retry until completion or `RALPH_MAX_ITERATIONS` (default: 25, set via
`.env`). On exhaustion, the agent MUST:
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
| Silver | Multiple watchers + MCP servers + scheduling | No |
| Gold | Full integration (Odoo, social, CEO briefing) | No |
| Platinum | Cloud hybrid + 24/7 VM + Git sync | Yes (approved) |

Each tier builds incrementally. Implementing a higher tier MUST NOT
break functionality from lower tiers. A tier is complete only when all
its test scenarios pass.

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
1. Catch all exceptions and log them to `Logs/errors.jsonl` with
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

## Standards & Constraints

### Tech Stack

Python 3.13+ | Claude Code 2.1.x (reasoning) | Obsidian v1.11.x+
(vault UI) | Playwright (browser automation) | Watchdog (filesystem) |
MCP servers (actions) | PM2/supervisord (process management).

### Vault

- **Path**: `VAULT_PATH` env var, defaulting to
  `/home/safdarayub/Documents/AI_Employee_Vault`.
- All file operations MUST use absolute paths resolved from
  `VAULT_PATH`. Log an error and abort if a relative path is detected.
- **File naming**: `kebab-case.md` for all vault files. No spaces, no
  uppercase in filenames.
- **Frontmatter**: Every vault markdown file MUST include YAML
  frontmatter with at minimum: `title`, `created`, `tier`, `status`.

### Needs_Action File Format

```yaml
---
title: "<descriptive title>"
created: "YYYY-MM-DDTHH:MM:SS"
tier: bronze|silver|gold|platinum
source: "<watcher or component name>"
priority: routine|sensitive|critical
status: needs_action
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

### Logging & Auditability

All logs use JSON Lines (`.jsonl`) format in the `Logs/` vault folder:
- **Required fields**: `timestamp` (ISO 8601), `component`, `action`,
  `status` (success|failure|skipped), `detail`.
- **Retention**: Logs older than 30 days MAY be archived to
  `Logs/archive/` but MUST NOT be deleted without user approval.
- **Action log**: Every vault file create/update/move/delete MUST be
  logged to `Logs/actions.jsonl`.

### No User Data in Cloud (Bronze–Gold)

External cloud dependencies for *user data storage or transmission* are
prohibited in Bronze, Silver, and Gold tiers. The following are
permitted in all tiers: pip/npm package installs, Claude API calls
(prompts only), git operations on the project repo, and system updates.

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

**Version**: 1.1.0 | **Ratified**: 2026-02-24 | **Last Amended**: 2026-02-24
