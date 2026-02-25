---
name: vault-interact
description: Safe, reusable vault file operations for the Personal AI Employee. Use when any skill or workflow needs to read, write, append, list, move, or create markdown files in the AI Employee Vault. Triggers on any vault file operation request, including phrases like "read vault file", "list inbox", "move to done", "write to vault", "update dashboard", or when another skill (e.g. process-needs-action) references vault_interact for file operations. All operations are scoped to the vault root and logged automatically.
---

# Vault Interact

Safe file operations for the AI Employee Vault. Every operation is scoped to the vault root, logged to `Logs/vault_operations.jsonl`, and never deletes files.

**Vault root**: `/home/safdarayub/Documents/AI_Employee_Vault`
(override via `VAULT_PATH` env var)

## Safety Rules

1. **Never delete files** — no rm, no unlink, no overwrite-with-empty
2. **Never operate outside vault root** — validate every path starts with vault root before executing; reject and log violation otherwise
3. **Log every operation** — append one JSON line to `Logs/vault_operations.jsonl`
4. **No silent failures** — if a file or folder does not exist, return a clear error message
5. **Use absolute paths internally** — resolve all paths against vault root

## Operations

### 1. Read File

Read the full content of any file in the vault.

**Input**: relative path from vault root (e.g. `Company_Handbook.md`, `Needs_Action/task-001.md`)
**Output**: file content as plain text

**Steps**:
1. Resolve absolute path: `{vault_root}/{relative_path}`
2. Validate path is within vault root
3. Check file exists — if not, return `Error: File not found: {relative_path}`
4. Read file content using Read tool
5. Log to `Logs/vault_operations.jsonl`: `{"timestamp": "ISO8601", "component": "vault-interact", "action": "read_file", "status": "success", "detail": "Read {relative_path}"}`
6. Return content as plain text (no extra markdown wrapping)

**Example**:
```
Input:  read Company_Handbook.md
Output: (full file content)
Log:    {"timestamp":"2026-02-24T14:30:00","component":"vault-interact","action":"read_file","status":"success","detail":"Read Company_Handbook.md"}
```

### 2. Write File

Write or overwrite a file with new content.

**Input**: relative path + content
**Output**: `Success: wrote {relative_path}`

**Steps**:
1. Resolve and validate absolute path within vault root
2. Create parent directories if they do not exist
3. Write content using Write tool
4. Log to `Logs/vault_operations.jsonl`: `{"timestamp": "ISO8601", "component": "vault-interact", "action": "write_file", "status": "success", "detail": "Wrote {relative_path} ({byte_count} bytes)"}`
5. Return confirmation

**Example**:
```
Input:  write Plans/plan-task-001.md with content "---\ntitle: Plan\n---\n## Action\nOrganize files"
Output: Success: wrote Plans/plan-task-001.md
Log:    {"timestamp":"2026-02-24T14:31:00","component":"vault-interact","action":"write_file","status":"success","detail":"Wrote Plans/plan-task-001.md (52 bytes)"}
```

### 3. Append to File

Append text to an existing file without overwriting.

**Input**: relative path + text to append
**Output**: `Success: appended to {relative_path}`

**Steps**:
1. Resolve and validate absolute path
2. Check file exists — if not, return `Error: File not found: {relative_path}` (use Write to create first)
3. Read current content
4. Write current content + newline + appended text
5. Log to `Logs/vault_operations.jsonl`: `{"timestamp": "ISO8601", "component": "vault-interact", "action": "append_file", "status": "success", "detail": "Appended to {relative_path} ({byte_count} bytes added)"}`
6. Return confirmation

**Example**:
```
Input:  append to Dashboard.md: "Processed 1 file at 14:32"
Output: Success: appended to Dashboard.md
Log:    {"timestamp":"2026-02-24T14:32:00","component":"vault-interact","action":"append_file","status":"success","detail":"Appended to Dashboard.md (30 bytes added)"}
```

### 4. List Files

List files in a vault folder with optional filter.

**Input**: folder path (relative to vault root) + optional extension filter (e.g. `.md`)
**Output**: bullet list of filenames

