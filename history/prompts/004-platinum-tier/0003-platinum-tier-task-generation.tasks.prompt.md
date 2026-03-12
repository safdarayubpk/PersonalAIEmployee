---
id: "0003"
title: Platinum Tier Task Generation
stage: tasks
date: 2026-03-11
surface: agent
model: claude-opus-4-6
feature: 004-platinum-tier
branch: main
user: safdarayub
command: /sp.tasks
labels: ["tasks", "platinum-tier", "implementation-planning"]
links:
  spec: specs/004-platinum-tier/spec.md
  ticket: null
  adr: history/adr/0009-0016
  pr: null
files:
  - specs/004-platinum-tier/tasks.md
tests:
  - none
---

## Prompt

/sp.tasks — Generate implementation tasks for Platinum tier feature (004-platinum-tier) based on spec.md, plan.md, data-model.md, and research.md.

## Response snapshot

Generated 48 tasks across 12 phases organized by user story priority:

- **Phase 1 (Setup)**: 5 tasks — role_gate.py, correlation.py update, vault_helpers.py update, vault folder structure, .env.example
- **Phase 2 (Foundational)**: 5 tasks — git_sync.py, claim_move.py, unit tests for role_gate/git_sync/claim_move
- **Phase 3 (US6 Secrets)**: 3 tasks — pre-commit hook, .gitignore verification, installation docs
- **Phase 4 (US2 Git Sync)**: 3 tasks — sync logging, cloud PM2 config, local PM2 config update
- **Phase 5 (US3 Role Gating)**: 6 tasks — base_server.py, email/social/odoo server gates, action-level gates, actions.json
- **Phase 6 (US1 Email Triage)**: 4 tasks — gmail_poll.py role-aware, approval_watcher.py, scheduler role-aware, e2e test
- **Phase 7 (US4 Claim-by-Move)**: 3 tasks — orchestrator integration (cloud + local), complete_file integration
- **Phase 8 (US5 Dashboard)**: 4 tasks — dashboard_merger.py, cloud/local integration, unit tests
- **Phase 9 (US8 Daemon)**: 3 tasks — PM2 config finalization, health monitor update, first-boot setup docs
- **Phase 10 (US7 Correlation)**: 4 tasks — frontmatter generation, preservation on move, JSONL logging, e2e verification
- **Phase 11 (Rejection/Stale)**: 3 tasks — rejection_handler.py, stale_detector.py, unit tests
- **Phase 12 (Polish)**: 5 tasks — Gold regression, security scan, cloud deployment, live demo, quickstart update

Critical path: Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 6 → Phase 12

## Outcome

- ✅ Impact: 48 tasks covering all 8 user stories, organized for incremental delivery with MVP at Phase 6
- 🧪 Tests: 6 test tasks included (unit + integration + e2e)
- 📁 Files: 1 new file (specs/004-platinum-tier/tasks.md)
- 🔁 Next prompts: /sp.implement to begin Phase 1 execution
- 🧠 Reflection: Secrets isolation (US6) deliberately ordered before Git Sync (US2) — safety-first approach. Claim-by-move and dashboard merge are P2 because MVP works without them (with minor duplicate risk).

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): All tasks have checkbox + ID + story label + file path (PASS), phases match user story priority order (PASS), dependencies form valid DAG (PASS)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Consider splitting Phase 5 (Role Gating) into server-level and action-level sub-phases for finer granularity
