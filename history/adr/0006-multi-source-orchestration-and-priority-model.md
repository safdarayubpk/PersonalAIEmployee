# ADR-0006: Multi-Source Orchestration and Priority Model

- **Status:** Accepted
- **Date:** 2026-02-26
- **Feature:** 002-silver-tier
- **Context:** Silver tier extends Bronze's single file-drop watcher to three input sources (filesystem, Gmail, WhatsApp) plus a scheduler. All sources must create standardized `Needs_Action/` files that a central orchestrator can process in priority order. The orchestrator must route tasks based on risk assessment and handle 10+ concurrent items without failure. Bronze had a single watcher and manual processing — Silver needs automated multi-source ingestion and intelligent routing.

## Decision

Use a **filesystem-mediated orchestration model** with centralized risk keywords and constitution-canonical priority vocabulary:

- **Watchers**: Each source (file-drop, Gmail, WhatsApp) runs independently and writes standardized Markdown files with YAML frontmatter to `Needs_Action/`. Filename format: `{source-prefix}-{slug}-{YYYYMMDD-HHMMSS}.md`.
- **Priority vocabulary**: Frontmatter uses constitution-canonical values `routine|sensitive|critical`. Watchers map internally (high-risk keywords → critical, medium-risk → sensitive, default → routine) before writing.
- **Risk keywords**: Centralized `config/risk-keywords.json` with `high` and `medium` arrays shared across all watchers.
- **Orchestrator**: `orchestrator.py` scans `Needs_Action/`, sorts by priority (`critical > sensitive > routine`), processes up to `--batch-size` files per run. Risk assessment routes: high-risk → Pending_Approval (HITL), medium-risk → dry-run action, low-risk → Done.
- **Atomic writes**: All file creation uses `.tmp` then `os.rename()` for crash safety (extending ADR-0003 pattern).

## Consequences

### Positive

- Loose coupling — watchers and orchestrator are fully independent processes; adding a new source requires only a new watcher script
- Debuggable — all intermediate state is visible as Markdown files in the vault (Obsidian-friendly)
- Priority consistency — single vocabulary across all components prevents routing errors
- Resilient — filesystem-based queue survives process restarts; no messages lost
- Constitution-compliant — HITL gate for high-risk items, no autonomous sensitive actions

### Negative

- No real-time processing — orchestrator runs in batches, not event-driven (latency up to batch interval)
- Filesystem polling overhead — orchestrator must scan directory each run (acceptable for <50 files)
- No deduplication — same Gmail/WhatsApp message could create duplicate files if watcher restarts (mitigated by ID tracking in watcher state)
- Risk keyword maintenance — shared JSON requires manual updates; no learning/adaptation

## Alternatives Considered

### Alternative A: In-Memory Message Queue

Use Python `queue.Queue` or `asyncio.Queue` with watchers and orchestrator in the same process.

- **Pros**: Real-time processing, no filesystem overhead, simple priority queue
- **Cons**: All messages lost on crash, no intermediate state visible in Obsidian, monolithic process (one watcher crash kills all), no persistence
- **Why rejected**: Violates vault-as-source-of-truth principle. No crash recovery. Bronze established filesystem-based pattern that works well.

### Alternative B: External Message Broker (Redis/RabbitMQ)

Use Redis Pub/Sub or RabbitMQ for watcher → orchestrator communication.

- **Pros**: Real-time, battle-tested, built-in priority queues, deduplication support
- **Cons**: External dependency (violates "no external cloud dependencies before Platinum"), complex setup for hackathon, overkill for single-user local system
- **Why rejected**: Constitution principle of local-first simplicity. No external services until Platinum tier.

### Alternative C: SQLite Task Queue

Use SQLite database as a persistent task queue with priority columns.

- **Pros**: ACID guarantees, SQL queries for filtering/sorting, efficient for large volumes
- **Cons**: Not Obsidian-readable, breaks vault-as-single-source-of-truth pattern, adds database dependency, harder for hackathon participants to inspect/debug
- **Why rejected**: Vault visibility is a core product feature. Markdown files are the canonical data format per constitution.

## References

- Feature Spec: `specs/002-silver-tier/spec.md` (FR-001, FR-002, FR-010, FR-016)
- Implementation Plan: `specs/002-silver-tier/plan.md` (Phase 2: Gmail Watcher, Phase 4: WhatsApp Watcher, Phase 5: Orchestrator)
- Data Model: `specs/002-silver-tier/data-model.md` (Entity 1: Needs_Action File, Entity 6: Orchestrator Run Summary)
- Constitution: `.specify/memory/constitution.md` (Priority vocabulary, Needs_Action File Format)
- Related ADRs: ADR-0001 (Event-Driven File Detection — Bronze watcher pattern extended), ADR-0003 (Vault Data Safety — atomic write pattern reused)
- Research: `specs/002-silver-tier/research.md` (R-002: Priority Vocabulary, R-004: Risk Keyword Centralization)
