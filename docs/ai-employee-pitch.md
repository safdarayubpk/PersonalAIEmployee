# Personal AI Employee — Project Overview

> A fully autonomous AI assistant that manages my business operations 24/7 — emails, WhatsApp, invoicing, social media, and weekly reporting — with human-in-the-loop safety.

---

## What Is It?

I built a **Personal AI Employee** — an autonomous system that monitors my communication channels, manages my business operations, and takes action on my behalf — while keeping me in control of sensitive decisions.

It runs locally and on a cloud VM, works 24/7, and handles tasks that would normally take 2-3 hours daily.

---

## What It Can Do

### 1. Email Management
- Monitors Gmail inbox automatically (3x daily)
- Reads, sends, and manages emails via natural language
- "Send email to client about project update" — AI drafts, I approve, it sends

### 2. WhatsApp Monitoring
- Watches WhatsApp Web 24/7 using browser automation (Playwright)
- Classifies messages by urgency (payment, meeting, casual)
- Creates action items for important messages, ignores noise

### 3. ERP Integration (Odoo)
- Connected to self-hosted Odoo 19 ERP
- Lists invoices, creates new ones, registers payments
- Pulls financial summaries for reporting

### 4. Social Media Management
- Posts to Facebook Page automatically
- AI drafts content based on topic, I approve before publishing
- Tracks post history and generates weekly social media reports

### 5. CEO Briefing (Weekly Report)
- Auto-generates every Monday at 9 AM
- Aggregates: financials (Odoo), completed tasks, social media activity
- Identifies bottlenecks and gives proactive suggestions

### 6. Smart Scheduling
- 8 automated recurring jobs (Gmail checks, inbox sweeps, reports)
- Cron-based scheduling with APScheduler
- Creates task files that feed into the processing pipeline

### 7. Health Monitoring
- Tracks 5 external services (Gmail, Facebook, Instagram, Twitter, Odoo)
- Circuit breaker pattern — auto-degrades on failures, auto-recovers
- Prevents cascading failures across the system

---

## Architecture

```
[Gmail]  [WhatsApp]  [Filesystem]  [Scheduler]
    \         |          |           /
     \        |          |          /
      v       v          v         v
    ┌─────────────────────────────────┐
    │     Central Orchestrator        │
    │  (Triage, Queue, Risk Check)    │
    └──────────────┬──────────────────┘
                   │
         ┌─────────┼─────────┐
         v         v         v
    [Auto-Execute] [HITL]  [Block]
     (Read ops)   (Email)  (Payment)
                   (Post)  (Legal)
```

### The Loop
1. **Watchers** monitor inputs (Gmail, WhatsApp, filesystem)
2. New items land as markdown files in `Needs_Action/`
3. **Orchestrator** triages and classifies risk
4. **Safe actions** execute automatically
5. **Sensitive actions** require my approval
6. **Critical actions** are blocked until I confirm
7. Everything is logged for audit

---

## Safety Model (Human-in-the-Loop)

| Risk Level | Example | What Happens |
|---|---|---|
| **Routine** | Read emails, list invoices | Auto-executes |
| **Sensitive** | Send email, post to social | I approve first |
| **Critical** | Register payment, delete data | Blocked until I confirm |

No action is taken without appropriate safety checks. The system is designed to **assist, not replace** human judgment on important decisions.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.13+ |
| **AI** | Claude (Anthropic) via Claude Code CLI |
| **Communication** | MCP (Model Context Protocol) servers |
| **Process Manager** | PM2 (auto-restart, logging) |
| **Browser Automation** | Playwright + Chromium (WhatsApp) |
| **ERP** | Odoo 19 Community (Docker) |
| **Email** | Gmail API (OAuth2) |
| **Social Media** | Facebook Graph API, Twitter API v2 |
| **Scheduling** | APScheduler (cron-based) |
| **Knowledge Base** | Obsidian vault (markdown + YAML frontmatter) |
| **Infrastructure** | Local machine + Oracle Cloud VM (Always Free tier) |
| **Version Control** | Git + GitHub (private repo) |

---

## Key Design Decisions

1. **Markdown as Database** — All tasks, logs, and reports are markdown files in an Obsidian vault. Human-readable, version-controlled, no database dependency.

