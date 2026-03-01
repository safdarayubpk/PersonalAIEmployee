"""MCP Odoo ERP Server — JSON-RPC bridge to Odoo 19 Community via odoorpc.

Tools: odoo.list_invoices (routine), odoo.create_invoice (critical),
       odoo.register_payment (critical), odoo.financial_summary (routine),
       odoo.list_partners (routine)
Transport: stdio
"""

import os
import sys
from datetime import datetime, timezone, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP
from base_server import (
    get_vault_path, is_dry_run,
    log_tool_call, log_critical_action,
    create_pending_approval, make_response,
    get_circuit_breaker, check_service_available,
)

server = FastMCP("fte-odoo")


def _get_odoo():
    """Connect to Odoo via odoorpc. Returns an OdooRPC session."""
    import odoorpc
    host = os.environ.get("ODOO_HOST", "localhost")
    port = int(os.environ.get("ODOO_PORT", "8069"))
    db = os.environ.get("ODOO_DB", "")
    user = os.environ.get("ODOO_USER", "admin")
    password = os.environ.get("ODOO_PASSWORD", "")

    if not db:
        raise ValueError("ODOO_DB environment variable must be set")

    odoo = odoorpc.ODOO(host, port=port)
    odoo.login(db, user, password)
    return odoo


@server.tool()
def odoo_list_invoices(payment_state: str = "", partner_id: int = 0,
                       limit: int = 50,
                       correlation_id: str = "") -> dict:
    """List invoices from Odoo, optionally filtered by payment status or partner.

    Args:
        payment_state: Filter by 'not_paid', 'partial', or 'paid' (default: all)
        partner_id: Filter by customer/vendor ID (default: all)
        limit: Max results (default: 50, max: 200)
        correlation_id: Correlation ID for audit tracing
    """
    limit = min(limit, 200)
    params = {"payment_state": payment_state, "partner_id": partner_id, "limit": limit}

    available, err = check_service_available("odoo")
    if not available:
        return make_response("service_degraded", "odoo.list_invoices", correlation_id,
                             detail="Odoo service is degraded.", data=[], count=0)

    log_tool_call("odoo", "odoo.list_invoices", "call", "success",
                  "Querying Odoo invoices", correlation_id, params=params)
    cb = get_circuit_breaker("odoo")
    try:
        odoo = _get_odoo()
        domain = [("move_type", "in", ["out_invoice", "in_invoice"])]
        if payment_state:
            domain.append(("payment_state", "=", payment_state))
        if partner_id:
            domain.append(("partner_id", "=", partner_id))

        Invoice = odoo.env["account.move"]
        ids = Invoice.search(domain, limit=limit)
        records = Invoice.read(ids, [
            "name", "partner_id", "amount_total", "amount_residual",
            "payment_state", "invoice_date", "invoice_date_due",
        ])

        data = []
        for r in records:
            data.append({
                "id": r["id"],
                "name": r.get("name", ""),
                "partner": r["partner_id"][1] if r.get("partner_id") else "",
                "amount_total": r.get("amount_total", 0),
                "amount_residual": r.get("amount_residual", 0),
                "payment_state": r.get("payment_state", ""),
                "invoice_date": str(r.get("invoice_date", "")),
                "invoice_date_due": str(r.get("invoice_date_due", "")),
            })

        cb.record_success()
        log_tool_call("odoo", "odoo.list_invoices", "success", "success",
                      f"Found {len(data)} invoices", correlation_id,
                      result={"count": len(data)})
        return make_response("success", "odoo.list_invoices", correlation_id,
                             data=data, count=len(data))

    except Exception as e:
        cb.record_failure(str(e))
        log_tool_call("odoo", "odoo.list_invoices", "failure", "failure",
                      f"Odoo query failed: {e}", correlation_id, params=params)
        return make_response("error", "odoo.list_invoices", correlation_id,
                             detail=f"Odoo query failed: {e}", data=[], count=0)


