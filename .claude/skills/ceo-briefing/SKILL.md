---
name: ceo-briefing
description: Generate the Monday Morning CEO Briefing aggregating Odoo financial data, completed tasks, social media activity, bottlenecks, and proactive suggestions. Use when the user asks to "generate CEO briefing", "Monday briefing", "weekly audit", "business summary", "weekly report", "CEO report", or when the scheduler triggers a weekly briefing. Also triggers on phrases like "executive summary", "weekly business review", "briefing report", or "how did the business do this week".
---

# CEO Briefing

Generate comprehensive weekly "Monday Morning CEO Briefing" via the documents MCP server. Aggregates data from 5 sources into a single executive report.

**Vault root**: `/home/safdarayub/Documents/AI_Employee_Vault`
(override via `VAULT_PATH` env var)

## Dependencies

- `src/mcp/documents_server.py` (MCP documents server)
- `src/mcp/odoo_server.py` (for financial data, optional — graceful degradation if unavailable)
- `Logs/mcp_social.jsonl` (social media activity logs)
- `Done/` folder (completed task files)
- `Pending_Approval/` folder (bottleneck detection)

## Data Sources

| Source | Section | Fallback |
|--------|---------|----------|
| Odoo ERP | Revenue & Expenses | "Financial data unavailable" notice |
| Done/ folder | Completed Tasks | Shows 0 tasks if empty |
| Logs/mcp_social.jsonl | Social Media Activity | Shows 0 posts per platform |
| Pending_Approval/ | Bottlenecks | "No stale items" |
| Analysis | Proactive Suggestions | Auto-generated from data |

## Workflow

```
1. INVOKE  → Call docs.generate_briefing via MCP
2. GATHER  → Aggregate from 5 data sources
3. HANDLE  → Graceful degradation for unavailable sources
4. WRITE   → Save to Briefings/YYYY-MM-DD_Monday_Briefing.md
5. RETURN  → Report file path, data sources used, completeness
```

## Usage

### On-demand briefing

```
claude "generate CEO briefing"
claude "weekly business summary"
claude "Monday morning briefing for last week"
```

### Scheduled briefing (via daily-scheduler)

The scheduler creates a `Needs_Action` file on Sunday 8 PM that routes to `docs.generate_briefing`:

```json
{
  "task_name": "weekly-ceo-briefing",
  "cron": "0 20 * * 0",
  "action": "docs.generate_briefing",
  "description": "Generate Monday Morning CEO Briefing"
}
```

### Custom date range

```
claude "generate CEO briefing from 2026-02-17 to 2026-02-23"
```

## Briefing Sections

1. **Executive Summary** — Overview with key metrics
2. **Revenue & Expenses** — From Odoo financial_summary (or unavailable notice)
3. **Completed Tasks** — Count and breakdown by source
4. **Social Media Activity** — Posts by platform (Facebook, Instagram, Twitter)
5. **Bottlenecks** — Stale items in Pending_Approval/ (>24h)
6. **Proactive Suggestions** — Data-driven recommendations

## Output

Generated briefing saved to: `Briefings/YYYY-MM-DD_Monday_Briefing.md`

Response includes:
- `briefing_file`: Path to generated file
- `data_sources`: List of sources used
- `incomplete`: Boolean — true if any source unavailable
- `unavailable_sources`: List of failed sources
- `sections`: Map of section names to availability

## Graceful Degradation

When Odoo is unavailable (circuit breaker open):
- Briefing generates with `incomplete: true`
- Revenue & Expenses section shows: "Financial data unavailable — Odoo service is degraded"
- All other sections populate normally
- Executive summary notes the missing data

## Safety Rules

1. **Read-only aggregation** — this skill only reads data, never modifies source data
2. **Atomic writes** — briefing file written via temp file + rename
3. **No financial actions** — reading Odoo data only, never creates invoices or payments
4. **Correlation ID propagation** — all log entries include correlation_id for traceability
5. **Circuit breaker respect** — checks health.json before querying Odoo

## Resources

### references/

- `briefing_format.md` — Briefing section structure, example output, graceful degradation examples, scheduling configuration, and on-demand generation
