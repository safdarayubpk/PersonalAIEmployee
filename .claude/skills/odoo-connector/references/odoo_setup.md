# Odoo 19 Community Setup Guide

## 1. Docker Installation (Recommended)

### Start Odoo with PostgreSQL

```bash
# Create a Docker network
docker network create odoo-net

# Start PostgreSQL
docker run -d \
  --name odoo-db \
  --network odoo-net \
  -e POSTGRES_USER=odoo \
  -e POSTGRES_PASSWORD=odoo \
  -e POSTGRES_DB=postgres \
  postgres:16

# Start Odoo 19 Community
docker run -d \
  --name odoo19 \
  --network odoo-net \
  -p 8069:8069 \
  -e HOST=odoo-db \
  -e USER=odoo \
  -e PASSWORD=odoo \
  odoo:19.0
```

### Verify Odoo Is Running

Open `http://localhost:8069` in a browser. You should see the Odoo database setup wizard.

### Create Database

1. On first visit, enter:
   - **Master Password**: `admin` (default, change in production)
   - **Database Name**: `fte_erp` (or your preferred name)
   - **Email**: your admin email
   - **Password**: your admin password
   - **Language**: English
   - **Country**: your country
2. Click **Create Database**
3. Wait for initialization (2-5 minutes)

### Install Accounting Module

1. Go to **Apps** → search "Invoicing" or "Accounting"
2. Install **Invoicing** (includes `account.move`, `account.move.line`, `res.partner`)
3. For full accounting features, install **Accounting** instead

---

## 2. Configure Environment Variables

```bash
export ODOO_HOST="localhost"
export ODOO_PORT="8069"
export ODOO_DB="fte_erp"
export ODOO_USER="admin"
export ODOO_PASSWORD="your-admin-password"
```

Add these to your `.env` file (already in `.gitignore`).

---

## 3. Python Dependencies

```bash
pip install odoorpc
```

The `odoorpc` library (v0.10.1+) handles JSON-RPC communication with Odoo.

---

## 4. Test Connection

```python
import odoorpc

odoo = odoorpc.ODOO("localhost", port=8069)
print(odoo.db.list())  # Should show your database

odoo.login("fte_erp", "admin", "your-password")
print(odoo.env.user.name)  # Should show "Administrator"
```

---

## 5. Odoo Models Used

| Model | Description | Operations |
|-------|-------------|------------|
| `account.move` | Invoices, bills, journal entries | list, create, read |
| `account.move.line` | Invoice lines, journal items | read (for financial_summary) |
| `res.partner` | Customers, vendors, contacts | list, search |
| `account.payment.register` | Payment wizard | create (register payments) |

### Key Fields — `account.move`

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Invoice number (e.g., "INV/2026/00001") |
| `partner_id` | many2one | Customer/vendor reference |
| `move_type` | selection | `out_invoice`, `in_invoice`, `out_refund`, `in_refund` |
| `amount_total` | float | Total amount |
| `amount_residual` | float | Amount remaining to pay |
| `payment_state` | selection | `not_paid`, `partial`, `paid`, `reversed` |
| `invoice_date` | date | Invoice date |
| `invoice_date_due` | date | Due date |
| `state` | selection | `draft`, `posted`, `cancel` |

### Key Fields — `res.partner`

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Partner name |
| `email` | str | Email address |
| `phone` | str | Phone number |
| `is_company` | bool | Company vs individual |
| `customer_rank` | int | >0 means customer |

---

## 6. Docker Management

```bash
# Stop Odoo
docker stop odoo19 odoo-db

# Start Odoo (after stop)
docker start odoo-db && docker start odoo19

# View Odoo logs
docker logs -f odoo19

# Reset (delete everything and start fresh)
docker rm -f odoo19 odoo-db
docker volume prune
# Then re-run the Docker commands above
```

---

## Security Notes

- Change the default master password in production
- Use strong passwords for database and admin user
- Never expose port 8069 to the public internet without a reverse proxy (nginx/caddy)
- Store credentials in `.env` file — never commit to git
- The MCP server uses `DRY_RUN=true` by default — no real operations without explicit opt-in
