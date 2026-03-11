# ADR-0009: File-Based IPC via Git-Synced Vault

- **Status:** Accepted
- **Date:** 2026-03-11
- **Feature:** 004-platinum-tier
- **Context:** Platinum tier introduces two agents (cloud VM + local laptop) that must coordinate task processing, approvals, and status updates. The agents may be offline at different times and must tolerate hours-long disconnection. We need an inter-agent communication mechanism that is asynchronous, auditable, conflict-resistant, and consistent with the existing Obsidian vault architecture.

## Decision

Use **git-synced vault folders** as the sole IPC mechanism between cloud and local agents:

- **Transport**: `git pull --rebase` + `git add . && git commit && git push` in a timed loop (default 60s via `GIT_SYNC_INTERVAL_SECONDS`)
- **Protocol**: Both agents work on the `main` branch of the same private GitHub repository (`safdarayubpk/PersonalAIEmployee`)
- **Message format**: Markdown files with YAML frontmatter flowing through vault workflow folders (`Needs_Action/` → `In_Progress/` → `Pending_Approval/` → `Approved/` → `Done/`)
- **Conflict resolution**: `git pull --rebase` + retry push (max 3 attempts). Unresolvable conflicts logged to `Logs/sync-conflicts.jsonl` and escalated via `Needs_Action/manual/`
- **Offline tolerance**: Commits queue locally when offline; all queued changes push on reconnection
- **No direct network IPC**: No APIs, SSH tunnels, WebSockets, or message queues between agents

## Consequences

### Positive

- **Offline-tolerant by design**: Git queues changes naturally. Neither agent needs to assume the other is online.
- **Full audit trail**: Every file change is a git commit with timestamp and author — complete history available via `git log`.
- **Reuses existing infrastructure**: The vault is already an Obsidian folder; git is already configured on both machines. No new services to install.
- **Human-readable state**: Anyone can inspect the current system state by browsing vault folders in Obsidian or a file manager.
- **Consistent with constitution**: Principle VII.2 mandates file-based communication; Principle I preserves local-first data sovereignty.

### Negative

- **60-second latency floor**: Changes are visible to the other agent only after the next sync cycle. Not suitable for real-time coordination (acceptable for this use case).
- **Git history bloat**: Frequent commits (every 60s) will grow the repo. May need periodic `git gc` or history squashing in the future.
- **Single-branch contention**: Both agents pushing to `main` increases push conflict likelihood (mitigated by rebase + retry).
- **No structured schema validation**: Files are plain markdown — schema enforcement relies on convention and frontmatter parsing, not a type system.

## Alternatives Considered

**Alternative A: Direct network API (REST/gRPC between agents)**
- Pros: Low latency, structured contracts, real-time updates.
- Rejected: Violates constitution Principle VII.2 (no direct network calls). Requires always-on network between agents. Fragile when either side is offline.

**Alternative B: Branch-per-agent with GitHub PR merge**
- Pros: Cleaner separation, PR-based review.
- Rejected: Introduces GitHub API dependency, PR approval latency, merge overhead. Overkill for file-based delegation where files don't conflict by design (domain subfolders + timestamp naming).

**Alternative C: Rsync/SCP file synchronization**
- Pros: Simple, no git overhead.
- Rejected: No audit trail, no conflict detection, no offline queuing. Cannot determine which changes are new.

## References

- Feature Spec: [spec.md](../../specs/004-platinum-tier/spec.md) — FR-001 to FR-004, US-2, SC-002, SC-009
- Implementation Plan: [plan.md](../../specs/004-platinum-tier/plan.md) — Git Sync Protocol Detail section
- Research: [research.md](../../specs/004-platinum-tier/research.md) — R1: Git Sync Strategy
- Related ADRs: ADR-0006 (Multi-Source Orchestration — filesystem-mediated queue, now extended with git sync)
- Related Constitution: Principle VII.2 (Inter-Agent Communication), VII.6 (Git Sync Protocol), VII.7 (Offline Tolerance)
