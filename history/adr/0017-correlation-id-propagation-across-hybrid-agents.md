# ADR-0017: Correlation ID Propagation Across Hybrid Agents

- **Status:** Accepted
- **Date:** 2026-03-12
- **Feature:** 004-platinum-tier
- **Context:** In a two-agent hybrid system (cloud + local), a single user request (e.g., incoming email) triggers actions across both agents over time. Without a shared identifier, tracing the lifecycle of a task from detection through drafting, approval, and execution becomes impossible. The system needs end-to-end observability across git-synced file delegation.

## Decision

Adopt a deterministic correlation ID format `corr-YYYY-MM-DD-XXXXXXXX` (8 hex chars) generated at the point of first detection (e.g., gmail-watcher). The ID is:

1. **Embedded in frontmatter** of every Needs_Action file at creation time
2. **Preserved through claim-by-move** — `claim_file()` and `complete_file()` in claim_move.py read the correlation_id from frontmatter before moving and include it in every JSONL log entry
3. **Propagated to action executor** — the action-executor receives and logs the correlation_id for dry-run and live execution entries
4. **Carried into Done/** — the final file retains the original correlation_id for audit
5. **Logged in actions.jsonl** — every log entry includes `correlation_id` field, enabling `grep corr-2026-03-12-d16b3470 Logs/actions.jsonl` to trace full lifecycle

## Consequences

### Positive

- Full audit trail from email arrival to send confirmation across two independent agents
- Simple text-based tracing — `grep` on a single JSONL file reconstructs the entire lifecycle
- No external tracing infrastructure (Jaeger, Zipkin) needed — fits E2.1.Micro constraints
- Frontmatter-based propagation works naturally with git sync (no database, no API)

### Negative

- Correlation ID is only as reliable as frontmatter parsing — malformed files lose traceability
- No automatic span/parent-child relationships — flat correlation only
- 8 hex chars (32 bits) has theoretical collision risk at scale, acceptable for single-user FTE

## Alternatives Considered

1. **UUID v4 per file**: More unique but longer, harder to type/grep. Rejected for ergonomics.
2. **External tracing (OpenTelemetry)**: Too heavy for E2.1.Micro, requires network-accessible collector. Rejected for resource constraints.
3. **Sequential integer IDs**: Simpler but no date context, harder to debug across days. Rejected.
4. **No correlation tracking**: Simplest but makes debugging multi-agent flows nearly impossible. Rejected.

## References

- Feature Spec: specs/004-platinum-tier/spec.md (FR-019, FR-040)
- Implementation Plan: specs/004-platinum-tier/plan.md
- Related ADRs: ADR-0003 (JSONL logging strategy), ADR-0009 (file-based IPC), ADR-0011 (claim-by-move)
- Constitution: Principle VII.5 (Correlation IDs)
- Live Demo: Correlation ID `corr-2026-03-12-d16b3470` traced through claim→draft→approve→send→Done
