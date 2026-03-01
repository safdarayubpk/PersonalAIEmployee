# MCP Documents Server Tools Contract

**Server**: `fte-documents`
**Script**: `src/mcp/documents_server.py`
**Transport**: stdio

## Tools

### docs.generate_report

**HITL**: Routine (no approval needed)
**Description**: Generate a markdown report from vault data

**Input**:
```json
{
  "report_type": "string (required) — 'task_summary'|'social_summary'|'health_status'|'custom'",
  "period_days": "integer (optional, default: 7)",
  "title": "string (optional) — custom report title",
  "correlation_id": "string (optional)"
}
```

**Output**:
```json
{
  "status": "success",
  "tool": "docs.generate_report",
  "report_file": "/path/to/Plans/report-<type>-<timestamp>.md",
  "detail": "Report generated: <title>",
  "correlation_id": "<propagated>"
}
```

---

### docs.generate_briefing

**HITL**: Routine (no approval needed)
**Description**: Generate the Monday Morning CEO Briefing

**Input**:
```json
{
  "period_start": "string (optional) — YYYY-MM-DD (default: 7 days ago)",
  "period_end": "string (optional) — YYYY-MM-DD (default: today)",
  "correlation_id": "string (optional)"
}
```

**Output**:
```json
{
  "status": "success",
  "tool": "docs.generate_briefing",
  "briefing_file": "/path/to/Briefings/2026-03-01_Monday_Briefing.md",
  "data_sources": ["odoo", "vault_done", "social_logs", "pending_approval"],
  "incomplete": false,
  "sections": {
    "executive_summary": true,
    "revenue_expenses": true,
    "completed_tasks": true,
    "social_media": true,
    "bottlenecks": true,
    "suggestions": true
  },
  "correlation_id": "<propagated>"
}
```

**Output (partial — Odoo unavailable)**:
```json
{
  "status": "success",
  "tool": "docs.generate_briefing",
  "briefing_file": "/path/to/Briefings/2026-03-01_Monday_Briefing.md",
  "data_sources": ["vault_done", "social_logs", "pending_approval"],
  "incomplete": true,
  "unavailable_sources": ["odoo"],
  "sections": {
    "executive_summary": true,
    "revenue_expenses": false,
    "completed_tasks": true,
    "social_media": true,
    "bottlenecks": true,
    "suggestions": true
  },
  "correlation_id": "<propagated>"
}
```
