---
name: check-and-process-needs-action
description: Proactive Bronze-tier orchestrator that checks Needs_Action/ for pending .md files and processes them automatically. Use when the user asks to "check for pending tasks", "run the agent loop", "process inbox", "check needs action", or any variation of checking and handling pending vault work. This skill ties together vault_interact (file ops) and process-needs-action (triage logic) into a single autonomous run. Also use as the top-level entry point when a watcher or scheduler triggers a processing cycle.
---

# Check and Process Needs Action

Proactive orchestrator for the Bronze tier. Checks `Needs_Action/` for
pending `.md` files, processes up to 5 per run, routes results, and
updates the dashboard.

**Vault root**: `/home/safdarayub/Documents/AI_Employee_Vault`

## Dependencies

- **vault_interact** — all file operations (read, write, append, list, move, create)
- **process-needs-action** — per-file triage logic (risk classification, plan creation, routing)
- **Company_Handbook.md** — processing rules (falls back to safe defaults if missing)

## Workflow

```
Check Needs_Action/
       │
       ├── Empty? → Log "no pending actions" → Update Dashboard → Done
       │
       └── Files found?
              │
              ├── Count > 5? → Take first 5, log warning about remainder
              │
              └── For each file (up to 5):
                     │
                     ├── Call process-needs-action triage
                     │      │
                     │      ├── Low-risk → execute → move to Done/
                     │      └── High-risk → defer → move to Pending_Approval/
                     │
                     └── On error → log to Logs/errors.jsonl → continue next file
              │
              └── Update Dashboard.md with summary
```

## Step 1: Check for Pending Files

Use vault_interact to list `.md` files in `Needs_Action/`.

```
vault_interact: list Needs_Action/ filter .md
```

**If no files found**:
1. Append to `Dashboard.md`:
   ```
   - [YYYY-MM-DDTHH:MM:SS] No pending actions.
   ```
2. Log to `Logs/vault_operations.jsonl`: `{"timestamp": "ISO8601", "component": "check-and-process", "action": "check_needs_action", "status": "success", "detail": "Checked Needs_Action/ (count: 0)"}`
3. Stop. No further processing needed.

**If files found**:
1. Count the files.
2. If count > 5, take only the first 5 (alphabetical order). Log a warning:
   ```
   vault_interact: append to Logs/errors.jsonl
   {"timestamp": "ISO8601", "component": "check-and-process", "action": "batch_limit", "status": "skipped", "detail": "{total_count} files in Needs_Action/, processing first 5 only. Remaining {total_count - 5} deferred to next run."}
   ```
3. Proceed to Step 2 with the batch (up to 5 files).

## Step 2: Process Each File

For each file in the batch, follow this sequence:

### 2a. Read the file

```
vault_interact: read Needs_Action/{filename}
```

Parse the YAML frontmatter for `priority` field and body for action details.

### 2b. Load Company_Handbook.md rules

```
vault_interact: read Company_Handbook.md
```

If the file does not exist, use defaults:
- **Routine** (auto-execute): file organization, note creation, reports, summaries
- **Sensitive** (HITL gate): email, messages, social media, financial records
- **Critical** (HITL gate): payments, deletions, legal, credentials

### 2c. Classify and route

Apply process-needs-action triage logic:

**Low-risk (routine priority, no sensitive keywords)**:
1. Create plan: `vault_interact: write Plans/plan-{filename}`
2. Execute the suggested action (Bronze tier: create a result summary note)
3. Write result: `vault_interact: write Done/result-{filename}`
4. Move original: `vault_interact: move Needs_Action/{filename} to Done`
5. Track: increment `done_count`

**High-risk (sensitive/critical priority, or sensitive keywords, or unknown)**:
1. Create plan: `vault_interact: write Plans/plan-{filename}`
2. Write proposal with approval header: `vault_interact: write Pending_Approval/{filename}`
3. Move original: `vault_interact: move Needs_Action/{filename} to Done` (with status `deferred_to_approval`)
4. Track: increment `approval_count`

### 2d. Handle errors

If any operation fails for a file:
1. Log the error:
   ```
   vault_interact: append to Logs/errors.jsonl
   {"timestamp": "ISO8601", "component": "check-and-process", "action": "process_file", "status": "failure", "detail": "Error processing {filename}: {error_message}", "error": "{error_class}", "traceback": "..."}
   ```
2. Track: increment `error_count`
3. Skip to the next file. Do not halt the entire batch.

## Step 3: Update Dashboard

After all files are processed, append a summary to `Dashboard.md`:

```
vault_interact: append to Dashboard.md
```

**Format**:
```markdown
### Processing Run — YYYY-MM-DDTHH:MM:SS

| Metric | Count |
|--------|-------|
| Files processed | {done_count + approval_count} |
| Auto-executed (Done) | {done_count} |
| Pending approval | {approval_count} |
| Errors | {error_count} |
| Deferred to next run | {deferred_count} |
```

If there were errors, also append:
```markdown
⚠️ {error_count} error(s) occurred. See `Logs/errors.jsonl` for details.
```

## Examples

### Example 1: No files pending

```
> check and process needs action

vault_interact: list Needs_Action/ filter .md → (empty)
vault_interact: append to Dashboard.md → "- [2026-02-24T14:30:00] No pending actions."

Output: "No pending actions at 2026-02-24T14:30:00. Dashboard updated."
```

### Example 2: One low-risk file

```
> check and process needs action

vault_interact: list Needs_Action/ filter .md → ["organize-inbox.md"]
vault_interact: read Needs_Action/organize-inbox.md → (priority: routine, action: sort files)
vault_interact: read Company_Handbook.md → (routine actions allowed)
vault_interact: write Plans/plan-organize-inbox.md → (plan created)
vault_interact: write Done/result-organize-inbox.md → (result summary)
vault_interact: move Needs_Action/organize-inbox.md to Done
vault_interact: append to Dashboard.md → "Processed 1 file. Auto-executed: 1. Pending: 0."

Output: "Processed 1 file. organize-inbox.md → Done/. Dashboard updated."
```

### Example 3: Two files, mixed risk

```
> check and process needs action

vault_interact: list Needs_Action/ filter .md → ["sort-notes.md", "send-invoice.md"]

File 1: sort-notes.md (priority: routine) → low-risk
  vault_interact: write Plans/plan-sort-notes.md
  vault_interact: write Done/result-sort-notes.md
  vault_interact: move Needs_Action/sort-notes.md to Done

File 2: send-invoice.md (priority: sensitive) → high-risk
  vault_interact: write Plans/plan-send-invoice.md
  vault_interact: write Pending_Approval/send-invoice.md (with approval header)
  vault_interact: move Needs_Action/send-invoice.md to Done

vault_interact: append to Dashboard.md →
  "Processed 2 files. Auto-executed: 1. Pending approval: 1."

Output: "Processed 2 files. sort-notes.md → Done/. send-invoice.md → Pending_Approval/. Dashboard updated."
```

## Limits and Guards

- **Max 5 files per run** — prevents runaway processing; excess files wait for next run
- **No file deletion** — all vault_interact moves use `.moved` rename pattern
- **Error isolation** — one file's failure does not block the rest of the batch
- **Company_Handbook.md authority** — if handbook says "block", the file is high-risk regardless of frontmatter priority
- **Unknown priority defaults to high-risk** — safe by default
