---
id: 005
title: Create Check Process Needs Action Skill
stage: general
date: 2026-02-24
surface: agent
model: claude-opus-4-6
feature: none
branch: master
user: safdarayub
command: skill-creator
labels: ["skill", "orchestrator", "bronze-tier", "proactive", "automation"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .claude/skills/check-and-process-needs-action/SKILL.md
  - /home/safdarayub/Documents/AI_Employee_Vault/check_and_process_needs_action.md
tests:
---

## Prompt

Use skill-creator to create a new Agent Skill named "check_and_process_needs_action". Proactive Bronze-tier orchestrator: checks Needs_Action/ for pending .md files, processes up to 5 per run via process-needs-action skill, routes low-risk to Done/ and high-risk to Pending_Approval/, updates Dashboard.md, logs errors. Uses vault_interact for all file ops. Create vault root file.

## Response snapshot

Used skill-creator workflow: ran init_skill.py, wrote SKILL.md with 3-step workflow (check → process each → update dashboard), ASCII flowchart, 3 worked examples (empty, one low-risk, two mixed-risk), limits/guards section (max 5, no deletion, error isolation, safe defaults). Removed all scaffold files. Validated: "Skill is valid!" Created check_and_process_needs_action.md in vault root. This skill completes the Bronze tier skill chain: vault_interact → process-needs-action → check-and-process-needs-action.

## Outcome

- ✅ Impact: Bronze tier skill chain complete — three skills compose into a full autonomous loop
- 🧪 Tests: quick_validate.py PASS
- 📁 Files: SKILL.md, vault root check_and_process_needs_action.md
- 🔁 Next prompts: Create Company_Handbook.md and Dashboard.md, drop a test file into Needs_Action/, run "check and process needs action" end-to-end
- 🧠 Reflection: Three skills now form a clean dependency chain: vault_interact (low-level IO) → process-needs-action (per-file triage) → check-and-process-needs-action (batch orchestrator)

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): quick_validate.py PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): End-to-end test with a sample Needs_Action file
