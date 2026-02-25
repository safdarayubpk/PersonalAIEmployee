# ADR-0001: Event-Driven File Detection Architecture

- **Status:** Accepted
- **Date:** 2026-02-24
- **Feature:** 001-bronze-tier

- **Context:** The Bronze tier requires a filesystem watcher that detects file drops in a designated folder (`~/Desktop/DropForAI`) and creates metadata markdown files in the vault's `Needs_Action/` directory. Constitution Principle III (Proactive Autonomy) mandates the agent watch for events without user prompting. The watcher must handle concurrent drops, ignore non-file events, prevent duplicate instances, and leave original files untouched per the constitution's no-deletion rule. This is the entry point for the entire processing pipeline — the architecture chosen here shapes how Silver tier's multiple watchers will work.

## Decision

- **Event library**: Watchdog (`watchdog.observers.Observer`) with custom `FileSystemEventHandler` subclass
- **Event filter**: `on_created` events only — ignore `on_modified`, `on_deleted`, `on_moved`
- **Debounce**: 0.5s delay to handle editors creating temp files before the final write
- **Output**: Metadata-only — watcher creates a `dropped-{stem}-{timestamp}.md` file in `Needs_Action/` referencing the original; original file is left untouched in the drop folder
- **Instance control**: PID lock file at `Logs/watcher.pid` with `os.kill(pid, 0)` liveness check; signal handler cleanup on `SIGTERM`/`SIGINT`
- **Configuration**: CLI args (`--drop-folder`, `--vault-path`) > env vars (`DROP_FOLDER`, `VAULT_PATH`) > defaults

## Consequences

### Positive

- Event-driven architecture aligns with constitution's Proactive Autonomy principle — zero CPU waste during idle periods
- Metadata-only approach preserves original files (no-deletion rule), keeps drop folder simple for the user, and avoids cross-device move issues
- PID lock prevents resource conflicts without external dependencies (no PM2 required in Bronze)
- Watchdog abstracts platform differences (inotify on Linux, FSEvents on macOS) — enables future cross-platform support
- Configuration precedence (CLI > env > default) supports both production use and quick testing

### Negative

- `on_created` may fire before a large file is fully written on some filesystems — 0.5s debounce mitigates but doesn't guarantee
- PID lock files can become stale after unclean shutdown (mitigated by liveness check)
- Watchdog is a runtime dependency that must be installed separately (vs stdlib polling)
- Single-watcher PID lock design must be rearchitected for Silver tier's multiple watchers

## Alternatives Considered

**Alternative A: Polling via `os.listdir()` loop**
- Pros: No external dependency, simple implementation
- Cons: Wastes CPU during idle periods, misses rapid sequential drops, no event-driven architecture, violates Proactive Autonomy spirit
- Rejected: Inferior to event-driven for a daemon that runs continuously

**Alternative B: Raw `inotify` via `inotify_simple`**
- Pros: No abstraction overhead, direct Linux kernel API, lightweight
- Cons: Linux-only (no macOS/Windows), more boilerplate code, no observer pattern
- Rejected: Watchdog provides the same inotify backend on Linux with cross-platform abstraction for free

**Alternative C: `asyncio` + `watchfiles` (Rust-backed)**
- Pros: Modern async architecture, potentially faster event handling, Rust performance
- Cons: Over-engineered for single-watcher Bronze scope, async adds complexity to signal handling and PID management
- Rejected: Complexity not justified for Bronze; could revisit for Silver's multiple watchers

## References

- Feature Spec: `specs/001-bronze-tier/spec.md` (FR-004, FR-005, FR-019)
- Implementation Plan: `specs/001-bronze-tier/plan.md` (D1, D5)
- Research: `specs/001-bronze-tier/research.md` (R1, R2, R6)
- Related ADRs: ADR-0003 (vault data safety — atomic writes apply to watcher output)
- Constitution: Principle III (Proactive Autonomy), Principle VI (Error Handling — PID lock)
