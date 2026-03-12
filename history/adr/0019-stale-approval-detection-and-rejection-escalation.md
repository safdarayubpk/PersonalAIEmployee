# ADR-0019: Stale Approval Detection and Rejection Escalation

- **Status:** Accepted
- **Date:** 2026-03-12
- **Feature:** 004-platinum-tier
- **Context:** In the Platinum hybrid model, files can sit in Pending_Approval/ indefinitely if the local user doesn't act. Similarly, rejected drafts in Rejected/ need an escalation path. Without detection and escalation, stale files accumulate silently, tasks are lost, and the system appears unresponsive to end users waiting for replies.

## Decision

Implement a two-part detection and escalation system:

1. **Stale detection** (`src/stale_detector.py`): Scans Pending_Approval/ (>48h) and Rejected/ (>7 days) by parsing frontmatter `created` timestamps. Returns structured results with file names, ages, and paths.

2. **Dashboard integration**: `update_dashboard_stale()` adds a `## Stale Items` section to Dashboard.md listing stale files with age indicators, or "No stale items detected" when clean.

3. **Rejection escalation** (`src/rejection_handler.py`):
   - `reject_file()` (local-only): Moves files from Pending_Approval/ to Rejected/ with updated frontmatter (`status: rejected`, `rejection_reason`, `rejected_at`)
   - `process_rejections()` (cloud-only): Escalates Rejected/ files to Needs_Action/manual/ for human review

4. **Thresholds**: 48 hours for pending approvals, 7 days for rejected items. Both configurable via function parameters.

## Consequences

### Positive

- Stale items are surfaced automatically in Dashboard.md — user never loses track
- Rejection workflow creates a clear audit trail (frontmatter updated with reason and timestamp)
- Role-gated operations prevent cloud from executing rejections and local from escalating
- Thresholds align with typical business response times (2 days for approvals, 1 week for rejections)

### Negative

- Detection relies on frontmatter `created` timestamp accuracy — if missing or malformed, files are skipped
- No automatic notification (email/push) for stale items — relies on user checking Dashboard
- Escalation to Needs_Action/manual/ may create re-processing loops if not handled carefully

## Alternatives Considered

1. **Auto-approve after timeout**: Too risky — violates HITL safety principle (Principle II). Rejected.
2. **Delete stale files after threshold**: Destructive, violates no-deletion policy (ADR-0003). Rejected.
3. **Email notification for stale items**: Requires Gmail send capability on cloud (violates draft-only). Rejected for now; could add as local-side notification in future.
4. **No stale detection**: Simplest but files accumulate silently. Rejected.

## References

- Feature Spec: specs/004-platinum-tier/spec.md (FR-031, FR-032)
- Constitution: Principle II (HITL Safety), Principle VII.4 (Single-writer dashboard)
- Related ADRs: ADR-0003 (no-deletion policy), ADR-0013 (dashboard single-writer)
- Files: src/stale_detector.py, src/rejection_handler.py
