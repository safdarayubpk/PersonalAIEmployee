# ADR-0013: Single-Writer Dashboard via Update Files

- **Status:** Accepted
- **Date:** 2026-03-11
- **Feature:** 004-platinum-tier
- **Context:** Both agents need to contribute to `Dashboard.md` (the user's primary situational awareness view). The cloud agent generates status updates (emails triaged, drafts created), and the local agent generates execution confirmations. If both write to `Dashboard.md` directly, every sync cycle risks a git merge conflict on the same file, corrupting the user's dashboard.

## Decision

Implement a **write-through update file pattern** with single-writer merge:

- **Cloud agent writes to `Updates/`**: Creates timestamped files (`Updates/dashboard-update-YYYY-MM-DDTHH-MM-SS.md`) containing incremental status information. Never modifies `Dashboard.md`, `Company_Handbook.md`, or `Logs/critical_actions.jsonl` directly (FR-012, FR-034).
- **Local agent merges from `Updates/`**: On each cycle, reads all files in `Updates/` in chronological order, appends content to a `## Cloud Updates` section in `Dashboard.md`, then deletes the processed update files (FR-013).
- **Same pattern extends to `Company_Handbook.md` and `Logs/critical_actions.jsonl`**: These are local-only write targets per constitution Section 7.4.
- **Accumulation-safe**: If local is offline for hours/days, update files accumulate without conflict. All are merged when local reconnects.

## Consequences

### Positive

- **Zero merge conflicts on Dashboard.md**: Only one agent writes to it. Update files have unique timestamp-based names — no filename collisions.
- **Offline-tolerant**: Cloud generates updates regardless of local state. Updates queue in `Updates/` until local processes them.
- **Chronological ordering preserved**: Timestamp-based filenames ensure updates merge in the correct order.
- **Auditable**: Each update file is a discrete commit in git history. The merge operation is also committed.

### Negative

- **Delayed visibility**: Cloud updates are not visible in `Dashboard.md` until the local agent merges them. During offline periods, the user must check `Updates/` manually (or wait for merge).
- **Update file accumulation**: Long offline periods generate many small files. Not a performance concern at this scale but could clutter the vault.
- **Delete-after-merge creates git deletions**: Processed update files are deleted, which generates git history for deleted files. Acceptable trade-off for keeping `Updates/` clean.

## Alternatives Considered

**Alternative A: Both agents write to `Dashboard.md` with git merge resolution**
- Pros: No intermediary files, immediate visibility.
- Rejected: High conflict rate on every sync cycle. Git's text merge is unreliable for structured markdown with sections. Requires complex custom merge drivers.

**Alternative B: Separate dashboards (`Dashboard-cloud.md` + `Dashboard-local.md`)**
- Pros: Zero conflicts, simple implementation.
- Rejected: Poor UX — user has to check two files. Violates single-pane-of-glass principle. Harder to get a unified picture of system state.

**Alternative C: CRDT-based collaborative editing**
- Pros: Conflict-free by design, real-time merge.
- Rejected: Massive implementation complexity. Requires CRDT library (Yjs, Automerge). Violates file-based IPC simplicity principle. Overkill for markdown append operations.

## References

- Feature Spec: [spec.md](../../specs/004-platinum-tier/spec.md) — FR-012, FR-013, FR-034, US-5
- Implementation Plan: [plan.md](../../specs/004-platinum-tier/plan.md) — `src/dashboard_merger.py` design
- Research: [research.md](../../specs/004-platinum-tier/research.md) — R7: Dashboard Single-Writer Pattern
- Related Constitution: Principle VII.4 (Single-Writer Authority)
