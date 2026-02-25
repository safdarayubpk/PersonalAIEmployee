# ADR-0004: Bronze Tier Scope and Deferral Strategy

- **Status:** Accepted
- **Date:** 2026-02-24
- **Feature:** 001-bronze-tier

- **Context:** The Personal AI Employee project follows a four-tier progression (Bronze → Silver → Gold → Platinum) per constitution Principle IV. The Bronze tier must establish the foundational architecture while explicitly deferring higher-tier features. Several constitution mandates (Ralph Wiggum loop, `critical_actions.jsonl`, stale Pending_Approval detection, PM2 process management, MCP servers) apply to the overall system but need to be scoped to what's meaningful in Bronze. The key question is: where exactly is the Bronze boundary, and how do we defer features without violating constitution MUSTs?

## Decision

- **In scope for Bronze**: Vault setup (idempotent), single filesystem watcher, Claude Code skill integration (manual trigger), dry-run mode only, JSONL logging, PID lock, path validation
- **Explicitly deferred with justification**:
  - **Ralph Wiggum loop**: Bronze uses manual trigger only. The persistence loop requires scheduling infrastructure (Silver tier) to be meaningful. Implementing it without a scheduler would create an unused code path.
  - **`critical_actions.jsonl`**: Constitution requires this for critical actions that execute. In Bronze, dry-run mode (FR-018) prevents any action from executing — critical files route to `Pending_Approval/` with a proposal but never execute. The log would have zero entries. Implement in Silver when live mode becomes available.
  - **Stale Pending_Approval detection**: Constitution requires flagging orphaned files older than 48h. Bronze has no scheduled/automated runs to trigger staleness checks — only manual invocation. Implement in Silver alongside scheduling.
  - **MCP servers**: Constitution lists MCP as part of the tech stack for Silver tier. Bronze uses Claude Code's native tools directly via skills.
  - **Multiple watchers**: Bronze implements exactly one watcher (filesystem). Gmail, WhatsApp, calendar watchers are Silver/Gold scope.
  - **PM2 process management**: Bronze includes a PM2 ecosystem config file but does not require PM2 for operation. The watcher runs as a foreground process or simple background task. Full PM2 management is Silver scope.
- **Dry-run enforcement**: FR-018 makes this the default and only mode. No `--live` flag exists in Bronze. Even if a Needs_Action file requests sending an email, it routes to `Pending_Approval/` with a proposal — never executes.

## Consequences

### Positive

- Clear tier boundary prevents scope creep — Bronze delivers a complete, testable vertical slice (drop → watch → process → route → dashboard) in 8–12 hours
- Deferred features have explicit justification tied to constitution principles — not arbitrary omissions
- Dry-run-only enforcement eliminates entire categories of risk (accidental email sends, payments, data mutations)
- Manual trigger simplifies testing — no need to debug scheduling, loop timing, or concurrency issues
- Foundation is solid for Silver to build on: vault structure, JSONL logging, skill composition chain, and atomic writes all carry forward

### Negative

- The system is not autonomous in Bronze — requires human to type "check and process needs action" each time, which somewhat contradicts the "AI Employee" narrative
- Deferred constitution MUSTs (`critical_actions.jsonl`, stale detection) create technical debt that Silver must address
- No automated testing framework — manual E2E tests only, which don't scale to Silver's complexity
- PM2 config exists but is untested in Bronze — could have integration issues when Silver activates it

## Alternatives Considered

**Alternative A: Include Ralph Wiggum loop in Bronze**
- Pros: Demonstrates full autonomy, closer to the hackathon vision, exercises the persistence mechanism
- Cons: Requires a scheduler or timer to trigger the loop (adds complexity), loop without multiple input sources just re-checks one folder repeatedly, risk of infinite loops during development, debugging loop behavior adds hours to timeline
- Rejected: The loop's value comes from multiple event sources and scheduling — both Silver tier features. Without them, it's a `while True: sleep(60)` wrapper around a single check

**Alternative B: Include live mode with HITL gates in Bronze**
- Pros: Tests the full approval flow (Pending_Approval → Approved → execute), more realistic demo
- Cons: Requires actual external integrations (email, social media) or convincing mocks, introduces risk of accidental real actions, HITL gate testing is complex (file system watches on Approved/ folder), significantly expands scope beyond 8–12 hours
- Rejected: Dry-run mode provides the same routing logic without execution risk. Live mode is Gold tier scope.

**Alternative C: Broader Bronze scope (include MCP + scheduling)**
- Pros: More impressive demo, exercises more of the constitution's requirements
- Cons: MCP server setup, scheduling infrastructure, and multi-watcher coordination would push timeline to 20+ hours, introduces network/IPC complexity that violates the simplicity goal, risk of partial implementation across many features vs complete implementation of core features
- Rejected: Constitution Principle IV mandates incremental delivery — a complete Bronze is better than a half-finished Silver

## References

- Feature Spec: `specs/001-bronze-tier/spec.md` (Not in Scope section, FR-018)
- Implementation Plan: `specs/001-bronze-tier/plan.md` (Complexity Tracking — deferral table)
- Constitution: Principle II (HITL Safety — dry-run), Principle III (Proactive Autonomy — Ralph Wiggum), Principle IV (Modularity — tier progression)
- Related ADRs: ADR-0001 (watcher scope), ADR-0002 (manual trigger decision)
