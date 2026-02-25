---
name: process-needs-action
description: Process Needs_Action markdown files in the AI Employee Vault. Use when the user asks to process, handle, or triage pending tasks from the Needs_Action/ folder. This skill reads each .md file in Needs_Action/, classifies risk level, creates a plan in Plans/, executes or routes to Pending_Approval/, logs actions, and updates Dashboard.md. Triggers on phrases like "process needs action", "handle pending tasks", "triage inbox", or "run needs action processor".
---

# Process Needs Action

Scan `Needs_Action/` in the vault, triage each file by risk level, plan and execute (or defer), then log and update the dashboard.

**Vault root**: Resolve from `VAULT_PATH` env var, default `/home/safdarayub/Documents/AI_Employee_Vault`.

**Dependency**: This skill uses `vault_interact` for all file operations. If `vault_interact` is not available, fall back to Claude's native Read/Write/Glob tools scoped to the vault path.

## Workflow

Processing Needs_Action files involves these steps:

1. Load rules from Company_Handbook.md
2. List .md files in Needs_Action/
3. For each file: read, classify, plan, execute or defer
4. Log every action to Logs/actions.jsonl
5. Update Dashboard.md with results

## Step 1: Load Rules

Read `Company_Handbook.md` from vault root. Extract:
- Allowed routine actions (auto-executable)
- Sensitive/critical action keywords requiring HITL approval
- Any domain-specific processing rules

If `Company_Handbook.md` does not exist, use these defaults:
- **Routine**: file organization, note creation, report generation, data summarization
- **Sensitive**: sending messages, modifying financial data, external API calls
- **Critical**: deleting files, executing payments, modifying credentials

## Step 2: List Needs_Action Files

Use vault_interact (or Glob) to list all `.md` files in `Needs_Action/`.

If the folder is empty or missing, log "No Needs_Action files found" and stop.

## Step 3: Process Each File

For each `.md` file in `Needs_Action/`:

### 3a. Read the file

Parse YAML frontmatter for: `title`, `source`, `priority`, `status`.
Read the body sections: "What happened", "Suggested action", "Context".

### 3b. Classify risk level

Determine risk from frontmatter `priority` field and body content:

| Priority field | Body keywords | Classification |
|---|---|---|
| `routine` | file, note, report, summary, organize | **Low-risk** → auto-execute |
| `sensitive` | email, message, post, invoice, payment | **High-risk** → HITL gate |
| `critical` | delete, payment, legal, credential | **High-risk** → HITL gate |
| missing/unknown | — | **High-risk** (safe default) |

Cross-check against Company_Handbook.md rules loaded in Step 1.

### 3c. Create plan

Ensure `Plans/` folder exists (create if missing via vault_interact or mkdir).

Write a plan file at `Plans/plan-<original-filename>`:

```markdown
---
title: "Plan: <original title>"
created: "<ISO 8601 timestamp>"
source_file: "Needs_Action/<original-filename>"
risk_level: low|high
status: planned
---

## Action plan
<describe what will be done based on the suggested action>

## Risk assessment
- Classification: <low-risk|high-risk>
- Reason: <why this classification>

## Expected outcome
<what the result should look like>
```

### 3d. Execute or defer

**Low-risk → execute dummy action + move to Done/**

1. Perform the action described in the plan (for Bronze tier: create a result note in `Done/` summarizing what was done).
2. Move the original file from `Needs_Action/` to `Done/`.
3. Update the plan file status to `completed`.

Example result file at `Done/result-<original-filename>`:

```markdown
---
title: "Result: <original title>"
created: "<ISO 8601 timestamp>"
source_file: "Needs_Action/<original-filename>"
status: done
---

## Action taken
<description of what was executed>

## Result
<outcome summary>
```

**High-risk → write to Pending_Approval/**

1. Copy the original file to `Pending_Approval/` with a proposal header added.
2. Move the original from `Needs_Action/` to `Done/` with status `deferred_to_approval`.
3. Update the plan file status to `pending_approval`.

Proposal header to prepend:

```markdown
## ⚠️ Approval required

**Risk level**: <sensitive|critical>
**Proposed action**: <what will happen if approved>
**Source**: Needs_Action/<original-filename>

Move this file to Approved/ to authorize execution.

---
```

## Step 4: Log actions

Append a JSON line to `Logs/actions.jsonl` for each file processed:

```json
{"timestamp": "<ISO 8601>", "component": "process-needs-action", "action": "process_file", "file": "<filename>", "risk_level": "<low|high>", "status": "<done|pending_approval>", "detail": "<brief description>"}
```

Create `Logs/` folder if it does not exist.

## Step 5: Update Dashboard

**IMPORTANT**: Skip this step when invoked by `check-and-process-needs-action`. The orchestrator handles the dashboard update itself using the summary metrics format from `contracts/dashboard-format.md`. Only execute Step 5 when `process-needs-action` is run standalone (directly by the user).

When run standalone, append a summary to `Dashboard.md` in vault root using the contract format:

```markdown
### Processing Run — YYYY-MM-DDTHH:MM:SS

| Metric | Count |
|--------|-------|
| Files processed | N |
| Auto-executed (Done) | N |
| Pending approval | N |
| Errors | N |
| Deferred to next run | N |
```

If no files were found:

```markdown
- [YYYY-MM-DDTHH:MM:SS] No pending actions.
```

## Error handling

- If a file cannot be read, log the error and skip to the next file.
- If vault_interact is unavailable, fall back to native file tools.
- Never leave files in an inconsistent state — complete the move or roll back.
- On any unrecoverable error, create a `Needs_Action/error-<timestamp>.md` describing the failure.

## References

- **Vault conventions and Needs_Action format**: See [vault-conventions.md](references/vault-conventions.md)
