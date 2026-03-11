# ADR-0011: Claim-by-Move Concurrency Control

- **Status:** Accepted
- **Date:** 2026-03-11
- **Feature:** 004-platinum-tier
- **Context:** When both agents are online simultaneously, they both scan `Needs_Action/` for new tasks. Without concurrency control, both could process the same email or task, resulting in duplicate drafts, duplicate replies, or conflicting outputs. We need a lightweight mechanism to ensure exactly-once processing without introducing external dependencies (databases, message brokers, distributed locks).

## Decision

Use **atomic file rename (`os.rename()`) as a claim mechanism**:

- **Claim protocol**: Before processing a file, the agent moves it from `Needs_Action/<domain>/` to `In_Progress/<role>/` (where role is `cloud` or `local`)
- **Atomicity guarantee**: `os.rename()` is atomic on POSIX when source and destination are on the same filesystem
- **Conflict detection**: If the file is already gone (`FileNotFoundError`), the agent assumes another agent claimed it and skips silently with a log entry
- **Git-level conflict**: If both agents claim in the same sync cycle (before either pushes), git conflict on push is resolved by first-committer-wins; the loser's sync detects the file is gone and skips
- **Completion**: After processing, claimed file moves to `Pending_Approval/<domain>/`, `Done/`, or `Rejected/`
- **Directory separation**: `In_Progress/cloud/` vs `In_Progress/local/` ensures files never collide between agents

## Consequences

### Positive

- **Zero external dependencies**: No databases, Redis, or distributed lock managers. Just filesystem operations already used throughout the project.
- **Self-healing**: Stale claims (agent crashes mid-processing) are visible as files stuck in `In_Progress/`. The stale detector (FR-035) can flag them.
- **Auditable**: Git history shows who moved what and when. Each claim is a commit.
- **Simple mental model**: "If the file is there, take it. If it's gone, someone else got it."

### Negative

- **Race window between git pull and rename**: An agent may see a file after `git pull` that was claimed by the other agent in between syncs. The rename will succeed locally but git push will conflict. Mitigated by first-committer-wins resolution.
- **Not truly distributed-safe**: Relies on git commit ordering, not distributed consensus. Theoretically two agents could both rename locally before either pushes. In practice, 60s sync interval makes this extremely unlikely.
- **Stuck files on crash**: If an agent claims a file (moves to `In_Progress/`) then crashes before completing, the file is orphaned. Requires manual or automated stale detection.

## Alternatives Considered

**Alternative A: Lock files (`.lock` sidecar per task)**
- Pros: Explicit ownership, can include lock holder metadata.
- Rejected: Risk of stale locks (agent crashes without releasing). Requires lock cleanup logic. Adds complexity without clear benefit over rename.

**Alternative B: Database-based locking (SQLite or Redis)**
- Pros: True atomic locking, rich query capabilities.
- Rejected: Violates constitution Principle VII.2 (file-based IPC only). Introduces external dependency. Both agents would need access to the same database, which conflicts with offline tolerance.

**Alternative C: Git LFS locking (`git lfs lock`)**
- Pros: Git-native, well-understood semantics.
- Rejected: Requires Git LFS installation, adds dependency. Designed for binary file contention, not task queue ownership. Overkill for markdown files.

## References

- Feature Spec: [spec.md](../../specs/004-platinum-tier/spec.md) — FR-009 to FR-011, US-4, SC-005
- Implementation Plan: [plan.md](../../specs/004-platinum-tier/plan.md) — Claim-by-Move Protocol diagram, `src/claim_move.py` design
- Research: [research.md](../../specs/004-platinum-tier/research.md) — R3: Claim-by-Move Concurrency Control
- Related ADRs: ADR-0003 (Vault Data Safety — atomic writes via `os.rename()`), ADR-0006 (Multi-Source Orchestration — filesystem queue)
- Related Constitution: Principle VII.3 (Claim-by-Move Rule)
