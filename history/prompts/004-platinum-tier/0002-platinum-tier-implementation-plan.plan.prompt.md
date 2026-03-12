---
id: "0002"
title: "Platinum Tier Implementation Plan"
stage: plan
date: "2026-03-11"
surface: agent
model: claude-opus-4-6
feature: 004-platinum-tier
branch: 004-platinum-tier
user: safdarayub
command: /sp.plan
labels: ["platinum", "cloud-hybrid", "implementation-plan", "architecture"]
links:
  spec: specs/004-platinum-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/004-platinum-tier/plan.md
  - specs/004-platinum-tier/research.md
  - specs/004-platinum-tier/data-model.md
  - specs/004-platinum-tier/quickstart.md
tests:
  - "Constitution check: all 7 principles + .gitignore gate PASS"
  - "Post-design re-check: all gates remain PASS"
---

## Prompt

Create a complete, detailed technical implementation plan for the Platinum tier upgrade as described in spec.md while strictly following constitution v1.3.0. The plan must cover: Exact folder structure on both cloud VM and local, FTE_ROLE detection and enforcement, Git sync service, Claim-by-move implementation, Update files merging for Dashboard.md, Role-aware changes to existing watchers and MCP servers, PM2 daemon configuration, Pre-commit hook for secrets isolation, Correlation ID generation and propagation, Cloud-init and first-boot setup on VM, Testing strategy for the offline-tolerant email demo, Backward compatibility with Gold tier. Include file paths, environment variables, cron schedules, and clear responsibilities for cloud vs local. Prioritize safety and no-regression.

## Response snapshot

Generated comprehensive Platinum tier implementation plan with:
- 7 new source files: role_gate.py, git_sync.py, claim_move.py, dashboard_merger.py, approval_watcher.py, rejection_handler.py, stale_detector.py
- 10 existing files modified: vault_helpers.py, correlation.py, setup_vault.py, base_server.py, email_server.py, odoo_server.py, gmail_poll.py, scheduler_daemon.py, ecosystem.config.js, actions.json
- 1 new config file: ecosystem.cloud.config.js (cloud PM2 config)
- 1 new hook: pre-commit (secrets validation)
- 6 new test files across unit and integration
- 23-step implementation dependency graph in 6 phases (A-F)
- Full environment variable matrix (10 vars, cloud vs local values)
- Complete vault folder structure with domain subfolders
- Cloud/local architecture diagrams with data flow
- 7 research decisions documented with rationale and alternatives
- 4-item risk register with mitigations
- Backward compatibility strategy ensuring FTE_ROLE=local = Gold behavior

## Outcome

- ✅ Impact: Technical plan ready for task generation. Covers all 35 FRs from spec, all 10 SCs, and all constitution v1.3.1 principles.
- 🧪 Tests: Constitution gates all PASS (pre-design and post-design checks)
- 📁 Files: 4 files created (plan.md, research.md, data-model.md, quickstart.md)
- 🔁 Next prompts: /sp.tasks (recommended next step to generate implementation tasks)
- 🧠 Reflection: Plan is detailed but achievable. The 23-step dependency graph should be followed strictly to avoid regressions. Gmail OAuth on headless VM remains the highest-risk item. E2.1.Micro memory constraints may force simplification if all 3 cloud services can't run simultaneously.

## Evaluation notes (flywheel)

- Failure modes observed: None — spec was comprehensive, codebase exploration revealed clear integration points
- Graders run and results (PASS/FAIL): Constitution check PASS (all gates, both pre and post-design)
- Prompt variant (if applicable): Standard /sp.plan with detailed user input covering 12 specific topics
- Next experiment (smallest change to try): Validate Gmail read-only token transfer works headlessly before Phase E deployment
