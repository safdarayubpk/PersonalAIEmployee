---
name: odoo-connector
description: Connect to self-hosted Odoo 19 Community ERP via MCP server for invoice management, payment registration, financial summaries, and partner/contact lookups. Use when the user asks to "list invoices", "create invoice", "register payment", "financial summary", "check Odoo", "ERP data", "accounting", "revenue report", or when the orchestrator routes an Odoo-related task. Also triggers on phrases like "unpaid invoices", "customer list", "financial report", or "Odoo query". Read operations are routine (auto-execute); write operations are critical (HITL + confirmation log).
---

# Odoo Connector

Connect to self-hosted Odoo 19 Community ERP through the MCP Odoo server (`fte-odoo`). Read operations auto-execute; write operations require critical-level HITL approval.

**Vault root**: `/home/safdarayub/Documents/AI_Employee_Vault`
(override via `VAULT_PATH` env var)

## Dependencies

- Odoo 19 Community running on Docker (`localhost:8069`)
- `odoorpc` Python package (v0.10.1)
- MCP Odoo server registered: `fte-odoo` in `.claude/settings.json`
- Odoo credentials in `.env`: `ODOO_HOST`, `ODOO_PORT`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD`

## Available MCP Tools

| Tool | HITL | Description |
|------|------|-------------|
| `odoo.list_invoices` | Routine | List invoices, filter by payment state |
| `odoo.create_invoice` | Critical | Create customer invoice |
| `odoo.register_payment` | Critical | Register payment on invoice |
| `odoo.financial_summary` | Routine | Aggregate revenue/expenses for period |
| `odoo.list_partners` | Routine | List customers/contacts |

## Usage

### Via Claude Code

```
claude "list all unpaid invoices"
claude "create invoice for partner 5 with 2 items"
claude "show financial summary for March 2026"
claude "list all customers in Odoo"
```

## Safety Rules

1. **Write operations are critical** — require HITL approval + confirmation log
2. **Read operations are routine** — auto-execute, log only
3. **Connection errors trigger circuit breaker** — after 3 failures, Odoo marked degraded
4. **All queries logged** — `Logs/mcp_odoo.jsonl` with correlation IDs
5. **Credentials from env vars** — never stored in vault or committed

## Resources

### references/

- `odoo_setup.md` — Docker installation, database creation, Accounting module setup, environment variables, and Odoo model/field reference for `account.move`, `res.partner`, and `account.payment.register`
