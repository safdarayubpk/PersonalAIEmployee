# Adding New Actions

## Overview

Actions are plain Python functions registered in `config/actions.json`. No HTTP servers, no frameworks — just functions behind an HITL gate.

## Step 1: Create the Module

Create a Python file in `src/actions/`:

```
src/
└── actions/
    ├── __init__.py      # Empty, makes it a package
    ├── email.py         # Email actions
    ├── social.py        # Social media actions
    ├── calendar.py      # Calendar actions
    └── documents.py     # Document generation
```

## Step 2: Write the Function

Every action function must:
- Accept `**kwargs` for forward compatibility
- Return a dict with at least `{"status": "..."}`
- Raise an exception on failure (caught by executor)

```python
# src/actions/email.py

def send_email(to: str, subject: str, body: str, **kwargs) -> dict:
    """Send an email via Gmail API."""
    # Use gmail_poll.py's OAuth2 auth
    # ...implementation...
    return {"status": "sent", "to": to, "subject": subject}

def draft_email(to: str, subject: str, body: str, **kwargs) -> dict:
    """Create a local draft in Plans/."""
    # Write draft markdown to vault
    return {"status": "drafted", "to": to}
```

## Step 3: Register in config/actions.json

```json
{
  "actions": {
    "email.send_email": {
      "description": "Send an email",
      "hitl": true,
      "module": "actions.email",
      "function": "send_email"
    }
  }
}
```

**Fields**:

| Field | Required | Description |
|-------|----------|-------------|
| `description` | Yes | What the action does |
| `hitl` | Yes | `true` if HITL approval required |
| `module` | Yes | Python module path (relative to `src/`) |
| `function` | Yes | Function name in the module |

## HITL Rules

Set `hitl: true` for:
- Sends data externally (email, social, notifications)
- Creates external state (calendar events)
- Involves money (invoices, payments)
- Destructive operations (deletes, revokes)

Set `hitl: false` for:
- Read-only (list, get, search)
- Local-only (draft, generate, export)
- Vault-only operations

## Example: Adding Odoo Integration (Gold Tier)

```python
# src/actions/odoo.py

def create_invoice(customer: str, amount: float, description: str, **kwargs) -> dict:
    """Create an invoice in Odoo."""
    # xmlrpc call to Odoo
    return {"status": "created", "invoice_id": 12345}
```

```json
{
  "odoo.create_invoice": {
    "description": "Create an Odoo invoice",
    "hitl": true,
    "module": "actions.odoo",
    "function": "create_invoice"
  }
}
```

## Testing

```bash
# Dry-run (always safe)
python .claude/skills/action-executor/scripts/execute_action.py \
  --action email.draft_email --params '{"to": "test@example.com", "subject": "Test"}'

# List all actions
python .claude/skills/action-executor/scripts/execute_action.py --list
```
