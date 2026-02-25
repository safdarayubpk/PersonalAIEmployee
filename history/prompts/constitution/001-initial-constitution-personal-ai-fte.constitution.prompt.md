---
id: 001
title: Initial Constitution Personal AI FTE
stage: constitution
date: 2026-02-24
surface: agent
model: claude-opus-4-6
feature: none
branch: master
user: safdarayub
command: /sp.constitution
labels: ["constitution", "hackathon", "ai-employee", "governance"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
tests:
---

## Prompt

/sp.constitution
Project: Personal AI Employee – Autonomous Digital FTE (Full-Time Equivalent) for 2026 Hackathon

Core principles:
- Local-first and privacy-centric: All sensitive data (emails, WhatsApp sessions, bank tokens, personal/business documents) must remain on-device; no cloud storage or transmission unless explicitly approved in Platinum tier.
- Human-in-the-loop (HITL) safety: No autonomous execution of financial, legal, emotional, medical, or high-risk actions; sensitive operations must write to Pending_Approval folder and wait for human move to Approved folder.
- Proactive autonomy: The agent must watch for events (watchers) and act without constant user prompting, using Ralph Wiggum loop for task persistence until completion or max iterations.
- Modularity and extensibility: Tier-based progression (Bronze → Silver → Gold → Platinum); each tier builds incrementally on the previous one.
- Cost-efficiency mindset: Demonstrate massive reduction in cost-per-task vs human FTE (target 85–90% savings); emphasize 24/7 availability vs human 40 h/week.

Key standards:
- All code and configuration must be traceable to the official hackathon document (Personal AI Employee Hackathon 0).
- Tech stack adherence: Python 3.13+, Claude Code 2.1.x as reasoning engine, Obsidian (v1.11.x+) as markdown vault, Playwright for browser automation, Watchdog for filesystem, MCP servers for actions, PM2/supervisord for process management.
- Security & ethics: No storage of secrets in vault or git; use .env + keychain; never simulate or execute real payments/emails without dry-run flag and approval; log all actions to Logs folder.
- Documentation clarity: Every generated file must include clear comments, purpose header, and reference to constitution/tier.
- Reproducibility: All watchers, orchestrators, and MCP servers must be daemonizable and restartable; include setup scripts and pm2/systemd examples.
- Testing rigor: Each tier must include at least one manual test scenario (e.g., drop file → watcher → Needs_Action .md → Claude process → Done move).

Constraints:
- Vault location: /home/safdarayub/Documents/AI_Employee_Vault (absolute path must be respected in all code)
- Tier scope limits: Bronze = basic vault + 1 watcher + read/write; Silver = multiple watchers + MCP + scheduling; Gold = full integration (Odoo, social posting, CEO briefing); Platinum = cloud hybrid + 24/7 VM + Git sync
- No external cloud dependencies before Platinum tier
- Maximum iteration loops: 10 per Ralph Wiggum cycle unless overridden
- Output format: All generated files in markdown with frontmatter where appropriate

Success criteria:
- Vault contains Dashboard.md, Company_Handbook.md, and tier-specific folders/files
- At least one watcher successfully creates Needs_Action markdown files
- Claude Code can read/write vault files when cwd is set to vault path
- Human approval flow works (Pending_Approval → move to Approved triggers action)
- No unhandled exceptions in watchers/orchestrator after 10-minute test run
- All tiers build incrementally without breaking previous functionality
- Final Gold tier produces Monday Morning CEO Briefing autonomously

## Response snapshot

Created constitution v1.0.0 for Personal AI Employee project. Established 5 core principles: (I) Local-First & Privacy-Centric, (II) Human-in-the-Loop Safety, (III) Proactive Autonomy, (IV) Modularity & Extensibility, (V) Cost-Efficiency Mindset. Added Key Standards & Technical Constraints section (tech stack, security, reproducibility), Development Workflow & Testing section, Success Criteria checklist, and Governance rules with semantic versioning policy. All templates verified compatible — no updates needed. Constitution written to `.specify/memory/constitution.md`.

## Outcome

- ✅ Impact: Project governance established; all future specs/plans/tasks governed by these 5 principles
- 🧪 Tests: N/A (governance document)
- 📁 Files: .specify/memory/constitution.md (created)
- 🔁 Next prompts: /sp.specify to create first feature spec (likely Bronze tier), /sp.plan for architecture
- 🧠 Reflection: User provided comprehensive input — all placeholders resolved without ambiguity

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Manual validation PASS — no unresolved placeholders, version correct, dates ISO format
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
