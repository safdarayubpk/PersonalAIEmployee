# How to Use Your AI Employee

> Quick reference guide for all active capabilities. Just open Claude Code and talk naturally.

---

## 1. Facebook Posting

**Page:** Safdar Ayub - AI & Tech

### Commands

| You Say | What Happens |
|---|---|
| `post to facebook: [your text]` | Posts your exact text |
| `post to facebook about [topic]` | AI drafts, you approve, it posts |
| `draft facebook post` | AI drafts, you edit, then posts |

### Examples

```
post to facebook: 5 tips for learning Python in 2026
```

```
post to facebook about AI trends in business
```

```
draft a motivational tech post for facebook
```

### How It Works

1. You give content or a topic
2. If topic only — AI drafts the post and shows you
3. You approve (say "yes") or ask for changes
4. AI posts to your Facebook page
5. You get the Post ID as confirmation

### Credentials

- Token stored in `.env` as `FACEBOOK_ACCESS_TOKEN`
- This is a **Page Access Token** (not user token)
- If token expires, go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/):
  1. Select app: **AI Employee Pages**
  2. Change "User or Page" dropdown to **Get Page Access Token**
  3. Ensure permissions: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`
  4. Click **Generate Access Token**
  5. Update `.env` with new token

---

## 2. Gmail (Read, Send, Manage)

**Account:** safdarayub@gmail.com

### Commands

| You Say | What Happens |
|---|---|
| `check my email` | Shows latest inbox emails |
| `any important emails?` | Reads and filters important ones |
| `send email to [address] about [topic]` | AI drafts, you approve, it sends |
| `email [address]: [message]` | Sends your exact message |
| `search emails from [sender/keyword]` | Finds matching emails |
| `reply to that email` | AI drafts a reply for you |

### Examples

```
send email to client@company.com about project update
```

```
check my email for anything from LinkedIn
```

```
draft an email to hr@company.com requesting leave on Monday
```

```
any new emails today?
```

```
search emails about invoice
```

### How It Works

1. **Send:** You give recipient + topic/message → AI drafts → you approve → it sends from safdarayub@gmail.com
2. **Read:** AI pulls your inbox and shows sender, subject, date
3. **Search:** AI searches by keyword, sender, or date range

### Credentials

- OAuth2 credentials in `credentials.json`
- Token in `token.json` (auto-refreshes)
- If token expires/revoked, AI will re-authenticate (opens browser for Google login)
- Permissions: `gmail.readonly`, `gmail.send`, `gmail.modify`

---

## 3. Odoo ERP (Invoices, Payments, Customers)

**Instance:** localhost:8069 | **Database:** fte_db

### Commands

| You Say | What Happens |
|---|---|
| `list invoices` | Shows all invoices with status |
| `show unpaid invoices` | Filters unpaid only |
| `create invoice for [customer]` | Creates invoice (you approve first) |
| `register payment for [invoice]` | Marks as paid (you approve first) |
| `financial summary` | Revenue, receivables, paid/unpaid counts |
| `list customers` | Shows all partners/contacts |

### Examples

```
list invoices
```

```
create invoice for Test Customer - web development - Rs 50,000
```

```
financial summary for this month
```

```
show unpaid invoices
```

### How It Works

- **Read operations** (list, summary) → auto-execute, no approval needed
- **Write operations** (create invoice, register payment) → you approve first
- Data comes from your local Odoo Docker instance

### Credentials

- Stored in `.env`: `ODOO_HOST`, `ODOO_PORT`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD`
- Make sure Odoo Docker is running: `docker-compose -f docker-compose.odoo.yml up -d`

---

## 4. WhatsApp Monitoring (Auto-Watch)

**Account:** Your linked WhatsApp number

### What It Does

| Capability | Description |
|---|---|
| Detect unread messages | Scans all chats every 15 seconds |
| Read message text | Extracts actual message content |
| Detect media | Identifies photos, videos, documents, voice notes |
| Classify urgency | Sorts into high/medium/low based on keywords |
| Create action files | Writes `Needs_Action/*.md` for important messages |
| Run 24/7 | Daemon mode via PM2 (headless, auto-restart) |

### Urgency Classification

| Level | Keywords | What Happens |
|---|---|---|
| **High** | payment, invoice, urgent, emergency, deadline, ASAP, legal, contract, breach | Action file created immediately |
| **Medium** | meeting, schedule, project, client, approve, confirm, email, call | Action file created |
| **Low** | Everything else (casual chat, memes) | Logged only, no action file |

### How to Start/Stop

