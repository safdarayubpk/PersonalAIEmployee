"""MCP Documents Server — report and briefing generation.

Tools: docs.generate_report (routine), docs.generate_briefing (routine)
Transport: stdio
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP
from base_server import (
    get_vault_path, log_tool_call, make_response,
    check_service_available,
)

server = FastMCP("fte-documents")


@server.tool()
def docs_generate_report(report_type: str, period_days: int = 7,
                         title: str = "",
                         correlation_id: str = "") -> dict:
    """Generate a markdown report from vault data.

    Args:
        report_type: 'task_summary', 'social_summary', 'health_status', or 'custom'
        period_days: Number of days to cover (default: 7)
        title: Custom report title (optional)
        correlation_id: Correlation ID for audit tracing
    """
    vault = get_vault_path()
    ts = datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")

    if not title:
        title = f"{report_type.replace('_', ' ').title()} Report"

    content = f"""---
title: "{title}"
created: "{ts_str}"
type: report
report_type: {report_type}
period_days: {period_days}
correlation_id: "{correlation_id}"
---

## {title}

**Generated**: {ts_str}
**Period**: Last {period_days} days

"""

    if report_type == "task_summary":
        done_dir = vault / "Done"
        if done_dir.exists():
            files = list(done_dir.glob("*.md"))
            content += f"### Completed Tasks: {len(files)}\n\n"
            for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
                content += f"- {f.stem}\n"
        else:
            content += "### No completed tasks found\n"

    elif report_type == "health_status":
        health_file = vault / "Logs" / "health.json"
        if health_file.exists():
            health = json.loads(health_file.read_text())
            content += "### Service Health\n\n| Service | State | Last Success |\n|---------|-------|--------------|\n"
            for svc in health.get("services", []):
                content += f"| {svc['service']} | {svc['state']} | {svc.get('last_success', 'N/A')} |\n"
        else:
            content += "### No health data available\n"

    elif report_type == "social_summary":
        content += "### Social Media Activity\n\n*(See social.weekly_summary tool for detailed stats)*\n"

    else:
        content += "### Custom Report\n\n*(Add custom content as needed)*\n"

    report_path = vault / "Plans" / f"report-{report_type}-{ts.strftime('%Y%m%d-%H%M%S')}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = report_path.with_suffix(report_path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.rename(tmp, report_path)

    log_tool_call("documents", "docs.generate_report", "success", "success",
                  f"Report generated: {title}", correlation_id,
                  result={"report_file": str(report_path)})

    return make_response("success", "docs.generate_report", correlation_id,
                         report_file=str(report_path),
                         detail=f"Report generated: {title}")


@server.tool()
def docs_generate_briefing(period_start: str = "", period_end: str = "",
                           correlation_id: str = "") -> dict:
    """Generate the Monday Morning CEO Briefing with 6 sections.

    Args:
        period_start: Start date YYYY-MM-DD (default: 7 days ago)
        period_end: End date YYYY-MM-DD (default: today)
        correlation_id: Correlation ID for audit tracing
    """
    vault = get_vault_path()
    ts = datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
    today = date.today()
    start = period_start or (today - timedelta(days=7)).isoformat()
    end = period_end or today.isoformat()

    data_sources = []
    incomplete = False
    unavailable_sources = []
    sections = {
        "executive_summary": True,
        "revenue_expenses": False,
        "completed_tasks": True,
        "social_media": True,
        "bottlenecks": True,
        "suggestions": True,
    }

    # --- Section 1: Financial Data from Odoo ---
    financial_section = ""
    odoo_available, _ = check_service_available("odoo")
    if odoo_available:
        try:
            # Try to get Odoo data via direct import
            from odoo_server import odoo_financial_summary
            fin_result = odoo_financial_summary(period_start=start, period_end=end,
                                                 correlation_id=correlation_id)
            if fin_result.get("status") == "success":
                data_sources.append("odoo")
                sections["revenue_expenses"] = True
                financial_section = f"""## Revenue & Expenses

| Metric | Amount |
|--------|--------|
| Revenue | ${fin_result.get('revenue', 0):,.2f} |
| Expenses | ${fin_result.get('expenses', 0):,.2f} |
| Net Income | ${fin_result.get('net_income', 0):,.2f} |
| Receivables | ${fin_result.get('receivables', 0):,.2f} |
| Payables | ${fin_result.get('payables', 0):,.2f} |

**Invoices**: {fin_result.get('invoice_count', {}).get('paid', 0)} paid, {fin_result.get('invoice_count', {}).get('unpaid', 0)} unpaid, {fin_result.get('invoice_count', {}).get('partial', 0)} partial
"""
            else:
                raise Exception(fin_result.get("detail", "Unknown error"))
        except Exception:
            incomplete = True
            unavailable_sources.append("odoo")
            financial_section = f"""## Revenue & Expenses

> **Financial data unavailable** — Odoo connection failed at {ts_str}. Showing task and social media data only.
"""
    else:
        incomplete = True
        unavailable_sources.append("odoo")
        financial_section = f"""## Revenue & Expenses

