---
name: health-monitor
description: Monitor circuit breaker states and external service health. Reads Logs/health.json and reports service status (healthy/degraded/down) for Gmail, Facebook, Instagram, Twitter, and Odoo. Use when the user asks to "check health", "service status", "health monitor", "circuit breaker status", "which services are up", "system health", or when the orchestrator needs to check service availability. Also triggers on phrases like "are services running", "health check", "degraded services", or "what's down".
---

# Health Monitor

Monitor external service health via circuit breaker state. Reads `Logs/health.json` and reports real-time status for all integrated services.

**Vault root**: `/home/safdarayub/Documents/AI_Employee_Vault`
(override via `VAULT_PATH` env var)

## Dependencies

- `src/circuit_breaker.py` (circuit breaker state machine)
- `Logs/health.json` (shared health state file)

## Monitored Services

| Service | Source | Circuit Breaker |
|---------|--------|-----------------|
| Gmail | email MCP server | Per-service |
| Facebook | social MCP server | Per-platform |
| Instagram | social MCP server | Per-platform |
| Twitter | social MCP server | Per-platform |
| Odoo | odoo MCP server | Per-service |

## Workflow

```
1. READ    → Load Logs/health.json
2. PARSE   → Extract state per service
3. REPORT  → Display health matrix
4. ALERT   → Flag degraded/down services with cooldown expiry times
```

## Usage

```
claude "check service health"
claude "which services are degraded?"
claude "health monitor report"
```

## Health States

| State | Circuit Breaker | Meaning |
|-------|----------------|---------|
| Healthy | CLOSED | Normal operation, calls go through |
| Degraded | OPEN | 3+ failures, in cooldown, calls rejected |
| Down | OPEN (non-retryable) | Auth failure or persistent error |

## Reading Health Status

Read `Logs/health.json` in the vault. Structure:

```json
{
  "services": [
    {
      "service": "odoo",
      "state": "healthy",
      "consecutive_failures": 0,
      "last_success": "2026-03-01T12:00:00"
    }
  ],
  "updated": "2026-03-01T12:00:00"
}
```

## Safety Rules

1. **Read-only** — this skill never modifies health state
2. **No external calls** — reads local health.json only
3. **Dashboard integration** — health status reflected in Dashboard.md

## Resources

### references/

- `health_json_schema.md` — Full `health.json` schema, circuit breaker state transitions (closed→open→half-open), per-service configuration, and Python example for reading health status
