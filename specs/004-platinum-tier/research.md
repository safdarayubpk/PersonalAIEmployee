# Research: Platinum Tier — Cloud-Local Hybrid Operation

**Feature**: 004-platinum-tier | **Date**: 2026-03-11 | **Status**: Complete

## R1: Git Sync Strategy for Two-Agent Vault

**Decision**: Use `git pull --rebase` + `git add .` + `git commit` + `git push` in a timed loop (default 60s interval).

**Rationale**: Rebase avoids merge commits, keeping history clean. The `.gitignore` ensures secrets are never staged. File-based IPC (not branch-based) means both agents work on the same branch (`main`), which is the simplest model.

**Alternatives considered**:
- Branch-per-agent with PR merge: Too complex for file-based delegation; introduces unnecessary GitHub API dependency.
- Rsync/scp: No audit trail, no conflict detection, no offline tolerance.
- Webhooks/polling GitHub API: Adds API rate limit concerns; git native push/pull is simpler.

**Key findings**:
- `os.rename()` is atomic on POSIX (same filesystem) — sufficient for claim-by-move.
- `git stash` before pull protects uncommitted changes during rebase.
- Push conflicts are resolved by retry: `pull --rebase` then `push` (up to 3 retries).
- Both agents writing to same folder is safe if file names don't collide (timestamp-based names handle this).

## R2: FTE_ROLE Enforcement Architecture

**Decision**: Enforce at action executor level (not just orchestrator) via a centralized `role_gate.py` module. Every component that can trigger external effects must call `enforce_role_gate()`.

**Rationale**: Constitution FR-008 explicitly requires enforcement "at the action executor level, not just the orchestrator, to prevent bypasses." A single-module approach ensures consistency and makes it impossible to forget the check.

**Alternatives considered**:
- Orchestrator-only gate: Violates FR-008. A bug in routing could bypass the gate.
- Decorator-based (@require_role): Clean but harder to test and debug. Simple function call is more explicit.
- Middleware in MCP server: Would work for MCP paths but not for direct function calls.

**Key findings**:
- `FTE_ROLE` is read from `os.environ` (loaded from `.env` at startup).
- Missing/invalid `FTE_ROLE` → fatal startup error (process refuses to start).
- Role is immutable for process lifetime — no runtime role switching.

## R3: Claim-by-Move Concurrency Control

**Decision**: Use `os.rename()` for atomic file move. First agent to successfully rename owns the file.

**Rationale**: `os.rename()` is atomic on POSIX when source and destination are on the same filesystem (true for vault). `FileNotFoundError` on failure means another agent already claimed it.

**Alternatives considered**:
- Lock files (`.lock` sidecar): Adds complexity, risk of stale locks.
- Database-based locking: Violates file-based IPC principle.
- Git-based locking (`git lfs lock`): Overkill, adds LFS dependency.

**Key findings**:
- Race condition window: Between `git pull` and `os.rename()`. In practice, sync interval (60s) makes simultaneous claims extremely unlikely.
- If both agents rename in the same cycle (before sync): git conflict on the commit. Resolution: first committer wins, second agent's sync detects file is gone and skips.
- Directory structure prevents collision: `In_Progress/cloud/` vs `In_Progress/local/`.

## R4: Gmail OAuth on Headless Cloud VM

**Decision**: Copy a read-only scoped `token.json` to cloud VM manually. Accept that token refresh may fail and require manual re-auth on local machine.

**Rationale**: Gmail OAuth2 token refresh works headlessly if the refresh token is valid. The risk is that Google revokes the refresh token (e.g., after 6 months of inactivity on the scope, or if user changes password). This is documented as a known risk with circuit breaker mitigation.

**Alternatives considered**:
- Service Account with domain-wide delegation: Requires Google Workspace admin (Safdar uses personal Gmail).
- App Password: Gmail deprecated app passwords for OAuth-only access.
- IMAP polling: Possible but loses Gmail API features (labels, threads, search).

**Key findings**:
- Read-only scope (`gmail.readonly`) is sufficient for cloud agent (it only reads and classifies — never sends).
- Token refresh is automatic via `google-auth` library when refresh token is present.
- On refresh failure: circuit breaker OPEN → `Needs_Action/manual/` file → user re-auths on local machine → copies new `token.json` to VM.
- **Risk level**: Medium. Mitigation adequate for hackathon demo. Production would need service account.

## R5: Correlation ID Format Alignment

**Decision**: Update from `corr-YYYYMMDD-HHMMSS-XXXX` (4 hex, current) to `corr-YYYY-MM-DD-XXXXXXXX` (8 hex, constitution spec).

**Rationale**: Constitution v1.3.1 Section 7.5 specifies `corr-<ISO-date>-<8-char-hex>`. The current code uses a different format. Aligning now prevents confusion and ensures cross-agent correlation works correctly.

**Alternatives considered**:
- Keep old format: Violates constitution. Would need to update constitution instead — more disruptive.
- UUID-based: Overkill for this scale. Constitution spec is specific.

**Key findings**:
- Backward compatibility: `is_valid_correlation_id()` will accept both old and new formats.
- `generate_correlation_id()` will only generate new format.
- Existing files with old format continue to work (no migration needed).

## R6: PM2 on E2.1.Micro Memory Constraints

**Decision**: Run 3 services on cloud VM (git-sync, gmail-watcher, scheduler). Omit WhatsApp watcher (requires `.session` files) and keep orchestrator lightweight.

**Rationale**: E2.1.Micro has 1GB RAM. PM2 itself uses ~30MB. Python processes use ~30-50MB each. 3 services + PM2 ≈ 170MB, well within limits. Adding a 4th (orchestrator) is feasible but should be monitored.

**Alternatives considered**:
- Run all 4 services: Risky on 1GB. OOM killer could terminate critical processes.
- Use systemd instead of PM2: Fewer features (no restart limits, no log management). PM2 is already in Gold-tier stack.
- Single monolithic process: Violates modularity. One crash takes everything down.

**Key findings**:
- PM2 restart limit (5 per 60s) prevents crash loops from consuming resources.
- `health.json` circuit breaker tracks service state.
- If A1.Flex (4 OCPU/24GB) becomes available, all services can run comfortably.

## R7: Dashboard Single-Writer Pattern

**Decision**: Cloud writes incremental files to `Updates/`. Local merges into `Dashboard.md`. Update files are deleted after merge.

**Rationale**: Prevents git merge conflicts on `Dashboard.md`. The local agent is the single writer, ensuring consistency. Cloud's updates are append-only files with timestamps — no conflict possible.

**Alternatives considered**:
- Both agents write to `Dashboard.md` with merge resolution: High conflict rate, complex resolution logic.
- Separate `Dashboard-cloud.md` and `Dashboard-local.md`: User has to check two files. Poor UX.
- Real-time sync via WebSocket: Violates file-based IPC constraint.

**Key findings**:
- Update file naming: `dashboard-update-YYYY-MM-DDTHH-MM-SS.md` ensures chronological ordering.
- Merge strategy: append to `## Cloud Updates` section in `Dashboard.md`.
- Local agent processes all accumulated updates on each cycle (handles offline periods).
