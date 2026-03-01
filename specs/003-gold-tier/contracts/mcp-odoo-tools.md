# MCP Odoo ERP Server Tools Contract

**Server**: `fte-odoo`
**Script**: `src/mcp/odoo_server.py`
**Transport**: stdio

## Tools

### odoo.list_invoices

**HITL**: Routine (auto-execute)
**Description**: List invoices from Odoo, optionally filtered by payment status or partner

**Input**:
```json
{
  "payment_state": "string (optional) — 'not_paid'|'partial'|'paid' (default: all)",
  "partner_id": "integer (optional) — filter by customer/vendor ID",
  "limit": "integer (optional, default: 50, max: 200)",
  "correlation_id": "string (optional)"
}
```

**Output**:
```json
{
  "status": "success",
  "tool": "odoo.list_invoices",
  "data": [
    {
      "id": 1,
      "name": "INV/2026/001",
      "partner": "Acme Corp",
      "amount_total": 1500.00,
      "amount_residual": 1500.00,
      "payment_state": "not_paid",
      "invoice_date": "2026-02-15",
      "invoice_date_due": "2026-03-15"
    }
  ],
  "count": 5,
  "correlation_id": "<propagated>"
}
```

---

### odoo.create_invoice

**HITL**: Critical (approval + confirmation log)
**Description**: Create a new customer invoice in Odoo

**Input**:
```json
{
  "partner_id": "integer (required) — customer ID in Odoo",
  "lines": [
    {
      "description": "string (required)",
      "quantity": "number (required)",
      "price_unit": "number (required)"
    }
  ],
  "invoice_date": "string (optional) — YYYY-MM-DD (default: today)",
  "correlation_id": "string (optional)"
}
```

**Output (live, approved)**:
```json
{
  "status": "success",
  "tool": "odoo.create_invoice",
  "invoice_id": 42,
  "invoice_name": "INV/2026/003",
  "amount_total": 500.00,
  "state": "draft",
  "correlation_id": "<propagated>"
}
```

---

### odoo.register_payment

**HITL**: Critical (approval + confirmation log)
**Description**: Register a payment against an existing invoice

**Input**:
```json
{
  "invoice_id": "integer (required) — Odoo invoice ID",
  "amount": "number (required) — payment amount",
  "payment_date": "string (optional) — YYYY-MM-DD (default: today)",
  "correlation_id": "string (optional)"
}
```

**Output (live, approved)**:
```json
{
  "status": "success",
  "tool": "odoo.register_payment",
  "payment_id": 15,
  "invoice_id": 42,
  "amount": 500.00,
  "new_payment_state": "paid",
  "correlation_id": "<propagated>"
}
```

---

### odoo.financial_summary

**HITL**: Routine (auto-execute)
**Description**: Get aggregated financial summary for a date range

**Input**:
```json
{
  "period_start": "string (optional) — YYYY-MM-DD (default: first day of current month)",
  "period_end": "string (optional) — YYYY-MM-DD (default: today)",
  "correlation_id": "string (optional)"
}
```

**Output**:
```json
{
  "status": "success",
  "tool": "odoo.financial_summary",
  "period": {"start": "2026-03-01", "end": "2026-03-01"},
  "revenue": 5000.00,
  "expenses": 2000.00,
  "receivables": 1500.00,
  "payables": 800.00,
  "net_income": 3000.00,
  "invoice_count": {"paid": 3, "unpaid": 2, "partial": 1},
  "correlation_id": "<propagated>"
}
```

---

### odoo.list_partners

**HITL**: Routine (auto-execute)
**Description**: List contacts/customers from Odoo

**Input**:
```json
{
  "customer_only": "boolean (optional, default: true)",
  "search": "string (optional) — name search filter",
  "limit": "integer (optional, default: 50)",
  "correlation_id": "string (optional)"
}
```

**Output**:
```json
{
  "status": "success",
  "tool": "odoo.list_partners",
  "data": [
    {
      "id": 1,
      "name": "Acme Corp",
      "email": "info@acme.com",
      "phone": "+1-555-0100",
      "is_company": true
    }
  ],
  "count": 10,
  "correlation_id": "<propagated>"
}
```
