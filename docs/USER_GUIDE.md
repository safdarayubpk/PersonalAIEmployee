# Personal AI Employee — Complete User Guide

A step-by-step guide for setting up and using your Personal AI Employee. Written for beginners — no prior experience needed.

---

## Table of Contents

1. [What is the Personal AI Employee?](#1-what-is-the-personal-ai-employee)
2. [How It Works (Simple Explanation)](#2-how-it-works)
3. [Prerequisites](#3-prerequisites)
4. [Installation](#4-installation)
5. [Setting Up External Services](#5-setting-up-external-services)
   - [5.1 Gmail](#51-gmail-setup)
   - [5.2 Twitter/X](#52-twitterx-setup)
   - [5.3 Facebook](#53-facebook-setup)
   - [5.4 WhatsApp](#54-whatsapp-setup)
   - [5.5 Odoo ERP](#55-odoo-erp-setup)
6. [Using Your AI Employee](#6-using-your-ai-employee)
7. [All Available Commands](#7-all-available-commands)
8. [Understanding the Vault (Your AI's Brain)](#8-understanding-the-vault)
9. [Automatic Scheduling](#9-automatic-scheduling)
10. [The Approval System (HITL)](#10-the-approval-system)
11. [Viewing with Obsidian (Optional)](#11-viewing-with-obsidian)
12. [Troubleshooting](#12-troubleshooting)
13. [Environment Variables Reference](#13-environment-variables-reference)
14. [FAQ](#14-faq)

---

## 1. What is the Personal AI Employee?

Your Personal AI Employee is a system that:

- **Monitors** your Gmail, WhatsApp, and file system for new tasks
- **Classifies** each task by priority (routine, sensitive, critical)
- **Handles** routine tasks automatically (archives spam, files newsletters)
- **Flags** important tasks for your review
- **Connects** to Odoo ERP for invoicing and financial tracking
- **Posts** to Twitter, Facebook on your command
- **Generates** weekly CEO business reports
- **Logs** everything for audit and traceability

Think of it as a smart assistant that sits in your terminal. You give it commands, and it does the work.

---

## 2. How It Works

```
YOU (give commands in Claude Code terminal)
  |
  v
AI EMPLOYEE (Claude Code + 14 Skills)
  |
  v
Reads/writes files in your vault folder:
  ~/Documents/AI_Employee_Vault/
    |-- Inbox/              <-- Drop files here, AI processes them
    |-- Needs_Action/       <-- Tasks waiting to be processed
    |-- Plans/              <-- AI creates plans for important tasks
    |-- Pending_Approval/   <-- Sensitive actions wait for your OK
    |-- Approved/           <-- Move files here to approve actions
    |-- Done/               <-- Completed tasks
    |-- Briefings/          <-- CEO reports
    |-- Logs/               <-- Everything is logged (audit trail)
    |-- Dashboard.md        <-- Status overview
    |-- Company_Handbook.md <-- Rules for the AI
```

### The Flow:

```
Email arrives / File dropped / Scheduled trigger
        |
        v
    WATCHER detects it
        |
        v
    Creates task in Needs_Action/
        |
        v
    ORCHESTRATOR processes it:
        |
        |-- Routine (spam, newsletter) --> auto-archive to Done/
        |-- Sensitive (social post)    --> Pending_Approval/ (needs your OK)
        |-- Critical (payment, legal)  --> Plans/ (needs your review)
        |
        v
    You review flagged items
        |
        v
    Move to Approved/ --> AI executes the action
        |
        v
    Done/ (completed + logged)
```

---

## 3. Prerequisites

### Software Required

| Software | Version | How to Install |
|----------|---------|----------------|
| Ubuntu Linux | 20.04+ | Already installed |
| Python | 3.13+ | `sudo apt install python3 python3-venv python3-pip` |
| Claude Code | Latest | `npm install -g @anthropic-ai/claude-code` |
| Docker | 28+ | `sudo apt install docker.io` |
| Git | Latest | `sudo apt install git` |
| Node.js | v24+ | `sudo apt install nodejs npm` |
| Obsidian | Latest (optional) | Download from https://obsidian.md |

### Hardware Required

- Minimum: 8GB RAM, 4-core CPU, 20GB free disk space
- Stable internet connection

---

## 4. Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/safdarayubpk/PersonalAIEmployee.git
cd PersonalAIEmployee
```

### Step 2: Create Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
pip install watchdog pyyaml apscheduler mcp tweepy odoorpc
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
pip install playwright && playwright install chromium
```

### Step 4: Initialize the Vault

```bash
python src/setup_vault.py
```

This creates the vault at `~/Documents/AI_Employee_Vault/` with all required folders.

### Step 5: Create .env File

Create a file called `.env` in the project root (NEVER commit this to git):

```bash
# .env - NEVER commit this file

# Gmail OAuth2 (see Section 5.1 for setup)
# credentials.json goes in project root

# Twitter/X API Keys (see Section 5.2 for setup)
TWITTER_API_KEY=your_api_key_here
TWITTER_API_SECRET=your_api_secret_here
TWITTER_ACCESS_TOKEN=your_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret_here

# Facebook Page (see Section 5.3 for setup)
FACEBOOK_PAGE_ID=your_page_id_here
FACEBOOK_ACCESS_TOKEN=your_page_access_token_here

# Odoo ERP (see Section 5.5 for setup)
ODOO_HOST=localhost
ODOO_PORT=8069
ODOO_DB=fte_db
ODOO_USER=admin
ODOO_PASSWORD=admin
```

### Step 6: Verify Installation

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
python -m pytest tests/unit/ -v

# Check vault exists
ls ~/Documents/AI_Employee_Vault/
```

---

## 5. Setting Up External Services

### 5.1 Gmail Setup

Gmail lets the AI Employee monitor your inbox automatically.

#### Step 1: Create Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Click **"Select a project"** (top left) → **"New Project"**
3. Name it: `AI Employee`
4. Click **Create**

#### Step 2: Enable Gmail API

1. In the Google Cloud Console, go to **APIs & Services** → **Library**
2. Search for **"Gmail API"**
3. Click it → Click **"Enable"**

#### Step 3: Create OAuth2 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **"+ Create Credentials"** → **"OAuth client ID"**
3. If asked, configure the **OAuth consent screen**:
   - User type: **External**
   - App name: `AI Employee`
   - User support email: your email
   - Add your email as a test user
4. Back in Credentials, create OAuth client ID:
   - Application type: **Desktop app**
   - Name: `AI Employee Desktop`
5. Click **Create**
6. Click **"Download JSON"**
7. Save the downloaded file as `credentials.json` in your project root:

```bash
mv ~/Downloads/client_secret_*.json ~/Desktop/claude/fte/credentials.json
```

#### Step 4: First Run (Authenticate)

```bash
source .venv/bin/activate
python .claude/skills/gmail-watcher/scripts/gmail_poll.py
```

A browser window will open asking you to log in to Google and allow access. After you approve, a `token.json` file is created automatically. You only need to do this once.

#### Step 5: Verify

```bash
python .claude/skills/gmail-watcher/scripts/gmail_poll.py --minutes 60
```

You should see emails found and classified.

---

### 5.2 Twitter/X Setup

Twitter lets the AI Employee post tweets and check your timeline.

#### Step 1: Create Developer Account

1. Go to https://developer.x.com/
2. Sign in with your Twitter/X account
3. Click **"Sign up for Free Account"**
4. Fill in the description: `Personal AI assistant for automated social media management`
5. Accept terms and submit

#### Step 2: Get API Keys

1. Go to https://developer.x.com/en/portal/dashboard
2. An app may be auto-created. If not, click **"+ Create App"**
3. Go to your app → **"Keys and tokens"** tab
4. Under **Consumer Keys**: Click **"Regenerate"** to get:
   - **API Key** (Consumer Key)
   - **API Key Secret** (Consumer Secret)
5. Under **Authentication Tokens**: Click **"Generate"** to get:
   - **Access Token**
   - **Access Token Secret**

#### Step 3: Set Up User Authentication

1. In your app settings, click **"Set up"** under User authentication
2. Set:
   - App permissions: **Read and Write**
   - Type of App: **Web App**
   - Callback URL: `https://localhost:3000`
   - Website URL: your website or GitHub profile URL
3. Save

#### Step 4: Add to .env

Add these to your `.env` file:

```bash
TWITTER_API_KEY=your_consumer_key
TWITTER_API_SECRET=your_consumer_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
```

#### Step 5: Verify

```bash
source .venv/bin/activate
python3 -c "
import tweepy
auth = tweepy.OAuthHandler('YOUR_API_KEY', 'YOUR_API_SECRET')
auth.set_access_token('YOUR_ACCESS_TOKEN', 'YOUR_ACCESS_TOKEN_SECRET')
api = tweepy.API(auth)
print('Connected as:', api.verify_credentials().screen_name)
"
```

---

### 5.3 Facebook Setup

Facebook lets the AI Employee post to your Facebook Page.

#### Step 1: Create a Facebook Page

1. Go to https://www.facebook.com/pages/create
2. Choose **"Business or Brand"**
3. Enter your page name and category
4. Click **Create Page**
5. Note your **Page ID** (visible in the URL or Page settings → About)

#### Step 2: Create Meta Developer App

1. Go to https://developers.facebook.com/
2. Click **"My Apps"** → **"Create App"**
3. Select **"Other"** → **"Create an app without a use case"** (or "Business")
4. Name it: `AI Employee Pages`
5. Click **Create**

#### Step 3: Add Page Permissions

1. In your app dashboard, go to **"Use cases"** on the left sidebar
2. Click **"Add use case"**
3. Select **"Manage everything on your Page"** (or similar)
4. Click **Customize** and enable:
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_posts`

#### Step 4: Generate Access Token

1. Go to https://developers.facebook.com/tools/explorer/
2. Select your app: **"AI Employee Pages"**
3. Click **"Generate Access Token"**
4. Allow all permissions when prompted
5. Copy the **User Access Token**

#### Step 5: Get Page Access Token

In the Graph API Explorer, query:
```
YOUR_PAGE_ID?fields=id,name,access_token
```

The response contains the **Page Access Token**. Copy it.

#### Step 6: Add to .env

```bash
FACEBOOK_PAGE_ID=your_page_id
FACEBOOK_ACCESS_TOKEN=your_page_access_token
```

#### Important Notes

- Facebook Page Access Tokens are **short-lived** (expire in hours to days)
- You need to regenerate them periodically at the Graph API Explorer
- For a long-lived token, exchange it using the Facebook API (see Facebook docs for "long-lived tokens")

#### Step 7: Verify

```bash
source .venv/bin/activate
python3 -c "
import requests
token = 'YOUR_PAGE_ACCESS_TOKEN'
page_id = 'YOUR_PAGE_ID'
r = requests.get(f'https://graph.facebook.com/v19.0/{page_id}?fields=id,name&access_token={token}')
print(r.json())
"
```

---

### 5.4 WhatsApp Setup

WhatsApp uses Playwright (browser automation) to monitor WhatsApp Web.

#### Step 1: First Run

```bash
source .venv/bin/activate
python .claude/skills/whatsapp-watcher/scripts/whatsapp_monitor.py
```

#### Step 2: Scan QR Code

A Chromium browser window will open showing WhatsApp Web. Scan the QR code with your phone:
1. Open WhatsApp on your phone
2. Go to **Settings** → **Linked Devices**
3. Tap **"Link a Device"**
4. Scan the QR code on screen

#### Step 3: Session Saved

After scanning, the session is saved to `~/.whatsapp-watcher-session/`. You won't need to scan again unless the session expires.

#### Important Notes

- WhatsApp Web must be running (the session must be active) for the watcher to work
- The watcher checks for keywords like: `urgent`, `asap`, `invoice`, `payment`, `help`
- Messages matching keywords create task files in `Needs_Action/`

---

### 5.5 Odoo ERP Setup

Odoo is a free business management tool (invoicing, customer management, financial reports).

#### Step 1: Start Docker

```bash
sudo systemctl start docker
```

#### Step 2: Start Odoo Containers

```bash
cd ~/Desktop/claude/fte
DOCKER_HOST=unix:///var/run/docker.sock docker compose -f docker-compose.odoo.yml --env-file /dev/null up -d
```

This starts two containers:
- **fte_odoo_db** — PostgreSQL database (port 5434)
- **fte_odoo** — Odoo web application (port 8069)

First run downloads ~500MB of Docker images. Subsequent starts are instant.

#### Step 3: Create Odoo Database

Open your browser and go to: **http://localhost:8069**

If this is the first time, you'll see the database creation page:
- Master Password: `admin`
- Database Name: `fte_db`
- Email: `admin`
- Password: `admin`
- Language: English
- Country: Pakistan (or your country)
- Click **Create database**

OR create via command line:
```bash
curl -s -X POST http://localhost:8069/web/database/create \
  -d "master_pwd=admin&name=fte_db&login=admin&password=admin&lang=en_US&country_code=PK"
```

#### Step 4: Install Invoicing Module

Login to Odoo at http://localhost:8069 (admin/admin) and:
1. Go to **Apps** menu
2. Search for **"Invoicing"**
3. Click **Install**

OR install via Python:
```bash
source .venv/bin/activate
python3 -c "
import odoorpc
odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login('fte_db', 'admin', 'admin')
Module = odoo.env['ir.module.module']
ids = Module.search([('name', '=', 'account')])
Module.button_immediate_install(ids)
print('Invoicing module installed!')
"
```

#### Step 5: Add to .env

```bash
ODOO_HOST=localhost
ODOO_PORT=8069
ODOO_DB=fte_db
ODOO_USER=admin
ODOO_PASSWORD=admin
```

#### Step 6: Verify

```bash
source .venv/bin/activate
python3 -c "
import odoorpc
odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login('fte_db', 'admin', 'admin')
print('Connected to:', odoo.env.user.company_id.name)
"
```

#### Step 7: Access Odoo Web Interface

Open **http://localhost:8069** in your browser to:
- Create customers
- Create and manage invoices
- Record payments
- View financial reports

Login: `admin` / `admin`

#### Important Notes

- Odoo runs in Docker. If you restart your computer, start Docker first: `sudo systemctl start docker`
- Then start Odoo: `DOCKER_HOST=unix:///var/run/docker.sock docker compose -f docker-compose.odoo.yml --env-file /dev/null up -d`
- Your data persists in Docker volumes (survives container restarts)

---

## 6. Using Your AI Employee

### Starting Up

Every time you want to use your AI Employee:

```bash
# Step 1: Open terminal and navigate to project
cd ~/Desktop/claude/fte

# Step 2: Activate virtual environment
source .venv/bin/activate

# Step 3: Start Claude Code
claude
```

Now you're in Claude Code and can give commands to your AI Employee.

### Basic Workflow

1. **Check for new tasks**: Say `check my gmail`
2. **See what's pending**: Say `show my pending tasks`
3. **Process tasks**: Say `process needs action`
4. **Review flagged items**: Open `~/Documents/AI_Employee_Vault/Plans/` in your file manager
5. **Approve actions**: Move files from `Pending_Approval/` to `Approved/`
6. **Get reports**: Say `generate CEO briefing`

---

## 7. All Available Commands

Type these in Claude Code:

### Email Commands
| Command | What It Does |
|---------|-------------|
| `check my gmail` | Polls Gmail for new emails, creates tasks for important ones |
| `check gmail last 24 hours` | Checks emails from the last 24 hours |

### Task Management Commands
| Command | What It Does |
|---------|-------------|
| `show my pending tasks` | Lists all tasks in Needs_Action/ |
| `process needs action` | AI processes all pending tasks (archives junk, flags important) |
| `run orchestrator` | Runs the full pipeline (check all sources + process) |

### Financial Commands
| Command | What It Does |
|---------|-------------|
| `check odoo invoices` | Shows all invoices from Odoo ERP |
| `list invoices` | Same as above |
| `financial summary` | Shows revenue, expenses, receivables |

### Social Media Commands
| Command | What It Does |
|---------|-------------|
| `post to twitter "Your message"` | Drafts a tweet (needs your approval) |
| `post to facebook "Your message"` | Drafts a Facebook post (needs approval) |

### Reporting Commands
| Command | What It Does |
|---------|-------------|
| `generate CEO briefing` | Creates a weekly business report |
| `check service health` | Shows which services are up/down |

### System Commands
| Command | What It Does |
|---------|-------------|
| `check health` | Verifies all services (Gmail, Twitter, etc.) |
| `start scheduler` | Starts the automatic task scheduler |

---

## 8. Understanding the Vault

The vault is a folder at `~/Documents/AI_Employee_Vault/`. It's the AI Employee's brain — where it reads and writes everything.

### Folder Purposes

| Folder | Purpose | Who Writes Here |
|--------|---------|----------------|
| `Inbox/` | Drop files for AI to process | You (drop files here) |
| `Needs_Action/` | Tasks waiting to be processed | Watchers (Gmail, WhatsApp, Scheduler) |
| `Plans/` | AI's plans for handling tasks | AI Employee |
| `Pending_Approval/` | Sensitive actions waiting for your OK | AI Employee |
| `Approved/` | You approved this action | You (move files here) |
| `Done/` | Completed/archived tasks | AI Employee |
| `Briefings/` | CEO reports and summaries | AI Employee |
| `Logs/` | Audit trail (JSON format) | AI Employee |

### Important Files

| File | Purpose |
|------|---------|
| `Dashboard.md` | Overview of last run, stats, service status |
| `Company_Handbook.md` | Rules the AI follows (edit to customize behavior) |

### How to Approve an Action

When the AI needs your permission (e.g., posting to social media):

1. It creates a file in `Pending_Approval/`
2. Open the file and review it
3. If you agree: **Move the file to `Approved/`**
4. If you disagree: **Move the file to `Done/`** (dismisses it)

You can move files using your file manager (Nautilus) or terminal:
```bash
# Approve
mv ~/Documents/AI_Employee_Vault/Pending_Approval/some-file.md ~/Documents/AI_Employee_Vault/Approved/

# Dismiss
mv ~/Documents/AI_Employee_Vault/Pending_Approval/some-file.md ~/Documents/AI_Employee_Vault/Done/
```

---

## 9. Automatic Scheduling

The scheduler runs tasks automatically without you having to type commands.

### Starting the Scheduler

```bash
cd ~/Desktop/claude/fte
source .venv/bin/activate
nohup python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py > /dev/null 2>&1 &
```

### Default Schedule (Pakistan Standard Time)

| Time | Task | Frequency |
|------|------|-----------|
| 7:00 AM | Health check (verify all services) | Daily |
| 8:00 AM | Check Gmail for new emails | Daily |
| 8:15 AM | Process all pending tasks | Daily |
| 2:00 PM | Afternoon Gmail check | Daily |
| 2:15 PM | Afternoon task sweep | Daily |
| 8:00 PM | Evening Gmail check | Daily |
| 9:00 AM | Generate CEO Briefing | Mondays only |
| 10:00 AM | Social media weekly summary | Mondays only |

### Managing the Scheduler

```bash
# View all scheduled jobs
python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py --list

# Add a new job
python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py \
  --add --task-name "custom-task" --interval daily --time "10:00" \
  --description "My custom task"

# Check if scheduler is running
cat ~/Documents/AI_Employee_Vault/Logs/scheduler.pid

# Stop the scheduler
kill $(cat ~/Documents/AI_Employee_Vault/Logs/scheduler.pid)

# View scheduler logs
tail -20 ~/Documents/AI_Employee_Vault/Logs/scheduler.jsonl
```

### Auto-Start on Boot

To make the scheduler start when you turn on your computer:

```bash
# Option 1: Using crontab
crontab -e
# Add this line:
@reboot cd /home/YOUR_USERNAME/Desktop/claude/fte && source .venv/bin/activate && python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py &

# Option 2: Using PM2 (if installed)
npm install -g pm2
pm2 start .claude/skills/daily-scheduler/scripts/scheduler_daemon.py --interpreter python3 --name ai-scheduler
pm2 save
pm2 startup
```

---

## 10. The Approval System

The AI Employee uses a **Human-In-The-Loop (HITL)** system to prevent mistakes.

### Three Levels

| Level | Examples | What Happens |
|-------|----------|-------------|
| **Routine** | Reading emails, listing invoices, health checks | Executes automatically |
| **Sensitive** | Posting to social media, sending emails | Creates approval file, waits for you |
| **Critical** | Creating invoices, registering payments | Creates approval file + logs extra audit entry |

### DRY_RUN Mode (Default: ON)

By default, all external actions are in **dry-run mode** — they simulate the action but don't actually do it. This prevents accidents while you're learning.

To enable real actions:
```bash
export DRY_RUN=false
```

To go back to safe mode:
```bash
export DRY_RUN=true
```

---

## 11. Viewing with Obsidian (Optional)

Obsidian is a free app that makes your vault files look nice. It's optional — you can use any text editor or file manager instead.

### Setup

1. Download and install Obsidian from https://obsidian.md
2. Open Obsidian
3. Click **"Open folder as vault"**
4. Navigate to `/home/YOUR_USERNAME/Documents/AI_Employee_Vault`
5. Select the **folder** (don't click into it) and click **Open**

### What You'll See

- All `.md` files rendered as formatted pages
- Folder navigation on the left
- Dashboard.md as your home page
- Briefings folder for CEO reports

### Alternative: Just Use Your File Manager

Open `~/Documents/AI_Employee_Vault/` in Nautilus (Ubuntu's file manager). Double-click any `.md` file to read it in a text editor. This works perfectly fine.

---

## 12. Troubleshooting

### Gmail Issues

| Problem | Solution |
|---------|----------|
| "Token expired" | Delete `token.json` and run `gmail_poll.py` again to re-authenticate |
| "credentials.json not found" | Download OAuth2 credentials from Google Cloud Console |
| "403 Forbidden" | Enable Gmail API in Google Cloud Console |
| "No emails found" | Try `--minutes 1440` to check last 24 hours |

### Twitter Issues

| Problem | Solution |
|---------|----------|
| "401 Unauthorized" | Regenerate API keys at developer.x.com |
| "403 Forbidden" | Set app permissions to "Read and Write" |
| "Account suspended" | Create new account and regenerate keys |

### Facebook Issues

| Problem | Solution |
|---------|----------|
| "Token expired" | Go to developers.facebook.com/tools/explorer/ and generate new token |
| "No Page returned" | Query `PAGE_ID?fields=id,name,access_token` directly |
| "Permissions error" | Add `pages_manage_posts` permission to your app |

### Odoo Issues

| Problem | Solution |
|---------|----------|
| "Connection refused" | Start Docker: `sudo systemctl start docker` then start containers |
| "Database not found" | Create database at http://localhost:8069 |
| "Login failed" | Default credentials: admin / admin |
| "Port already in use" | Change port in `docker-compose.odoo.yml` |

### Scheduler Issues

| Problem | Solution |
|---------|----------|
| "Already running" | Delete PID file: `rm ~/Documents/AI_Employee_Vault/Logs/scheduler.pid` |
| "No jobs scheduled" | Check `config/schedules.json` has jobs with `"enabled": true` |
| "Scheduler stopped" | Restart: `nohup python scheduler_daemon.py > /dev/null 2>&1 &` |

### General Issues

| Problem | Solution |
|---------|----------|
| "Module not found" | Activate venv: `source .venv/bin/activate` |
| "Vault not found" | Run `python src/setup_vault.py` to create it |
| "Permission denied" | Check file permissions: `chmod -R 755 ~/Documents/AI_Employee_Vault` |

---

## 13. Environment Variables Reference

Create a `.env` file in the project root with these variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VAULT_PATH` | No | `~/Documents/AI_Employee_Vault` | Path to your vault folder |
| `DROP_FOLDER` | No | `~/Desktop/DropForAI` | Folder monitored for file drops |
| `DRY_RUN` | No | `true` | Set to `false` for real actions |
| `TWITTER_API_KEY` | For Twitter | — | Twitter Consumer Key |
| `TWITTER_API_SECRET` | For Twitter | — | Twitter Consumer Secret |
| `TWITTER_ACCESS_TOKEN` | For Twitter | — | Twitter Access Token |
| `TWITTER_ACCESS_TOKEN_SECRET` | For Twitter | — | Twitter Access Token Secret |
| `FACEBOOK_PAGE_ID` | For Facebook | — | Your Facebook Page ID |
| `FACEBOOK_ACCESS_TOKEN` | For Facebook | — | Facebook Page Access Token |
| `ODOO_HOST` | For Odoo | `localhost` | Odoo server hostname |
| `ODOO_PORT` | For Odoo | `8069` | Odoo server port |
| `ODOO_DB` | For Odoo | — | Odoo database name |
| `ODOO_USER` | For Odoo | `admin` | Odoo login username |
| `ODOO_PASSWORD` | For Odoo | — | Odoo login password |

---

## 14. FAQ

### Q: Does my computer need to be on 24/7?

**A:** The AI Employee only works when your computer is on and the scheduler is running. If you turn off your computer, it stops. When you turn it back on, start the scheduler again and it will catch up.

### Q: Will it send emails or post tweets without asking me?

**A:** No. By default, everything is in **dry-run mode** (simulates but doesn't act). Even with dry-run off, sensitive actions (emails, social posts) require your explicit approval by moving a file to the `Approved/` folder.

### Q: Will it spend my money?

**A:** Never. All payment-related actions are **critical level** — they always require your explicit approval AND are logged with extra audit trails.

### Q: Can I customize what the AI considers important?

**A:** Yes. Edit `~/Documents/AI_Employee_Vault/Company_Handbook.md`. This file contains the rules the AI follows for classifying emails, handling tasks, and deciding what needs your attention.

### Q: Do I need Obsidian?

**A:** No. Obsidian is just a viewer for the vault files. You can use any text editor or your file manager to view and edit files.

### Q: How do I stop the AI Employee?

**A:** Close the Claude Code terminal. To stop the scheduler: `kill $(cat ~/Documents/AI_Employee_Vault/Logs/scheduler.pid)`

### Q: What if a service goes down (e.g., Gmail stops working)?

**A:** The circuit breaker system handles this automatically. If a service fails 3 times in a row, it's marked as "degraded" and the AI skips it for 5 minutes before trying again. Other services continue working normally.

### Q: How do I update the AI Employee?

**A:**
```bash
cd ~/Desktop/claude/fte
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt  # if it exists
```

### Q: Where are my logs?

**A:** All logs are in `~/Documents/AI_Employee_Vault/Logs/` as `.jsonl` files:
- `gmail.jsonl` — Email polling activity
- `orchestrator.jsonl` — Task processing decisions
- `mcp_social.jsonl` — Social media actions
- `mcp_odoo.jsonl` — Odoo ERP queries
- `scheduler.jsonl` — Scheduler triggers
- `ralph.jsonl` — Retry attempts

### Q: Is my data safe?

**A:** Yes. Everything is stored locally on your computer. No data is sent to any cloud service except when you explicitly use external APIs (Gmail, Twitter, etc.). API credentials are stored in `.env` (which is in `.gitignore` and never committed to Git).

---

## Quick Reference Card

```
DAILY USE:
  claude                          # Start AI Employee
  check my gmail                  # Check emails
  show my pending tasks           # See what needs attention
  process needs action            # Let AI handle tasks
  generate CEO briefing           # Weekly business report
  check service health            # Verify services

STARTUP (after reboot):
  sudo systemctl start docker     # Start Docker (for Odoo)
  cd ~/Desktop/claude/fte
  source .venv/bin/activate
  nohup python .claude/skills/daily-scheduler/scripts/scheduler_daemon.py > /dev/null 2>&1 &
  claude                          # Start Claude Code

VIEW YOUR VAULT:
  Open ~/Documents/AI_Employee_Vault/ in file manager
  OR open in Obsidian

APPROVE AN ACTION:
  Move file from Pending_Approval/ to Approved/

DISMISS AN ACTION:
  Move file from Pending_Approval/ to Done/
```
