# Bronze Tier Manual Test Plan

**Feature**: 001-bronze-tier
**Date**: 2026-02-25
**Prerequisites**: Python 3.13+, watchdog installed, vault initialized via `setup_vault.py`

---

## SC-001: Vault Initialization (Idempotent)

**Steps**:
1. Delete the vault folder (if safe to do so) or use a fresh `VAULT_PATH`
2. Run `python src/setup_vault.py`
3. Verify 7 folders exist: `Inbox/`, `Needs_Action/`, `Done/`, `Pending_Approval/`, `Approved/`, `Plans/`, `Logs/`
4. Verify 2 files exist: `Dashboard.md`, `Company_Handbook.md`
5. Run `python src/setup_vault.py` again
6. Verify no files overwritten (timestamps unchanged)
7. Check `Logs/vault_operations.jsonl` shows `"status": "skipped"` entries on second run

**Expected**: First run creates all items. Second run reports "0 folders and 0 files created".

**Pass criteria**: All 7 folders + 2 files exist. Re-run is idempotent.

---

## SC-002: Watcher File Detection (<5s)

**Steps**:
1. Start watcher: `python src/file_drop_watcher.py`
2. Drop a `.txt` file into `~/Desktop/DropForAI`
3. Check `Needs_Action/` within 5 seconds

**Expected**: A `dropped-{stem}-{timestamp}.md` file appears in `Needs_Action/` with:
- 6 YAML frontmatter fields: `title`, `created`, `tier`, `source`, `priority`, `status`
- 3 body sections: "What happened", "Suggested action", "Context"

**Pass criteria**: Metadata file appears within 5s with all fields valid.

---

## SC-003: Vault Read/Write Operations (6 operations)

**Steps**:
1. Ask Claude Code to read `Company_Handbook.md` — verify full content
2. Ask Claude Code to write `Inbox/test.md` with frontmatter — verify created
3. Ask Claude Code to append to `Dashboard.md` — verify text added
4. Ask Claude Code to list `Needs_Action/` — verify file list returned
5. Ask Claude Code to move `Inbox/test.md` to `Done` — verify at destination, source has `.moved` suffix
6. Ask Claude Code to create `Inbox/new.md` with title — verify frontmatter

**Expected**: All 6 operations succeed. Each logs to `Logs/vault_operations.jsonl`.

**Pass criteria**: All operations return expected output. JSONL log entries present.

---

## SC-004: Single-File E2E Processing (<60s)

**Steps**:
1. Ensure one file exists in `Needs_Action/` (drop a file via watcher or create manually)
2. Trigger `check-and-process-needs-action` in Claude Code
3. Time the processing

**Expected**:
- Plan file created in `Plans/`
- If routine: result in `Done/`, original moved with `.moved` suffix
- If sensitive/critical: proposal in `Pending_Approval/`
- Dashboard updated with processing summary
- Entry in `Logs/actions.jsonl`

**Pass criteria**: Complete processing within 60s. Correct routing based on risk level.

---

## SC-005: 5-File Batch Processing (<5min)

**Steps**:
1. Create 5 Needs_Action files: 3 routine, 1 sensitive, 1 critical
2. Trigger `check-and-process-needs-action` in Claude Code
3. Time the processing

**Expected**:
- 5 plans in `Plans/`
- 3 results in `Done/` (routine files)
- 2 proposals in `Pending_Approval/` (sensitive + critical)
- Dashboard shows: "Files processed: 5, Auto-executed: 3, Pending approval: 2"
- 5 entries in `Logs/actions.jsonl`

**Pass criteria**: All 5 files processed correctly within 5 minutes. Counts match.

---

## SC-006: 10-Minute Stability Test

**Steps**:
1. Start watcher: `python src/file_drop_watcher.py`
2. Over 10 minutes, drop 5+ files at varied intervals (every 1-3 minutes)
3. After each batch of drops, trigger `check-and-process-needs-action`
4. Monitor for exceptions in terminal and `Logs/errors.jsonl`

**Expected**:
- No unhandled exceptions
- Watcher remains responsive throughout
- Every Needs_Action file reaches `Done/` or `Pending_Approval/`
- No orphaned files (every file fully processed)

**Pass criteria**: 0 unhandled exceptions. All files processed. Watcher responsive after 10 minutes.

---

## SC-007: JSONL Mutation Logging

**Steps**:
1. Perform several vault operations (setup, watcher drops, processing)
2. Read `Logs/vault_operations.jsonl`
3. Verify each line is valid JSON with required fields

**Expected**: Every mutation logged with fields: `timestamp`, `component`, `action`, `status`, `detail`.

**Pass criteria**: All log entries are valid JSONL. Count matches mutations performed.

---

## SC-008: Path Violation Rejection

**Steps**:
1. Ask Claude Code to read `/etc/passwd` via vault-interact
2. Ask Claude Code to write `/tmp/outside.md` via vault-interact
3. Check `Logs/vault_operations.jsonl` for failure entries

**Expected**: Both operations rejected with "Path violation" error. No file access outside vault.

**Pass criteria**: Zero path violations succeed. Failure entries logged.

---

## SC-009: Dry-Run Enforcement

**Steps**:
1. Process a Needs_Action file with `priority: sensitive` (e.g., "send email")
2. Verify the file routes to `Pending_Approval/` with a proposal
3. Check that no email was actually sent (no external side effects)

**Expected**: Sensitive/critical actions create proposals only. No real execution occurs.

**Pass criteria**: No external side effects. All actions are dry-run only.
