# ADR-0003: Vault Data Safety and Logging Strategy

- **Status:** Accepted
- **Date:** 2026-02-24
- **Feature:** 001-bronze-tier

- **Context:** The vault at `/home/safdarayub/Documents/AI_Employee_Vault` is the single source of truth for all agent data. Every file mutation (write, append, move, create) must be safe against crashes, auditable, and scoped to prevent accidental operations outside the vault. Constitution Principle I (Local-First) requires all data stays on-device, Principle VI (Error Handling) mandates atomic writes and comprehensive logging, and the Logging & Auditability standard requires JSONL format. These constraints collectively define how every component interacts with the filesystem.

## Decision

- **Atomic writes**: All file mutations use write-to-temp (`{target}.tmp` in same directory) then `os.rename()` — atomic on POSIX filesystems per constitution Principle VI
- **No-deletion policy**: Files are never deleted. Move operations read source → write destination → rename source to `{filename}.moved`. Periodically clean `.moved` files manually
- **Path validation**: Every file operation resolves against `VAULT_PATH` (env var, default `/home/safdarayub/Documents/AI_Employee_Vault`). Operations targeting paths outside vault root are rejected with `Error: Path violation` and logged
- **Logging format**: All logs use JSON Lines (`.jsonl`) with 5 required fields: `timestamp` (ISO 8601), `component`, `action`, `status` (success|failure|skipped), `detail`
- **Log files**: Three separate JSONL files for different concerns:
  - `Logs/vault_operations.jsonl` — every vault file mutation
  - `Logs/actions.jsonl` — processing actions (triage, classification, routing)
  - `Logs/errors.jsonl` — errors with stack traces
- **Frontmatter**: All vault markdown files include YAML frontmatter with minimum fields: `title`, `created`, `tier`, `status`. Generated via f-strings (not PyYAML dump) for deterministic output

## Consequences

### Positive

- Atomic writes prevent corrupted vault files on crashes — critical for a daemon (watcher) that runs continuously
- No-deletion policy creates a complete audit trail — `.moved` files can be forensically examined if routing was wrong
- Path validation prevents accidental writes to system files or other user directories — defense-in-depth for an autonomous agent
- JSONL format enables machine-parseable log analysis, dashboard generation from structured data, and future integration with monitoring tools
- Three separate log files prevent mixing concerns — vault ops, processing logic, and errors each have dedicated streams
- f-string frontmatter avoids PyYAML's unpredictable quoting behavior for simple key-value data

### Negative

- Atomic writes via same-directory temp files leave `.tmp` artifacts on crashes (mitigated by cleanup on next startup)
- No-deletion policy causes disk space growth over time — `.moved` files accumulate and require manual cleanup
- Path validation adds overhead to every file operation (negligible for <100 vault files in Bronze)
- Three log files means three append operations per processing cycle — more I/O than a single unified log
- f-string frontmatter is rigid — adding nested YAML structures in future tiers would require switching to PyYAML

## Alternatives Considered

**Alternative A: Direct file writes (no atomic pattern)**
- Pros: Simpler code, fewer temp files, standard Python `open().write()` pattern
- Cons: Crash during write leaves partial/corrupted file in vault; violates constitution Principle VI explicitly
- Rejected: Constitution mandates atomic writes — non-negotiable

**Alternative B: Plain text logs (`.log` files)**
- Pros: Human-readable without tooling, simpler to implement (just string formatting), familiar format
- Cons: Not machine-parseable, inconsistent format across components, cannot generate Dashboard metrics from structured data, violates constitution Logging standard
- Rejected: Constitution mandates JSONL — and structured logs are strictly superior for an autonomous agent that needs to self-report

**Alternative C: SQLite database for logging**
- Pros: Queryable, supports aggregation for Dashboard metrics, single file, ACID transactions
- Cons: Not human-readable in Obsidian, binary file in markdown vault, adds dependency, over-engineered for Bronze's <100 files
- Rejected: Doesn't fit the Obsidian-native vault philosophy; could revisit for Platinum tier with thousands of log entries

**Alternative D: Soft-delete (mark files as deleted in frontmatter)**
- Pros: Files stay in original location, no `.moved` clutter, status tracked in metadata
- Cons: Deleted files still appear in Obsidian folder listings, confuses vault navigation, "move to Done/" workflow becomes unclear
- Rejected: Physical movement to `Done/`/`Pending_Approval/` folders provides clear visual workflow in Obsidian

## References

- Feature Spec: `specs/001-bronze-tier/spec.md` (FR-008, FR-012, FR-013, FR-016, FR-017)
- Implementation Plan: `specs/001-bronze-tier/plan.md` (D3, D4)
- Research: `specs/001-bronze-tier/research.md` (R3, R4, R5)
- Data Model: `specs/001-bronze-tier/data-model.md` (Log Entry entity)
- Contracts: `specs/001-bronze-tier/contracts/log-formats.md`
- Related ADRs: ADR-0001 (watcher uses atomic writes for Needs_Action files)
- Constitution: Principle I (Local-First), Principle VI (Error Handling), Logging & Auditability standard