> **Financial data unavailable** — Odoo service is degraded (circuit breaker open). Showing task and social media data only.
"""

    # --- Section 2: Completed Tasks from Done/ ---
    done_dir = vault / "Done"
    task_count = 0
    by_source = {}
    if done_dir.exists():
        for f in done_dir.glob("*.md"):
            task_count += 1
            content = f.read_text(encoding="utf-8", errors="ignore")
            for line in content.split("\n"):
                if line.startswith("source:"):
                    src = line.split(":", 1)[1].strip()
                    by_source[src] = by_source.get(src, 0) + 1
                    break
    data_sources.append("vault_done")

    tasks_section = f"""## Completed Tasks

**Total this week**: {task_count}

| Source | Count |
|--------|-------|
"""
    for src, count in sorted(by_source.items(), key=lambda x: -x[1]):
        tasks_section += f"| {src} | {count} |\n"
    if not by_source:
        tasks_section += "| *(no tasks)* | 0 |\n"

    # --- Section 3: Social Media Activity ---
    social_log = vault / "Logs" / "mcp_social.jsonl"
    social_stats = {"facebook": 0, "instagram": 0, "twitter": 0}
    if social_log.exists():
        for line in social_log.read_text().splitlines():
            try:
                entry = json.loads(line)
                if entry.get("action") == "success":
                    tool = entry.get("tool", "")
                    if "facebook" in tool:
                        social_stats["facebook"] += 1
                    elif "instagram" in tool:
                        social_stats["instagram"] += 1
                    elif "twitter" in tool:
                        social_stats["twitter"] += 1
            except json.JSONDecodeError:
                continue
    data_sources.append("social_logs")
    total_social = sum(social_stats.values())

    social_section = f"""## Social Media Activity

| Platform | Posts |
|----------|-------|
| Facebook | {social_stats['facebook']} |
| Instagram | {social_stats['instagram']} |
| Twitter/X | {social_stats['twitter']} |
| **Total** | **{total_social}** |
"""

    # --- Section 4: Bottlenecks ---
    pending_dir = vault / "Pending_Approval"
    bottlenecks = []
    if pending_dir.exists():
        for f in pending_dir.glob("*.md"):
            age_hours = (ts.timestamp() - f.stat().st_mtime) / 3600
            if age_hours > 24:
                bottlenecks.append({"file": f.name, "hours_waiting": round(age_hours, 1)})
    data_sources.append("pending_approval")

    bottleneck_section = "## Bottlenecks\n\n"
    if bottlenecks:
        bottleneck_section += "| Task | Hours Waiting |\n|------|---------------|\n"
        for b in sorted(bottlenecks, key=lambda x: -x["hours_waiting"]):
            bottleneck_section += f"| {b['file']} | {b['hours_waiting']}h |\n"
    else:
        bottleneck_section += "No stale items in Pending_Approval/ (all under 24h).\n"

    # --- Section 5: Proactive Suggestions ---
    suggestions_section = """## Proactive Suggestions

"""
    if bottlenecks:
        suggestions_section += f"- **Review {len(bottlenecks)} stale approval items** — some tasks have been waiting 24+ hours\n"
    if total_social == 0:
        suggestions_section += "- **No social media posts this week** — consider scheduling regular business updates\n"
    if task_count == 0:
        suggestions_section += "- **No tasks completed** — check if watchers and orchestrator are running\n"
    if not bottlenecks and total_social > 0 and task_count > 0:
        suggestions_section += "- All systems running smoothly. No immediate action required.\n"

    # --- Executive Summary ---
    exec_section = f"""## Executive Summary

Weekly briefing for {start} to {end}. {task_count} tasks completed, {total_social} social media posts published. """
    if incomplete:
        exec_section += f"**Note**: Financial data unavailable (Odoo {'degraded' if not odoo_available else 'error'}). "
    if bottlenecks:
        exec_section += f"{len(bottlenecks)} item(s) stalled in approval queue."
    exec_section += "\n"

    # --- Assemble briefing ---
    briefing_content = f"""---
generated: "{ts_str}"
period: "{start} to {end}"
data_sources: {json.dumps(data_sources)}
incomplete: {str(incomplete).lower()}
correlation_id: "{correlation_id}"
---

# Monday Morning CEO Briefing

**Period**: {start} to {end}
**Generated**: {ts_str}

{exec_section}

{financial_section}

{tasks_section}

{social_section}

{bottleneck_section}

{suggestions_section}
"""

    # Write briefing file
    briefings_dir = vault / "Briefings"
    briefings_dir.mkdir(parents=True, exist_ok=True)
    briefing_filename = f"{today.isoformat()}_Monday_Briefing.md"
    briefing_path = briefings_dir / briefing_filename

    tmp = briefing_path.with_suffix(briefing_path.suffix + ".tmp")
    tmp.write_text(briefing_content, encoding="utf-8")
    os.rename(tmp, briefing_path)

    log_tool_call("documents", "docs.generate_briefing", "success", "success",
                  f"CEO Briefing generated: {briefing_filename}", correlation_id,
                  result={"briefing_file": str(briefing_path), "incomplete": incomplete})

    return make_response("success", "docs.generate_briefing", correlation_id,
                         briefing_file=str(briefing_path),
                         data_sources=data_sources,
                         incomplete=incomplete,
                         unavailable_sources=unavailable_sources if unavailable_sources else [],
                         sections=sections)


if __name__ == "__main__":
    server.run(transport="stdio")