```
# First time (needs QR scan — visible browser)
python .claude/skills/whatsapp-watcher/scripts/whatsapp_monitor.py

# After QR linked (headless, background)
python .claude/skills/whatsapp-watcher/scripts/whatsapp_monitor.py --headless

# Via PM2 (recommended for 24/7)
pm2 start config/ecosystem.config.js --only whatsapp-watcher
pm2 stop whatsapp-watcher
pm2 logs whatsapp-watcher
```

### How It Works

1. Watcher runs in background, polls WhatsApp Web every 15 seconds
2. Detects unread messages in direct chats and groups
3. Classifies urgency using `config/risk-keywords.json`
4. High/Medium messages → creates `Needs_Action/*.md` in vault
5. Low priority → logged to `Logs/whatsapp.jsonl` only
6. Orchestrator picks up action files → you decide what to do

### What It Cannot Do

| Limitation | Reason |
|---|---|
| Cannot reply to messages | Read-only for safety |
| Cannot send new messages | Avoids accidental sends |
| Cannot download media | Detects type only |
| Cannot work if phone is off | WhatsApp Web needs phone online |

### Output Files

- Action files: `AI_Employee_Vault/Needs_Action/whatsapp-*.md`
- Logs: `AI_Employee_Vault/Logs/whatsapp.jsonl`
- Session: `~/.whatsapp-watcher-session/` (no QR needed after first link)

### First Time Setup

1. Run the monitor without `--headless`
2. Browser opens with WhatsApp Web QR code
3. On phone: **WhatsApp → Settings → Linked Devices → Link a Device**
4. Scan QR code
5. Session saved — future runs don't need QR again

---

## 5. CEO Briefing (Weekly Business Summary)

**Output:** `AI_Employee_Vault/Briefings/YYYY-MM-DD_CEO_Briefing.md`

### Commands

| You Say | What Happens |
|---|---|
| `generate CEO briefing` | Generates full briefing for past 7 days |
| `weekly business summary` | Same as above |
| `CEO report` | Same as above |
| `generate CEO briefing from 2026-03-01 to 2026-03-15` | Custom date range |

### Examples

```
generate CEO briefing
```

```
weekly business summary
```

```
how did the business do this week
```

```
CEO report for last 2 weeks
```

### What It Covers (6 Sections)

| Section | Data Source | What You See |
|---|---|---|
| **Executive Summary** | All sources | Tasks done, items pending, bottlenecks, posts count |
| **Revenue & Finances** | Odoo ERP | Invoices, revenue, receivables, paid/unpaid counts |
| **Completed Tasks** | `Done/` folder | Count by source (Gmail, WhatsApp, file-drop, manual) |
| **Social Media Activity** | `Logs/mcp_social.jsonl` | Posts per platform (Facebook, Instagram, Twitter) |
| **Bottlenecks** | `Pending_Approval/` | Items stuck for more than 24 hours |
| **Proactive Suggestions** | Auto-generated | Clear bottlenecks, follow up payments, post to social |

### How It Works

1. You say "generate CEO briefing"
2. AI pulls data from Odoo, vault folders, and social logs
3. Generates a markdown report with all 6 sections
4. Saves to `AI_Employee_Vault/Briefings/`
5. Shows you the full briefing

### Scheduled (Automatic)

- Configured to run every **Monday at 9 AM** via scheduler
- Creates a `Needs_Action/` file which the orchestrator processes
- You get the briefing without asking

### Output Location

- `AI_Employee_Vault/Briefings/2026-03-20_CEO_Briefing.md`
- Open in Obsidian vault for best viewing

---

## 6. Scheduling (Automated Recurring Tasks)

**Config:** `config/schedules.json` | **Timezone:** Asia/Karachi

### Pre-Configured Jobs

| Job | Schedule | What It Does |
|---|---|---|
| Morning Gmail check | 8:00 AM daily | Poll Gmail for important emails |
| Afternoon Gmail check | 2:00 PM daily | Catch missed emails |
| Evening Gmail check | 8:00 PM daily | End-of-day email sweep |
| Morning inbox sweep | 8:15 AM daily | Process all pending Needs_Action files |
| Afternoon inbox sweep | 2:15 PM daily | Afternoon task processing |
| Weekly CEO briefing | Monday 9:00 AM | Generate business summary report |
| Weekly social summary | Monday 10:00 AM | Social media activity stats |
| Daily health check | 7:00 AM daily | Check all service health status |

### Commands

