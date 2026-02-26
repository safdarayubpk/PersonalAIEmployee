---
name: ralph-retry
description: Implements the Ralph Wiggum persistence loop — retries failed tasks with exponential backoff until success or max iterations. Use when a task fails and needs automatic retry (MCP call timeout, watcher error, file lock, network failure), when the user asks to "retry task", "keep trying", "persist until done", "ralph loop", "retry with backoff", or when another skill or orchestrator needs fault-tolerant execution. Also use as a wrapper around any unreliable operation that should be retried automatically.
---

# Ralph Retry

Ralph Wiggum persistence loop: wrap any fallible task in an exponential-backoff retry loop. Never infinite — always stops on success or max retries.

**Vault root**: `/home/safdarayub/Documents/AI_Employee_Vault`
(override via `VAULT_PATH` env var)

## Workflow

```
Receive task (callable + args)
       │
       ├── Attempt 1 → Execute task
       │     ├── Success → Log → Update Dashboard → Return result
       │     └── Failure → Log error → Calculate backoff
       │
       ├── Attempt 2 → Wait (backoff) → Execute task
       │     ├── Success → Log → Update Dashboard → Return result
       │     └── Failure → Log error → Calculate backoff
       │
       ├── ... (up to max_retries)
       │
       └── Max retries reached → Log final failure → Update Dashboard → Return error
```

## Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `max_retries` | 15 | 1–20 | Maximum retry attempts (hard cap: 20) |
| `backoff_base` | 2 | 1–5 | Base for exponential backoff in seconds |
| `backoff_max` | 300 | — | Maximum wait between retries (5 min cap) |
| `task_id` | auto | — | Identifier for logging (auto-generated if not provided) |
| `task_description` | required | — | Human-readable description for logs and dashboard |

**Backoff formula**: `min(backoff_base ^ attempt, backoff_max)` seconds

Example with defaults (base=2): 2s, 4s, 8s, 16s, 32s, 64s, 128s, 256s, 300s, 300s...

## Usage

### As a Python module

```python
from ralph_retry import ralph_loop

# Wrap any callable
result = ralph_loop(
    task=lambda: some_unreliable_function(),
    task_description="Send weekly report email",
    max_retries=10,
    backoff_base=2,
)
# result = {"success": True, "attempts": 3, "error": None, "result": <return value>}
```

### As a CLI tool

```bash
# Retry an MCP call
python .claude/skills/ralph-retry/scripts/ralph_retry.py \
  --command "python .claude/skills/mcp-caller/scripts/mcp_call.py --server email --method send_email --params '{...}' --live" \
  --description "Send weekly report email" \
  --max-retries 10 \
  --backoff-base 2

# Retry a watcher restart
python .claude/skills/ralph-retry/scripts/ralph_retry.py \
  --command "python src/file_drop_watcher.py" \
  --description "Restart file drop watcher" \
  --max-retries 5 \
  --backoff-base 3

# Custom vault path
python .claude/skills/ralph-retry/scripts/ralph_retry.py \
  --command "python some_task.py" \
  --description "Process batch" \
  --vault-path /custom/vault
```

## Step 1: Validate Parameters

1. Enforce hard cap: `max_retries = min(max_retries, 20)` — never exceed 20
2. Enforce backoff range: `backoff_base` must be 1–5
3. Generate `task_id` if not provided: `ralph-<YYYYMMDD-HHMMSS>-<4-char-uuid>`
4. Log start to `Logs/ralph.jsonl`

## Step 2: Execute Retry Loop

For each attempt (1 to max_retries):

1. Log attempt start with attempt number and task description
2. Execute the task (callable or subprocess)
3. **On success**:
   - Log success with attempt count and total elapsed time
   - Update Dashboard.md with success entry
   - Return result JSON
4. **On failure**:
   - Capture full error traceback
   - Log failure with error details, attempt number, next backoff delay
   - If attempt < max_retries: wait `min(backoff_base ^ attempt, backoff_max)` seconds
   - If attempt == max_retries: proceed to Step 3

## Step 3: Handle Final Failure

1. Log final failure with all attempt details
2. Update Dashboard.md with failure entry
3. Return error JSON

## Output Format

```json
{
  "success": true,
  "attempts": 3,
  "error": null,
  "task_id": "ralph-20260225-120000-a1b2",
  "task_description": "Send weekly report email",
  "total_elapsed_seconds": 14.5,
  "result": "<task return value or subprocess stdout>"
}
```

On failure:

```json
{
  "success": false,
  "attempts": 15,
  "error": "ConnectionError: Cannot connect to localhost:8001 after 15 attempts",
  "task_id": "ralph-20260225-120000-a1b2",
  "task_description": "Send weekly report email",
  "total_elapsed_seconds": 612.3,
  "result": null
}
```

## Logging

Append one JSON line per attempt to `Logs/ralph.jsonl`:

```json
{
  "timestamp": "2026-02-25T12:00:02",
  "component": "ralph-retry",
  "action": "attempt",
  "status": "failure",
  "task_id": "ralph-20260225-120000-a1b2",
  "task_description": "Send weekly report email",
  "attempt": 1,
  "max_retries": 15,
  "error": "ConnectionError: Cannot connect to localhost:8001",
  "traceback": "Traceback (most recent call last):\n  ...",
  "next_backoff_seconds": 2,
  "detail": "Attempt 1/15 failed, retrying in 2s"
}
```

## Dashboard Updates

Append to Dashboard.md Processing History on completion:

**On success**:
```markdown
### Ralph Retry — 2026-02-25T12:00:15

| Metric | Value |
|--------|-------|
| Task | Send weekly report email |
| Result | Success |
| Attempts | 3 / 15 |
| Total time | 14.5s |
```

**On failure**:
```markdown
### Ralph Retry — 2026-02-25T12:10:15

| Metric | Value |
|--------|-------|
| Task | Send weekly report email |
| Result | FAILED |
| Attempts | 15 / 15 (exhausted) |
| Total time | 612.3s |
| Last error | ConnectionError: Cannot connect to localhost:8001 |
```

## Safety Rules

1. **Hard cap at 20 retries** — `max_retries` silently clamped, never exceeds 20
2. **Backoff cap at 300s** — maximum 5 minutes between retries
3. **Never infinite loop** — always terminates on success or max retries
4. **Full traceback logging** — every failure logs complete error trace to `Logs/ralph.jsonl`
5. **No retry on specific errors** — immediately fail (no retry) on: `KeyboardInterrupt`, `SystemExit`, `PermissionError`, `PathViolationError`
6. **All vault writes scoped to vault root** — path validation on Dashboard and log writes
7. **No-deletion policy** — never delete logs or vault files on failure
8. **Subprocess timeout** — CLI mode enforces 60s timeout per attempt (configurable)

## Resources

### scripts/

- `ralph_retry.py` — CLI wrapper and importable Python module with `ralph_loop()` function
