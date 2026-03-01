# MCP Email Server Tools Contract

**Server**: `fte-email`
**Script**: `src/mcp/email_server.py`
**Transport**: stdio

## Tools

### email.send

**HITL**: Sensitive (approval required)
**Description**: Send an email via Gmail API

**Input**:
```json
{
  "to": "string (required) — recipient email address",
  "subject": "string (required) — email subject line",
  "body": "string (required) — email body (plain text or HTML)",
  "cc": "string (optional) — CC recipients, comma-separated",
  "correlation_id": "string (optional) — propagated from task"
}
```

**Output (dry-run)**:
```json
{
  "status": "dry_run",
  "tool": "email.send",
  "detail": "Would send email to <to> with subject '<subject>'",
  "correlation_id": "<propagated>"
}
```

**Output (live, no approval)**:
```json
{
  "status": "pending_approval",
  "tool": "email.send",
  "approval_file": "/path/to/Pending_Approval/pending-email-send-<timestamp>.md",
  "correlation_id": "<propagated>"
}
```

**Output (live, approved)**:
```json
{
  "status": "success",
  "tool": "email.send",
  "message_id": "<gmail-message-id>",
  "detail": "Email sent to <to>",
  "correlation_id": "<propagated>"
}
```

---

### email.draft

**HITL**: Routine (no approval needed)
**Description**: Draft an email locally without sending

**Input**:
```json
{
  "to": "string (required)",
  "subject": "string (required)",
  "body": "string (required)",
  "correlation_id": "string (optional)"
}
```

**Output**:
```json
{
  "status": "success",
  "tool": "email.draft",
  "draft_file": "/path/to/Plans/email-draft-<timestamp>.md",
  "detail": "Draft saved for <to>",
  "correlation_id": "<propagated>"
}
```

---

### email.search

**HITL**: Routine (no approval needed)
**Description**: Search Gmail inbox for emails matching criteria

**Input**:
```json
{
  "query": "string (required) — Gmail search query (e.g., 'from:client@example.com is:unread')",
  "max_results": "integer (optional, default: 10, max: 50)",
  "correlation_id": "string (optional)"
}
```

**Output**:
```json
{
  "status": "success",
  "tool": "email.search",
  "results": [
    {
      "id": "<gmail-message-id>",
      "from": "<sender>",
      "subject": "<subject>",
      "date": "<ISO 8601>",
      "snippet": "<first 200 chars>"
    }
  ],
  "count": 5,
  "correlation_id": "<propagated>"
}
```