2. **MCP Protocol** — Each capability (email, social, ERP) is a separate MCP server. Modular, testable, independently deployable.

3. **Circuit Breaker Pattern** — If an external service fails 3 times, the system stops calling it for 5 minutes. Prevents cascading failures.

4. **Role-Based Execution** — Cloud VM can only read and create drafts. Local machine executes with approval. Prevents unauthorized actions.

5. **Dry-Run by Default** — Every action runs in preview mode first. Must explicitly enable live mode.

---

## Development Approach

- **Spec-Driven Development (SDD)** — Every feature starts with a specification, then plan, then tasks, then implementation
- **4-Tier Architecture** — Bronze (filesystem) → Silver (multi-source) → Gold (MCP + safety) → Platinum (cloud deployment)
- **Prompt History Records** — Every development decision is recorded for traceability
- **Architecture Decision Records** — Significant decisions documented with rationale

---

## Results

- **3+ hours/day saved** on email triage, WhatsApp monitoring, and reporting
- **Zero missed important messages** — urgency classification catches everything
- **Automated weekly reporting** — CEO briefing generated without manual effort
- **Safe by design** — no accidental emails sent, no unauthorized payments

---

## What Makes It Different

| Traditional Automation | My AI Employee |
|---|---|
| Rule-based (if-then) | AI understands intent and context |
| Separate tools for each task | One system handles everything |
| Breaks when inputs change | Adapts to new message formats |
| No safety controls | 3-tier risk classification |
| Manual monitoring needed | Self-healing with circuit breakers |
| Fixed schedules only | Natural language + scheduled |

---

## Live Demo (What I Can Show)

1. "Post to Facebook about AI tips" → AI drafts → I approve → posted live
2. "Check my email" → pulls latest Gmail inbox
3. "Send email to [address]" → drafts and sends
4. "Generate CEO briefing" → full business report in seconds
5. "Check service health" → all 5 services status
6. WhatsApp watcher running → detecting messages in real-time

---

## Elevator Pitch (30 Seconds)

> "I built a Personal AI Employee that monitors my Gmail, WhatsApp, and ERP 24/7 — it triages messages by urgency, posts to social media, generates weekly CEO briefings, and handles invoicing — all with human-in-the-loop safety so nothing sensitive happens without my approval. It's built with Python, Claude AI, and runs on a free Oracle Cloud VM."

---

## 2-Minute Pitch (For Interviews)

> "The problem I solved is that business owners spend 3+ hours daily on repetitive tasks — checking emails, reading WhatsApp, creating invoices, posting on social media.
>
> I built an autonomous AI system that handles all of this. It uses watchers that monitor Gmail and WhatsApp, classifies messages by urgency, and routes them through a central orchestrator. Safe actions execute automatically, sensitive ones need my approval.
>
> The tech stack is Python, Claude AI via MCP protocol, Playwright for browser automation, Odoo for ERP, and it runs on Oracle Cloud's Always Free tier.
>
> The key differentiator is the 3-tier safety model — routine, sensitive, and critical — so the AI never takes dangerous actions without human consent.
>
> It also generates a weekly CEO Briefing every Monday that pulls financials from Odoo, completed tasks, social media stats, and identifies bottlenecks — giving me a full business snapshot without lifting a finger.
>
> I developed it using Spec-Driven Development — every feature started as a specification, then an architecture plan, then testable tasks. The system grew through 4 tiers: Bronze for basic file watching, Silver for multi-source orchestration, Gold for MCP servers with circuit breakers, and Platinum for cloud deployment with PM2 process management.
>
> The result: 3+ hours saved daily, zero missed important messages, and a system that runs itself while keeping me in control."

---

## Future Roadmap

- Instagram posting (needs image hosting solution)
- Twitter posting (needs paid API plan)
- LinkedIn integration
- Voice commands via mobile
- Multi-business support (manage multiple clients)

---

## Contact

**Safdar Ayub**
- GitHub: [Project Repository]
- LinkedIn: [Your Profile]
- Email: safdarayub@gmail.com
- Facebook: Safdar Ayub - AI & Tech

---

*Built with Claude (Anthropic), Python, and a vision for autonomous business management.*
