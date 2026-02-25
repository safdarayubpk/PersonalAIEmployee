# Research: Bronze Tier

**Feature**: 001-bronze-tier
**Date**: 2026-02-24

## R1: Watchdog Library — Best Practices for File Drop Detection

**Decision**: Use `watchdog.observers.Observer` with a custom `FileSystemEventHandler` subclass, filtering for `on_created` events only.

**Rationale**: Watchdog is the standard Python filesystem monitoring library. The `on_created` event fires when a file is fully written (on Linux with inotify). Filtering to `on_created` only (ignoring `on_modified`, `on_deleted`, `on_moved`) prevents duplicate processing and aligns with FR-004 (only new files trigger metadata creation).

**Alternatives considered**:
- `inotify` directly via `inotify_simple`: Lower-level, Linux-only, more code to write. Watchdog abstracts this.
- Polling via `os.listdir` loop: Wastes CPU, misses rapid drops, no event-driven architecture.
- `asyncio` + `aiofiles` + `watchfiles`: Over-engineered for Bronze tier single-watcher scope.

**Implementation notes**:
- Use a small debounce (0.5s) to handle editors that create temp files before the final file.
- Filter: only `is_file()` events, ignore directories (FR-004 acceptance scenario 4).
- Metadata filename: `dropped-{original_stem}-{timestamp}.md` (kebab-case per constitution).

## R2: PID Lock File — Preventing Concurrent Watchers

**Decision**: Write PID to `Logs/watcher.pid` on startup. On startup, check if file exists and if the PID is alive via `os.kill(pid, 0)`. If alive, exit with error. If stale (process dead), overwrite. Remove on clean `SIGTERM`/`SIGINT` via signal handler.

**Rationale**: Simple, no external dependencies, standard Unix pattern. FR-019 requires this exact behavior.

**Alternatives considered**:
- `fcntl.flock()` file locking: More robust but platform-specific and doesn't survive crashes cleanly.
- Named socket: Over-engineered for single-user Bronze tier.
- PM2 manages instance count: Defers to Silver tier (PM2 not required in Bronze).

## R3: Atomic File Writes — Preventing Partial Files

**Decision**: Write to a temp file (`{target}.tmp`) in the same directory, then `os.rename()` to the target path. This is atomic on POSIX filesystems.

**Rationale**: Constitution Principle VI mandates "write-to-temp then atomic rename for all file mutations." This prevents vault corruption if the watcher or setup script crashes mid-write.

**Alternatives considered**:
- Direct `open(path, 'w').write()`: Not atomic — crash mid-write leaves partial file.
- `tempfile.NamedTemporaryFile` in `/tmp`: Cross-device rename would fail (drop folder and vault may differ). Using same-directory temp avoids this.

## R4: YAML Frontmatter Generation

**Decision**: Use string formatting (f-strings) for frontmatter generation, not PyYAML's `dump()`. Frontmatter is simple key-value with no nested structures.

**Rationale**: PyYAML's `dump()` adds unnecessary complexity (quoting rules, sort_keys, default_flow_style) for 6 flat fields. f-string template is deterministic, readable, and produces exactly the format the constitution specifies.

**Alternatives considered**:
- `PyYAML.dump()`: Unpredictable quoting for values containing colons. Would need `default_flow_style=False` and manual tweaking.
- `python-frontmatter` library: Extra dependency for a trivial task.

## R5: Log Format Standardization — .log vs .jsonl

**Decision**: Standardize all log files to JSONL format (`.jsonl` extension) per constitution. Update vault-interact skill to reference `vault_operations.jsonl` instead of `vault_operations.log`.

**Rationale**: Constitution section "Logging & Auditability" states: "All logs use JSON Lines (.jsonl) format." The vault-interact skill was created before this review and used plain text. Aligning to JSONL enables machine-parseable logs, consistent tooling, and Dashboard.md generation from structured data.

**Files affected**:
- `.claude/skills/vault-interact/SKILL.md`: Change all references from `vault_operations.log` to `vault_operations.jsonl`, update log format description.
- `src/vault_helpers.py`: Implement `log_operation()` function outputting JSONL.
- `src/file_drop_watcher.py`: Use `vault_helpers.log_operation()` for all logging.

## R6: Watcher Startup — CLI Interface

**Decision**: `file_drop_watcher.py` accepts optional `--drop-folder` and `--vault-path` CLI arguments, falling back to environment variables (`DROP_FOLDER`, `VAULT_PATH`), then to defaults (`~/Desktop/DropForAI`, `/home/safdarayub/Documents/AI_Employee_Vault`).

**Rationale**: FR-004 specifies `DROP_FOLDER` env var with default. Adding CLI args provides flexibility for testing without modifying `.env`. Precedence: CLI > env var > default.

**Alternatives considered**:
- Config file (`.yaml` or `.ini`): Over-engineered for 2 settings.
- Environment variables only: Less convenient for quick testing.

## R7: Setup Script — Idempotent Initialization

**Decision**: `setup_vault.py` checks each folder/file individually. Creates missing items only. For `Dashboard.md` and `Company_Handbook.md`, checks existence before writing (never overwrites). Logs all actions to `vault_operations.jsonl`.

**Rationale**: FR-017 requires idempotent initialization. SC-001 tests that re-run preserves existing files byte-for-byte. Checking each item individually is simpler and more reliable than diff-based approaches.

**Vault folders created** (7): `Inbox/`, `Needs_Action/`, `Done/`, `Pending_Approval/`, `Approved/`, `Plans/`, `Logs/`
**Vault files created** (2): `Dashboard.md`, `Company_Handbook.md`
