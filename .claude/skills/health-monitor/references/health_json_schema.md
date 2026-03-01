# Health JSON Schema Reference

## File Location

```
AI_Employee_Vault/Logs/health.json
```

This file is updated by MCP servers via the circuit breaker (`src/circuit_breaker.py`) after every external service call.

## Schema

```json
{
  "services": [
    {
      "service": "gmail",
      "state": "healthy",
      "consecutive_failures": 0,
      "last_success": "2026-03-01T12:00:00",
      "last_failure": null,
      "last_failure_reason": null
    },
    {
      "service": "facebook",
      "state": "healthy",
      "consecutive_failures": 0,
      "last_success": "2026-03-01T11:30:00",
      "last_failure": null,
      "last_failure_reason": null
    },
    {
      "service": "instagram",
      "state": "degraded",
      "consecutive_failures": 3,
      "last_success": "2026-02-28T09:00:00",
      "last_failure": "2026-03-01T10:15:00",
      "last_failure_reason": "401 Unauthorized",
      "cooldown_until": "2026-03-01T10:20:00"
    },
    {
      "service": "twitter",
      "state": "healthy",
      "consecutive_failures": 0,
      "last_success": "2026-03-01T11:45:00",
      "last_failure": null,
      "last_failure_reason": null
    },
    {
      "service": "odoo",
      "state": "healthy",
      "consecutive_failures": 0,
      "last_success": "2026-03-01T12:00:00",
      "last_failure": null,
      "last_failure_reason": null
    }
  ],
  "updated": "2026-03-01T12:00:00"
}
```

## Service States

| State | Circuit Breaker | Description | Action |
|-------|----------------|-------------|--------|
| `healthy` | CLOSED | Normal operation, calls succeed | No action needed |
| `degraded` | OPEN | 3+ consecutive failures, in cooldown | Calls rejected, wait for cooldown |
| `recovering` | HALF-OPEN | Cooldown expired, testing one call | Next call determines if healthy or degraded |
| `down` | OPEN (non-retryable) | Auth failure or permanent error | Manual intervention required |

## Circuit Breaker Configuration

Defined in `src/circuit_breaker.py`:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `failure_threshold` | 3 | Consecutive failures before opening circuit |
| `cooldown_seconds` | 300 | Seconds to wait before half-open retry (5 min) |
| `non_retryable` | varies | Auth errors (401) skip cooldown, go straight to down |

## State Transitions

```
CLOSED (healthy)
    │
    ├── success → stay CLOSED
    │
    └── failure (3x) → OPEN (degraded)
                           │
                           ├── cooldown expires → HALF-OPEN (recovering)
                           │                         │
                           │                         ├── success → CLOSED (healthy)
                           │                         │
                           │                         └── failure → OPEN (degraded)
                           │
                           └── non-retryable error → OPEN (down)
                                                        │
                                                        └── manual reset required
```

## Per-Service Circuit Breakers

Each external service has its own independent circuit breaker:

- **gmail** — Email MCP server (`src/mcp/email_server.py`)
- **facebook** — Social MCP server (`src/mcp/social_server.py`)
- **instagram** — Social MCP server (`src/mcp/social_server.py`)
- **twitter** — Social MCP server (`src/mcp/social_server.py`)
- **odoo** — Odoo MCP server (`src/mcp/odoo_server.py`)

Social media platforms have separate circuits because one platform can be down while others are healthy.

## Reading Health Status

To check health in Python:

```python
import json
from pathlib import Path

vault = Path("/home/safdarayub/Documents/AI_Employee_Vault")
health_file = vault / "Logs" / "health.json"

if health_file.exists():
    health = json.loads(health_file.read_text())
    for svc in health["services"]:
        print(f"{svc['service']}: {svc['state']} (failures: {svc['consecutive_failures']})")
else:
    print("No health data — services have not been called yet")
```

## Dashboard Integration

The orchestrator reads `health.json` before routing tasks to MCP servers. If a service is degraded, tasks are queued for retry after cooldown.
