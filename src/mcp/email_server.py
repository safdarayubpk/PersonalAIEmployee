"""MCP Email Server — wraps src/actions/email.py for Claude Code tool access.

Tools: email.send (sensitive), email.draft (routine), email.search (routine)
Transport: stdio
"""

import os
import sys
from pathlib import Path

# Add src/ to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP
from base_server import (
    HITL_SENSITIVE, HITL_ROUTINE,
    get_vault_path, is_dry_run, is_live_mode,
    log_tool_call, create_pending_approval, make_response,
    get_circuit_breaker, check_service_available,
)

server = FastMCP("fte-email")


@server.tool()
def email_draft(to: str, subject: str, body: str,
                correlation_id: str = "") -> dict:
    """Draft an email locally without sending. Saves to Plans/ folder.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content
        correlation_id: Correlation ID for audit tracing
    """
    from actions.email import draft_email

    log_tool_call("email", "email.draft", "call", "success",
                  f"Drafting email to {to}", correlation_id,
                  params={"to": to, "subject": subject})

    result = draft_email(to=to, subject=subject, body=body)

    log_tool_call("email", "email.draft", "success", "success",
                  f"Draft saved: {result.get('draft_file', '')}",
                  correlation_id, result=result)

    return make_response("success", "email.draft", correlation_id,
                         draft_file=result.get("draft_file", ""),
                         detail=f"Draft saved for {to}")


@server.tool()
def email_send(to: str, subject: str, body: str,
               cc: str = "", approval_ref: str = "",
               correlation_id: str = "") -> dict:
    """Send an email via Gmail API. Requires HITL approval (sensitive).

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body (plain text or HTML)
        cc: CC recipients, comma-separated
        approval_ref: Path to approved file in Approved/ folder
        correlation_id: Correlation ID for audit tracing
    """
    params = {"to": to, "subject": subject, "body": body, "cc": cc}

    # Dry-run check
    if is_dry_run():
        log_tool_call("email", "email.send", "dry_run", "success",
                      f"Would send email to {to} with subject '{subject}'",
                      correlation_id, params=params)
        return make_response("dry_run", "email.send", correlation_id,
                             detail=f"Would send email to {to} with subject '{subject}'")

    # HITL gate — sensitive action requires approval
    if not approval_ref:
        approval_file = create_pending_approval("email.send", params, correlation_id)
        log_tool_call("email", "email.send", "hitl_blocked", "skipped",
                      f"HITL gate: approval required for email to {to}",
                      correlation_id, params=params)
        return make_response("pending_approval", "email.send", correlation_id,
                             approval_file=approval_file,
                             detail=f"Approval required to send email to {to}")

    # Verify approval file exists
    vault = get_vault_path()
    approval_path = vault / approval_ref if not Path(approval_ref).is_absolute() else Path(approval_ref)
    if not approval_path.exists():
        log_tool_call("email", "email.send", "failure", "failure",
                      f"Approval file not found: {approval_ref}",
                      correlation_id, params=params)
        return make_response("error", "email.send", correlation_id,
                             detail=f"Approval file not found: {approval_ref}")

    # Circuit breaker check
    available, err = check_service_available("gmail")
    if not available:
        log_tool_call("email", "email.send", "circuit_open", "failure",
                      "Gmail service degraded", correlation_id, params=params)
        return make_response("service_degraded", "email.send", correlation_id,
                             detail="Gmail service is degraded. Circuit breaker is open.")

    # Execute live send
    cb = get_circuit_breaker("gmail")
    try:
        from actions.email import send_email
        result = send_email(to=to, subject=subject, body=body, cc=cc)
        cb.record_success()
        log_tool_call("email", "email.send", "success", "success",
                      f"Email sent to {to}", correlation_id,
                      params=params, result=result)
        return make_response("success", "email.send", correlation_id,
                             message_id=result.get("message_id", ""),
                             detail=f"Email sent to {to}")
    except Exception as e:
        cb.record_failure(str(e))
        log_tool_call("email", "email.send", "failure", "failure",
                      f"Failed to send email: {e}", correlation_id, params=params)
        return make_response("error", "email.send", correlation_id,
                             detail=f"Failed to send email: {e}")


@server.tool()
def email_search(query: str, max_results: int = 10,
                 correlation_id: str = "") -> dict:
    """Search Gmail inbox for emails matching criteria.

    Args:
        query: Gmail search query (e.g., 'from:client@example.com is:unread')
        max_results: Maximum number of results (default: 10, max: 50)
        correlation_id: Correlation ID for audit tracing
    """
    max_results = min(max_results, 50)

    log_tool_call("email", "email.search", "call", "success",
                  f"Searching Gmail: {query}", correlation_id,
                  params={"query": query, "max_results": max_results})

    # Circuit breaker check
    available, err = check_service_available("gmail")
    if not available:
        return make_response("service_degraded", "email.search", correlation_id,
                             detail="Gmail service is degraded.", results=[], count=0)

    cb = get_circuit_breaker("gmail")
    try:
        from actions.email import _get_gmail_service
        service = _get_gmail_service()
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        email_list = []
        for msg_stub in messages[:max_results]:
            msg = service.users().messages().get(
                userId="me", id=msg_stub["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            email_list.append({
                "id": msg_stub["id"],
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", "")[:200],
            })

        cb.record_success()
        log_tool_call("email", "email.search", "success", "success",
                      f"Found {len(email_list)} emails for query: {query}",
                      correlation_id, result={"count": len(email_list)})

        return make_response("success", "email.search", correlation_id,
                             results=email_list, count=len(email_list))

    except Exception as e:
        cb.record_failure(str(e))
        log_tool_call("email", "email.search", "failure", "failure",
                      f"Search failed: {e}", correlation_id)
        return make_response("error", "email.search", correlation_id,
                             detail=f"Search failed: {e}", results=[], count=0)


if __name__ == "__main__":
    server.run(transport="stdio")
