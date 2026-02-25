# Contract: Log File Formats

**Version**: 1.0
**Format**: JSON Lines (one JSON object per line, `.jsonl` extension)

## vault_operations.jsonl

Records every vault file mutation (write, append, move, create).

```json
{"timestamp": "2026-02-24T14:30:00", "component": "setup-vault", "action": "create_folder", "status": "success", "detail": "Created folder: Needs_Action/"}
{"timestamp": "2026-02-24T14:30:01", "component": "file-drop-watcher", "action": "write_file", "status": "success", "detail": "Created Needs_Action/dropped-report-20260224-143000.md"}
{"timestamp": "2026-02-24T14:31:00", "component": "vault-interact", "action": "move_file", "status": "success", "detail": "Moved Needs_Action/dropped-report-20260224-143000.md → Done/dropped-report-20260224-143000.md"}
```

## actions.jsonl

Records every processing action by the skill pipeline.

```json
{"timestamp": "2026-02-24T14:31:00", "component": "process-needs-action", "action": "classify", "file": "dropped-report-20260224-143000.md", "risk_level": "low", "status": "success", "detail": "Classified as routine per Company Handbook"}
{"timestamp": "2026-02-24T14:31:05", "component": "check-and-process-needs-action", "action": "process_file", "file": "dropped-report-20260224-143000.md", "risk_level": "low", "status": "done", "detail": "Routed to Done/"}
```

## errors.jsonl

Records errors with stack traces.

```json
{"timestamp": "2026-02-24T14:32:00", "component": "file-drop-watcher", "action": "create_metadata", "status": "failure", "detail": "Permission denied: Needs_Action/dropped-secret-20260224-143200.md", "error": "PermissionError", "traceback": "..."}
```

## Required Fields (all log files)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| timestamp | ISO 8601 string | yes | When the event occurred |
| component | string | yes | Source component |
| action | string | yes | What was attempted |
| status | enum | yes | `success` \| `failure` \| `skipped` |
| detail | string | yes | Human-readable description |

## Additional fields by log file

- **actions.jsonl**: `file` (string), `risk_level` (enum: `low`\|`high`)
- **errors.jsonl**: `error` (exception class name), `traceback` (string)
