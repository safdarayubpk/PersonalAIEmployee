# CEO Briefing Format Reference

## Briefing Structure

The Monday Morning CEO Briefing contains 6 sections, each populated from a different data source:

| # | Section | Data Source | Fallback |
|---|---------|-------------|----------|
| 1 | Executive Summary | Aggregated from all sections | Always available |
| 2 | Revenue & Expenses | Odoo ERP via `odoo.financial_summary` | "Financial data unavailable" notice |
| 3 | Completed Tasks | `Done/` folder in vault | "0 tasks" if empty |
| 4 | Social Media Activity | `Logs/mcp_social.jsonl` | "0 posts" per platform |
| 5 | Bottlenecks | `Pending_Approval/` folder (items >24h) | "No stale items" |
| 6 | Proactive Suggestions | Auto-generated from data patterns | Always available |

## Output Location

```
AI_Employee_Vault/
└── Briefings/
    └── YYYY-MM-DD_Monday_Briefing.md
```

## Example Briefing

```markdown
---
generated: "2026-02-23T20:00:00"
period: "2026-02-17 to 2026-02-23"
data_sources: ["odoo", "vault_done", "social_logs", "pending_approval"]
incomplete: false
correlation_id: "corr-20260223-200000-a1b2"
---

# Monday Morning CEO Briefing

**Period**: 2026-02-17 to 2026-02-23
**Generated**: 2026-02-23T20:00:00

## Executive Summary

Weekly briefing for 2026-02-17 to 2026-02-23. 12 tasks completed, 5 social
media posts published.

## Revenue & Expenses

| Metric | Amount |
|--------|--------|
| Revenue | $45,000.00 |
| Expenses | $12,500.00 |
| Net Income | $32,500.00 |
| Receivables | $8,200.00 |
| Payables | $3,100.00 |

**Invoices**: 8 paid, 3 unpaid, 1 partial

## Completed Tasks

**Total this week**: 12

| Source | Count |
|--------|-------|
| gmail-watcher | 5 |
| file-drop-watcher | 4 |
| daily-scheduler | 2 |
| whatsapp-watcher | 1 |

## Social Media Activity

| Platform | Posts |
|----------|-------|
| Facebook | 2 |
| Instagram | 1 |
| Twitter/X | 2 |
| **Total** | **5** |

## Bottlenecks

| Task | Hours Waiting |
|------|---------------|
| pending-social-post-twitter-a1b2.md | 36.5h |

## Proactive Suggestions

- **Review 1 stale approval item** — some tasks have been waiting 24+ hours
```

## Graceful Degradation Example

When Odoo is unavailable (circuit breaker open), the Revenue & Expenses section shows:

```markdown
## Revenue & Expenses

> **Financial data unavailable** — Odoo service is degraded (circuit breaker
> open). Showing task and social media data only.
```

The briefing still generates with `incomplete: true` in the frontmatter, and the
Executive Summary notes the missing data.

## Scheduling

The briefing is scheduled via `config/schedules.json`:

```json
{
  "task_name": "weekly-ceo-briefing",
  "cron": "0 20 * * 0",
  "description": "Generate Monday Morning CEO Briefing",
  "action": "docs.generate_briefing"
}
```

This triggers every Sunday at 8:00 PM (Asia/Karachi timezone), creating a
`Needs_Action` file that routes to the documents MCP server.

## On-Demand Generation

```bash
claude "generate CEO briefing"
claude "generate CEO briefing from 2026-02-01 to 2026-02-28"
```
