---
id: 003
title: Create Process Needs Action Skill
stage: general
date: 2026-02-24
surface: agent
model: claude-opus-4-6
feature: none
branch: master
user: safdarayub
command: skill-creator
labels: ["skill", "needs-action", "vault", "bronze-tier", "automation"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .claude/skills/process-needs-action/SKILL.md
  - .claude/skills/process-needs-action/references/vault-conventions.md
  - /home/safdarayub/Documents/AI_Employee_Vault/process_needs_action.md
tests:
---

## Prompt

Use skill-creator to make a new skill named "process_needs_action". This skill should: use vault_interact to list .md files in Needs_Action/, read each file, follow Company_Handbook.md rules, create Plan.md in Plans/, classify low-risk (execute + move to Done/) vs high-risk (write to Pending_Approval/), log to Logs/, update Dashboard.md. Create process_needs_action.md in vault root.

## Response snapshot

Used skill-creator workflow: ran init_skill.py to scaffold process-needs-action in .claude/skills/, wrote SKILL.md with 5-step workflow (load rules → list files → process each → log → update dashboard), created references/vault-conventions.md with Needs_Action format and risk classification table, removed unused example files, validated skill ("Skill is valid!"). Created vault folder structure (Needs_Action/, Done/, Pending_Approval/, Approved/, Plans/, Logs/) and process_needs_action.md in vault root as quick-reference runner doc. vault_interact does not exist yet — skill falls back to Claude's native Read/Write/Glob tools.

## Outcome

- ✅ Impact: New skill created for autonomous Needs_Action processing with risk-based routing
- 🧪 Tests: Skill validation passed via quick_validate.py
- 📁 Files: SKILL.md, references/vault-conventions.md, vault process_needs_action.md, 6 vault folders created
- 🔁 Next prompts: Create vault_interact skill, create Company_Handbook.md, create Dashboard.md, test with a sample Needs_Action file
- 🧠 Reflection: vault_interact referenced by user does not exist — skill gracefully falls back to native tools; vault was completely empty so created folder structure as prerequisite

## Evaluation notes (flywheel)

- Failure modes observed: vault_interact skill missing — documented as fallback
- Graders run and results (PASS/FAIL): quick_validate.py PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Create a test Needs_Action file and run the skill end-to-end
