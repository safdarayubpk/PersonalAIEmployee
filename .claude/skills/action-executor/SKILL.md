---
name: action-executor
description: Lightweight action executor with HITL gate and dry-run default. Executes actions (send_email, post_social, create_event, generate_report) as direct Python function calls — no HTTP servers needed. Use when the user asks to "send an email", "post to social media", "create a calendar event", "execute action", "run action", or when an action plan requires execution. Also triggers on phrases like "execute plan step", "run the action", "do the task", or when process-needs-action or central-orchestrator routes a task to execution. Replaces mcp-caller with zero external dependencies.
---

# Action Executor

Execute actions as direct Python function calls with HITL gate and dry-run safety. No HTTP servers, no FastAPI, no httpx — just functions behind a safety gate.

**Vault root**: `/home/safdarayub/Documents/AI_Employee_Vault`
(override via `VAULT_PATH` env var)

**Project root**: Auto-detected from script location
(override via `PROJECT_ROOT` env var)

## Dependencies

None (stdlib only). Action modules are imported directly.

## Exit Codes

- `0` — Success (action executed or dry-run completed)
- `1` — Failure (action not found, execution error)
- `2` — HITL blocked (approval required, pending file created)

## Decision Tree

```
Receive action request (category + action + params)
       │
       ├── 1. Validate action exists in registry
       │     ├── Not found → Log error → Abort
       │     └── Found → Continue
       │
       ├── 2. HITL gate check
       │     ├── Action is HITL-exempt (read-only/local) → Continue
       │     └── Action requires HITL
       │           ├── Approved plan in Approved/ folder? → Continue
       │           └── No approval → Route to Pending_Approval/ → Stop
       │
       ├── 3. Dry-run check
       │     ├── --live flag? → Execute function
       │     └── Default → Log what WOULD happen → Return dry-run result
       │
       └── 4. Execute and log
             ├── Success → Log to Logs/actions.jsonl → Return result
             └── Failure → Log error → Return error details
```

## Action Registry

Actions are defined in `config/actions.json`:

```json
{
  "actions": {
    "email.send_email": {
      "description": "Send an email",
      "hitl": true,
      "module": "actions.email",
      "function": "send_email"
    },
    "email.draft_email": {
      "description": "Create an email draft locally",
      "hitl": false,
      "module": "actions.email",
      "function": "draft_email"
    },
    "social.post_social": {
      "description": "Post to social media",
      "hitl": true,
      "module": "actions.social",
      "function": "post_social"
    },
    "calendar.create_event": {
      "description": "Create a calendar event",
      "hitl": true,
      "module": "actions.calendar",
      "function": "create_event"
    },
    "calendar.list_events": {
      "description": "List upcoming calendar events",
      "hitl": false,
      "module": "actions.calendar",
      "function": "list_events"
    },
    "documents.generate_report": {
      "description": "Generate a report document",
      "hitl": false,
      "module": "actions.documents",
      "function": "generate_report"
    }
  }
}
```

## Usage

### CLI

```bash
# Dry-run (default) — logs what would happen, never executes
python .claude/skills/action-executor/scripts/execute_action.py \
  --action email.send_email \
  --params '{"to": "user@example.com", "subject": "Report", "body": "..."}'

# Live mode — actually runs the function
python .claude/skills/action-executor/scripts/execute_action.py \
  --action email.send_email \
  --params '{"to": "user@example.com", "subject": "Report", "body": "..."}' \
  --live

# With explicit approval reference
python .claude/skills/action-executor/scripts/execute_action.py \
  --action social.post_social \
  --params '{"platform": "twitter", "content": "Hello world"}' \
  --approval-ref "Approved/plan-post-update-20260225.md" \
  --live

# List all registered actions
python .claude/skills/action-executor/scripts/execute_action.py --list
```

### As a Python module

```python
from execute_action import run_action

result = run_action(
    action="email.draft_email",
    params={"to": "user@example.com", "subject": "Weekly Report"},
)
# {"success": True, "dry_run": True, "detail": "DRY RUN: Would call email.draft_email"}
```

## Step 1: Validate Action

1. Load `config/actions.json` (create with defaults if missing)
2. Check that `--action` key exists in the registry
3. If not found, log error and list available actions

## Step 2: HITL Gate

**HITL-exempt** (safe to execute without approval):
- Read-only: `list_events`, `get_contacts`
- Local-only: `draft_email`, `generate_report`, `export_pdf`, `create_summary`

**HITL-required** (must have approval):
- External sends: `send_email`, `post_social`, `send_notification`
- State creation: `create_event`, `schedule_post`
- Financial: `create_invoice`, `process_payment`
- Destructive: `delete_event`, `revoke_access`

**Approval flow**:
1. Check `Approved/` folder for a plan file referencing this action
2. If `--approval-ref` provided, verify the file exists in `Approved/`
3. No approval → create pending file in `Pending_Approval/` → stop
4. Approved → proceed

## Step 3: Execute or Dry-Run

**Dry-run** (default):
- Log full request to `Logs/actions.jsonl`
- Return what WOULD happen — never call the function

**Live** (`--live`):
- Import the action module dynamically
- Call the function with params
- Return result
- Log request + result

## Step 4: Log Results

Append one JSON line per call to `Logs/actions.jsonl`:

```json
{
  "timestamp": "2026-02-25T12:00:00",
  "component": "action-executor",
  "action": "execute",
  "status": "success",
  "action_id": "email.send_email",
  "params": {"to": "user@example.com", "subject": "Report"},
  "dry_run": true,
  "hitl_check": "exempt",
  "request_id": "a1b2c3d4",
  "detail": "DRY RUN: Would call email.send_email"
}
```

## Adding New Actions

1. Create a Python module in `src/actions/` (e.g. `src/actions/email.py`):

```python
def send_email(to: str, subject: str, body: str, **kwargs) -> dict:
    """Send an email via Gmail API or SMTP."""
    # Implementation here (use gmail_poll.py's auth for Gmail)
    return {"status": "sent", "to": to, "subject": subject}

def draft_email(to: str, subject: str, body: str, **kwargs) -> dict:
    """Create a local email draft in Plans/."""
    # Write draft to vault
    return {"status": "drafted", "to": to}
```

2. Register in `config/actions.json`:

```json
{
  "email.send_email": {
    "description": "Send an email",
    "hitl": true,
    "module": "actions.email",
    "function": "send_email"
  }
}
```

3. Done — the executor discovers it automatically via the registry.

## Safety Rules

1. **Dry-run by default** — never execute unless `--live` flag is explicitly passed
2. **HITL gate mandatory** — every non-exempt action must have approval before live execution
3. **No credential logging** — redact sensitive fields (password, token, api_key) from logs
4. **No HTTP required** — direct function calls, no network layer
5. **Dynamic imports** — action modules loaded only when needed, isolated failures
6. **All vault writes scoped to vault root** — path validation on all file operations
7. **No-deletion policy** — failed actions create error logs, never delete files
8. **Idempotency keys** — unique request ID per execution for deduplication
9. **Log everything** — every attempt (dry-run or live) logged to `Logs/actions.jsonl`

## Resources

### scripts/

- `execute_action.py` — CLI tool and importable module with HITL gate, dry-run, and action registry

### references/

- `adding_actions.md` — Guide for creating new action modules and registering them
