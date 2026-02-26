# Routing Decision Matrix

## By Source and Risk Level

| Source | Low Risk | Medium Risk | High Risk |
|--------|----------|-------------|-----------|
| **filesystem** | Done/ (auto) | Done/ (auto) | Pending_Approval/ |
| **gmail** | Done/ (auto) | MCP draft_email (dry-run) + Pending_Approval/ | Pending_Approval/ |
| **whatsapp** | Done/ (log only) | Pending_Approval/ | Pending_Approval/ |
| **scheduler** | Execute task locally | Execute or MCP | Pending_Approval/ |

## Risk Keywords by Category

### High Risk (always HITL)

| Category | Keywords |
|----------|----------|
| Financial | payment, invoice, transfer, bank, salary, billing |
| Legal | legal, contract, NDA, compliance, agreement |
| Destructive | delete, remove, revoke, terminate |
| Personal | password, credential, health, medical |

### Medium Risk (context-dependent)

| Category | Keywords |
|----------|----------|
| Communication | email, send, post, publish, reply, forward |
| External | API, webhook, external |
| Access | permission, admin |

### Low Risk (auto-process)

Everything else — file organization, report generation, note creation, summaries, status checks.

## Priority Queue Order

1. **High priority** — process first regardless of source
2. **Medium priority** — process second, FIFO within tier
3. **Low priority** — process last, FIFO within tier

## MCP Server Routing

| Source | Default MCP Server | Default Method | Requires Approval |
|--------|--------------------|----------------|-------------------|
| gmail | email | draft_email | No (draft) |
| gmail | email | send_email | Yes |
| whatsapp | — | — | N/A (no auto-reply) |
| scheduler | varies | varies | Depends on task |

## Error Handling

| Error Type | Action |
|------------|--------|
| File read error | Skip file, log error, continue batch |
| MCP call timeout | Log, mark as deferred, retry next run |
| Risk assessment error | Default to high risk (fail safe) |
| Dashboard write error | Log warning, continue (non-blocking) |
| Plan creation error | Log error, still route file |