@server.tool()
def odoo_create_invoice(partner_id: int, lines: list,
                        invoice_date: str = "",
                        approval_ref: str = "",
                        correlation_id: str = "") -> dict:
    """Create a new customer invoice in Odoo. HITL: critical (approval + confirmation log).

    Args:
        partner_id: Customer ID in Odoo
        lines: List of invoice lines [{"description": str, "quantity": num, "price_unit": num}]
        invoice_date: Invoice date YYYY-MM-DD (default: today)
        approval_ref: Path to approved file in Approved/ folder
        correlation_id: Correlation ID for audit tracing
    """
    params = {"partner_id": partner_id, "lines": lines, "invoice_date": invoice_date}

    if is_dry_run():
        total = sum(l.get("quantity", 0) * l.get("price_unit", 0) for l in lines)
        log_tool_call("odoo", "odoo.create_invoice", "dry_run", "success",
                      f"Would create invoice for partner {partner_id}, total ~{total}",
                      correlation_id, params=params)
        return make_response("dry_run", "odoo.create_invoice", correlation_id,
                             detail=f"Would create invoice for partner {partner_id}, total ~{total}")

    # HITL gate — critical
    if not approval_ref:
        approval_file = create_pending_approval("odoo.create_invoice", params, correlation_id)
        log_critical_action("odoo.create_invoice", "hitl_blocked", "skipped",
                            f"Critical action: invoice creation for partner {partner_id}",
                            correlation_id, params=params)
        log_tool_call("odoo", "odoo.create_invoice", "hitl_blocked", "skipped",
                      "HITL gate: critical approval required", correlation_id, params=params)
        return make_response("pending_approval", "odoo.create_invoice",
                             correlation_id, approval_file=approval_file)

    try:
        odoo = _get_odoo()
        inv_date = invoice_date or date.today().isoformat()
        inv_lines = []
        for line in lines:
            inv_lines.append((0, 0, {
                "name": line.get("description", ""),
                "quantity": line.get("quantity", 1),
                "price_unit": line.get("price_unit", 0),
            }))

        Invoice = odoo.env["account.move"]
        inv_id = Invoice.create({
            "move_type": "out_invoice",
            "partner_id": partner_id,
            "invoice_date": inv_date,
            "invoice_line_ids": inv_lines,
        })

        inv_data = Invoice.read(inv_id, ["name", "amount_total", "state"])
        result = {
            "invoice_id": inv_id,
            "invoice_name": inv_data[0].get("name", "") if inv_data else "",
            "amount_total": inv_data[0].get("amount_total", 0) if inv_data else 0,
            "state": inv_data[0].get("state", "draft") if inv_data else "draft",
        }

        log_critical_action("odoo.create_invoice", "success", "success",
                            f"Invoice created: {result['invoice_name']}",
                            correlation_id, params=params)
        log_tool_call("odoo", "odoo.create_invoice", "success", "success",
                      f"Invoice created: {result['invoice_name']}", correlation_id,
                      params=params, result=result)
        return make_response("success", "odoo.create_invoice", correlation_id, **result)

    except Exception as e:
        log_tool_call("odoo", "odoo.create_invoice", "failure", "failure",
                      f"Invoice creation failed: {e}", correlation_id, params=params)
        return make_response("error", "odoo.create_invoice", correlation_id,
                             detail=f"Invoice creation failed: {e}")


@server.tool()
def odoo_register_payment(invoice_id: int, amount: float,
                          payment_date: str = "",
                          approval_ref: str = "",
                          correlation_id: str = "") -> dict:
    """Register a payment against an existing invoice. HITL: critical.

    Args:
        invoice_id: Odoo invoice ID
        amount: Payment amount
        payment_date: Payment date YYYY-MM-DD (default: today)
        approval_ref: Path to approved file in Approved/ folder
        correlation_id: Correlation ID for audit tracing
    """
    params = {"invoice_id": invoice_id, "amount": amount, "payment_date": payment_date}

    if is_dry_run():
        log_tool_call("odoo", "odoo.register_payment", "dry_run", "success",
                      f"Would register payment of {amount} on invoice {invoice_id}",
                      correlation_id, params=params)
        return make_response("dry_run", "odoo.register_payment", correlation_id,
                             detail=f"Would register payment of {amount} on invoice {invoice_id}")

    if not approval_ref:
        approval_file = create_pending_approval("odoo.register_payment", params, correlation_id)
        log_critical_action("odoo.register_payment", "hitl_blocked", "skipped",
                            f"Critical action: payment {amount} on invoice {invoice_id}",
                            correlation_id, params=params)
        return make_response("pending_approval", "odoo.register_payment",
                             correlation_id, approval_file=approval_file)

    try:
        odoo = _get_odoo()
        pay_date = payment_date or date.today().isoformat()

        # Use Odoo's payment register wizard
        Invoice = odoo.env["account.move"]
        inv_data = Invoice.read(invoice_id, ["payment_state"])

        # Register payment via account.payment.register wizard
        PaymentRegister = odoo.env["account.payment.register"]
        ctx = {"active_model": "account.move", "active_ids": [invoice_id]}
        wiz_id = PaymentRegister.with_context(ctx).create({
            "amount": amount,
            "payment_date": pay_date,
        })
        PaymentRegister.with_context(ctx).action_create_payments([wiz_id])

        # Read updated state
        updated = Invoice.read(invoice_id, ["payment_state"])
        new_state = updated[0].get("payment_state", "") if updated else ""

        result = {
            "payment_id": wiz_id,
            "invoice_id": invoice_id,
            "amount": amount,
            "new_payment_state": new_state,
        }

        log_critical_action("odoo.register_payment", "success", "success",
                            f"Payment registered: {amount} on invoice {invoice_id}",
                            correlation_id, params=params)
        log_tool_call("odoo", "odoo.register_payment", "success", "success",
                      f"Payment registered", correlation_id,
                      params=params, result=result)
        return make_response("success", "odoo.register_payment", correlation_id, **result)

    except Exception as e:
        log_tool_call("odoo", "odoo.register_payment", "failure", "failure",
                      f"Payment failed: {e}", correlation_id, params=params)
        return make_response("error", "odoo.register_payment", correlation_id,
                             detail=f"Payment failed: {e}")


