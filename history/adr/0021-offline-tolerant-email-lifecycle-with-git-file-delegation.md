# ADR-0021: Offline-Tolerant Email Lifecycle with Git File Delegation

- **Status:** Accepted
- **Date:** 2026-03-12
- **Feature:** 004-platinum-tier
- **Context:** The core Platinum value proposition is that the AI employee continues working when the owner's laptop is off. This requires an end-to-end lifecycle where: (1) cloud detects events autonomously, (2) creates structured approval requests, (3) syncs to local via git, (4) local user reviews and approves, (5) local executes the real action. This lifecycle must tolerate hours or days of local offline time without losing work or creating duplicates.

## Decision

Implement a 7-stage file-based lifecycle using git as the transport layer:

1. **Detection** (cloud): Gmail watcher polls every 120s, creates `Needs_Action/gmail/*.md` with frontmatter (correlation_id, gmail_id, priority, source)
2. **Claim** (cloud): Orchestrator atomically moves file to `In_Progress/cloud/` via `os.rename()` (claim-by-move, ADR-0011)
3. **Draft** (cloud): Action executor runs `email.draft_email` in dry-run mode, orchestrator adds `tool: email.send` to frontmatter
4. **Stage** (cloud): `complete_file()` moves to `Pending_Approval/` with `status: pending_approval`
5. **Sync** (git): cloud-git-sync commits and pushes; local pulls on next sync cycle
6. **Approve** (local/user): User reviews file, moves to `Approved/` (manual or via Obsidian)
7. **Execute** (local): approval_watcher detects file, calls `email.send` via Gmail API, moves to `Done/` with `status: completed`, `executed_by: local`, `completed_at: <timestamp>`

**Key design properties:**
- Each stage transition is an atomic file move (no partial states)
- Correlation ID traces the entire lifecycle in `actions.jsonl`
- Git sync tolerates any offline duration — files queue until next sync
- No duplicate execution: claim-by-move prevents double-processing; approval_watcher processes each file exactly once

## Consequences

### Positive

- True offline tolerance: cloud queues work indefinitely via git
- Full audit trail: every stage logged with correlation ID
- Human oversight preserved: user must explicitly move file to Approved/
- Simple mental model: file location = current state (no database, no state machine)
- Verified in production: live demo sent real email with correlation ID `corr-2026-03-12-d16b3470`

### Negative

- Latency: minimum 60s git sync + 120s poll interval = 3+ minutes from email to draft visibility
- Manual approval step: user must `mv` or drag file in Obsidian (no one-click approve button)
- Git conflicts possible if both agents modify same file simultaneously (mitigated by role separation)
- Scale limit: git sync becomes slow with thousands of concurrent files (acceptable for single-user FTE)

## Alternatives Considered

1. **A2A direct messaging (Agent-to-Agent protocol)**: Lower latency but requires persistent network connection between cloud and local. Rejected for Phase 1 — planned for Phase 2.
2. **Webhook/API-based approval**: Requires exposing local machine to internet (security risk) or a relay service (complexity). Rejected.
3. **Email-based approval** (reply "APPROVED" to auto-forward): Novel but fragile, creates email loops, hard to debug. Rejected.
4. **Shared database (Supabase/Firebase)**: Real-time sync but adds external dependency, cost, and network requirement. Rejected for simplicity and offline tolerance.

## References

- Feature Spec: specs/004-platinum-tier/spec.md (SC-001 through SC-010)
- Constitution: Principle VII (Hybrid Cloud-Local Operation), Principle II (HITL Safety)
- Related ADRs: ADR-0009 (git-based IPC), ADR-0010 (role gating), ADR-0011 (claim-by-move), ADR-0012 (secrets isolation), ADR-0016 (Gmail token transfer), ADR-0017 (correlation ID), ADR-0020 (source-to-tool mapping)
- Live Demo: T047 — full lifecycle verified 2026-03-12 with real Gmail send