**Steps**:
1. Resolve and validate absolute folder path
2. Check folder exists — if not, return `Error: Folder not found: {folder_path}`
3. List files using Glob tool with pattern `{folder}/*` or `{folder}/*.md`
4. Log to `Logs/vault_operations.jsonl`: `{"timestamp": "ISO8601", "component": "vault-interact", "action": "list_files", "status": "success", "detail": "Listed {folder_path} (filter: {filter}, count: {n})"}`
5. Return as simple bullet list

**Example**:
```
Input:  list Needs_Action/ filter .md
Output:
- task-001.md
- task-002.md
- error-report.md
Log:    {"timestamp":"2026-02-24T14:33:00","component":"vault-interact","action":"list_files","status":"success","detail":"Listed Needs_Action/ (filter: .md, count: 3)"}
```

### 5. Move File

Move a file from one vault folder to another.

**Input**: source relative path + destination folder
**Output**: `Success: moved {filename} from {source_folder} to {dest_folder}`

**Steps**:
1. Resolve and validate both source and destination paths
2. Check source file exists — if not, return `Error: Source not found: {source_path}`
3. Create destination folder if it does not exist
4. Check destination does not already have a file with the same name — if it does, return `Error: File already exists at destination: {dest_path}` (do not overwrite silently)
5. Read source file content
6. Write content to destination path
7. Write empty-marker to source (rename source to `{filename}.moved` to preserve audit trail)
8. Log to `Logs/vault_operations.jsonl`: `{"timestamp": "ISO8601", "component": "vault-interact", "action": "move_file", "status": "success", "detail": "Moved {source_path} → {dest_folder}/{filename}"}`
9. Return confirmation

**Important**: Since files are never deleted, the "move" reads from source, writes to destination, and renames the source with a `.moved` suffix. Periodically clean `.moved` files manually.

**Example**:
```
Input:  move Needs_Action/task-001.md to Done
Output: Success: moved task-001.md from Needs_Action to Done
Log:    {"timestamp":"2026-02-24T14:34:00","component":"vault-interact","action":"move_file","status":"success","detail":"Moved Needs_Action/task-001.md → Done/task-001.md"}
```

### 6. Create File

Create a new empty markdown file with minimal frontmatter.

**Input**: relative path + title
**Output**: `Success: created {relative_path}`

**Steps**:
1. Resolve and validate absolute path
2. Check file does NOT exist — if it does, return `Error: File already exists: {relative_path}`
3. Create parent directories if needed
4. Write minimal content:
   ```markdown
   ---
   title: "{title}"
   created: "{ISO 8601 timestamp}"
   tier: bronze
   status: active
   ---
   ```
5. Log to `Logs/vault_operations.jsonl`: `{"timestamp": "ISO8601", "component": "vault-interact", "action": "create_file", "status": "success", "detail": "Created {relative_path}"}`
6. Return confirmation

**Example**:
```
Input:  create Inbox/new-task.md with title "New Task from Watcher"
Output: Success: created Inbox/new-task.md
Log:    {"timestamp":"2026-02-24T14:35:00","component":"vault-interact","action":"create_file","status":"success","detail":"Created Inbox/new-task.md"}
```

## Log Format

Every operation appends one JSON line to `Logs/vault_operations.jsonl`:

```json
{"timestamp": "2026-02-24T14:30:00", "component": "vault-interact", "action": "read_file", "status": "success", "detail": "Read Company_Handbook.md"}
```

**Required fields**: `timestamp` (ISO 8601), `component` (always `"vault-interact"`), `action`, `status` (`success`|`failure`|`skipped`), `detail`.

Create `Logs/` folder and log file automatically if they do not exist on first operation.

## Error Handling

- **Path outside vault root**: `Error: Path violation — {path} is outside vault root`
- **File not found**: `Error: File not found: {path}`
- **Folder not found**: `Error: Folder not found: {path}`
- **File already exists** (on create/move): `Error: File already exists: {path}`
- All errors are logged to `Logs/vault_operations.jsonl` with `"status": "failure"` and the error message in `detail`

## Tool Mapping

This skill uses Claude's native tools for all operations:

| Operation | Claude Tool |
|-----------|-------------|
| Read | Read tool |
| Write | Write tool |
| Append | Read tool → Write tool |
| List | Glob tool |
| Move | Read → Write → rename via Bash `mv` |
| Create | Write tool |
| Log | Read → Write (append pattern) |