| You Say | What Happens |
|---|---|
| `start scheduler` | Starts the scheduler daemon |
| `schedule a task` | AI helps you add a new recurring job |
| `list scheduled jobs` | Shows all active jobs |
| `stop scheduler` | Stops the daemon |

### How to Start/Stop

```
# Start via PM2 (recommended for 24/7)
pm2 start config/ecosystem.config.js --only scheduler-daemon
pm2 stop scheduler-daemon
pm2 logs scheduler-daemon

# Start directly
python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py
```

### How It Works

1. Scheduler daemon runs in background (PM2 or direct)
2. At each scheduled time, creates a `Needs_Action/scheduler/*.md` file
3. Orchestrator picks it up and executes the action
4. All events logged to `Logs/scheduler.jsonl`

### Adding a Custom Job

Edit `config/schedules.json` and add:
```json
{
  "task_name": "my-custom-task",
  "cron": "0 17 * * *",
  "description": "What this job does",
  "action": "orchestrator.process_all",
  "priority": "routine",
  "source": "daily-scheduler",
  "enabled": true
}
```

Common cron patterns:
- `0 8 * * *` — Every day at 8:00 AM
- `0 9 * * 1` — Every Monday at 9:00 AM
- `0 */6 * * *` — Every 6 hours
- `30 8 * * 1-5` — Weekdays at 8:30 AM

---

## 7. Health Monitoring (Service Status)

**Data:** `AI_Employee_Vault/Logs/health.json`

### Monitored Services

| Service | What It Tracks |
|---|---|
| **Gmail** | Email API connection |
| **Facebook** | Graph API posting |
| **Instagram** | Graph API posting |
| **Twitter** | Twitter API connection |
| **Odoo** | ERP database connection |

### Health States

| State | Meaning | Action |
|---|---|---|
| **Healthy** | Working normally | No action needed |
| **Degraded** | 3+ consecutive failures, cooldown active (5 min) | Auto-recovers, monitor |
| **Recovering** | Cooldown expired, testing connection | Wait for next call |
| **Down** | Auth error (401), requires manual fix | Check credentials |

### Commands

| You Say | What Happens |
|---|---|
| `check service health` | Shows status of all 5 services |
| `which services are down?` | Filters unhealthy services |
| `health monitor report` | Full health report with failure counts |
| `system health` | Same as above |

### Examples

```
check service health
```

```
are all services running?
```

```
which services are degraded?
```

### How It Works

1. Each MCP server (Gmail, Social, Odoo) has a **circuit breaker**
2. After each API call, it records success or failure in `health.json`
3. 3 consecutive failures → circuit opens → service marked degraded
4. After 5 min cooldown → circuit half-opens → tries one test call
5. If test succeeds → healthy again. If fails → stays degraded
6. Health check runs automatically every day at 7:00 AM

### Auto-Protection

- If a service is degraded, the orchestrator **skips routing tasks** to it
- Prevents cascading failures (e.g., Gmail down won't block other tasks)
- Non-retryable errors (auth failures) require you to fix credentials manually

---

## General Tips

1. **Just talk naturally** — no special syntax needed
2. **AI always confirms** before sending emails or posting
3. **Say "yes"** to approve, or ask for changes
4. **All credentials** are in `/home/safdarayub/Desktop/claude/fte/.env`
5. **Never share** the `.env` file (it contains API keys)

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Facebook post fails | Token expired → regenerate in Graph API Explorer (see above) |
| Gmail auth error | Token revoked → AI will re-authenticate automatically |
| Odoo connection refused | Start Docker: `docker-compose -f docker-compose.odoo.yml up -d` |
| Twitter posting fails | Requires paid API plan ($100/mo) — currently read-only |
| WhatsApp QR expired | Run monitor without `--headless`, scan QR again |
| WhatsApp not detecting messages | DOM selectors may have changed — check `references/whatsapp_web_selectors.md` |
| WhatsApp phone disconnected | Reconnect phone to internet, WhatsApp Web will resume |
| CEO briefing missing financials | Odoo Docker not running → `docker-compose -f docker-compose.odoo.yml up -d` |
| CEO briefing shows 0 social posts | Social log empty → posts will appear after using Facebook posting |
| Scheduler not running | Start via PM2: `pm2 start config/ecosystem.config.js --only scheduler-daemon` |
| Scheduler duplicate instance | Delete PID lock: `rm Logs/scheduler.pid` then restart |
| Service shows degraded | Check credentials in `.env`, restart the MCP server |
| Health.json missing | AI Employee will recreate it on next health check |

---

*Last updated: 2026-03-20*