@server.tool()
def odoo_financial_summary(period_start: str = "", period_end: str = "",
                           correlation_id: str = "") -> dict:
    """Get aggregated financial summary for a date range.

    Args:
        period_start: Start date YYYY-MM-DD (default: first day of current month)
        period_end: End date YYYY-MM-DD (default: today)
        correlation_id: Correlation ID for audit tracing
    """
    today = date.today()
    start = period_start or today.replace(day=1).isoformat()
    end = period_end or today.isoformat()
    params = {"period_start": start, "period_end": end}

    log_tool_call("odoo", "odoo.financial_summary", "call", "success",
                  f"Financial summary {start} to {end}", correlation_id, params=params)
    try:
        odoo = _get_odoo()
        MoveLine = odoo.env["account.move.line"]

        # Get all posted move lines in the period
        domain = [
            ("date", ">=", start),
            ("date", "<=", end),
            ("parent_state", "=", "posted"),
        ]
        line_ids = MoveLine.search(domain)
        lines = MoveLine.read(line_ids, ["debit", "credit", "account_id"])

        revenue = 0.0
        expenses = 0.0
        receivables = 0.0
        payables = 0.0

        for line in lines:
            account_name = line.get("account_id", [0, ""])[1].lower() if line.get("account_id") else ""
            debit = line.get("debit", 0) or 0
            credit = line.get("credit", 0) or 0

            if "revenue" in account_name or "income" in account_name:
                revenue += credit - debit
            elif "expense" in account_name:
                expenses += debit - credit
            elif "receivable" in account_name:
                receivables += debit - credit
            elif "payable" in account_name:
                payables += credit - debit

        # Count invoices by payment state
        Invoice = odoo.env["account.move"]
        paid = len(Invoice.search([("move_type", "in", ["out_invoice"]), ("payment_state", "=", "paid"), ("invoice_date", ">=", start), ("invoice_date", "<=", end)]))
        unpaid = len(Invoice.search([("move_type", "in", ["out_invoice"]), ("payment_state", "=", "not_paid"), ("invoice_date", ">=", start), ("invoice_date", "<=", end)]))
        partial = len(Invoice.search([("move_type", "in", ["out_invoice"]), ("payment_state", "=", "partial"), ("invoice_date", ">=", start), ("invoice_date", "<=", end)]))

        result = {
            "period": {"start": start, "end": end},
            "revenue": round(revenue, 2),
            "expenses": round(expenses, 2),
            "receivables": round(receivables, 2),
            "payables": round(payables, 2),
            "net_income": round(revenue - expenses, 2),
            "invoice_count": {"paid": paid, "unpaid": unpaid, "partial": partial},
        }

        log_tool_call("odoo", "odoo.financial_summary", "success", "success",
                      f"Summary: revenue={revenue:.2f}, expenses={expenses:.2f}",
                      correlation_id, result=result)
        return make_response("success", "odoo.financial_summary", correlation_id, **result)

    except Exception as e:
        log_tool_call("odoo", "odoo.financial_summary", "failure", "failure",
                      f"Financial summary failed: {e}", correlation_id, params=params)
        return make_response("error", "odoo.financial_summary", correlation_id,
                             detail=f"Financial summary failed: {e}")


@server.tool()
def odoo_list_partners(customer_only: bool = True, search: str = "",
                       limit: int = 50,
                       correlation_id: str = "") -> dict:
    """List contacts/customers from Odoo.

    Args:
        customer_only: Only show customers (default: true)
        search: Name search filter
        limit: Max results (default: 50)
        correlation_id: Correlation ID for audit tracing
    """
    params = {"customer_only": customer_only, "search": search, "limit": limit}

    log_tool_call("odoo", "odoo.list_partners", "call", "success",
                  f"Querying Odoo partners", correlation_id, params=params)
    try:
        odoo = _get_odoo()
        domain = []
        if customer_only:
            domain.append(("customer_rank", ">", 0))
        if search:
            domain.append(("name", "ilike", search))

        Partner = odoo.env["res.partner"]
        ids = Partner.search(domain, limit=limit)
        records = Partner.read(ids, ["name", "email", "phone", "is_company"])

        data = [{
            "id": r["id"],
            "name": r.get("name", ""),
            "email": r.get("email", "") or "",
            "phone": r.get("phone", "") or "",
            "is_company": r.get("is_company", False),
        } for r in records]

        log_tool_call("odoo", "odoo.list_partners", "success", "success",
                      f"Found {len(data)} partners", correlation_id,
                      result={"count": len(data)})
        return make_response("success", "odoo.list_partners", correlation_id,
                             data=data, count=len(data))

    except Exception as e:
        log_tool_call("odoo", "odoo.list_partners", "failure", "failure",
                      f"Partner query failed: {e}", correlation_id, params=params)
        return make_response("error", "odoo.list_partners", correlation_id,
                             detail=f"Partner query failed: {e}", data=[], count=0)


if __name__ == "__main__":
    server.run(transport="stdio")
