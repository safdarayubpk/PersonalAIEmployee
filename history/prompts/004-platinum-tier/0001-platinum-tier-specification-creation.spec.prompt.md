---
id: "0001"
title: "Platinum Tier Specification Creation"
stage: spec
date: "2026-03-11"
surface: agent
model: claude-opus-4-6
feature: 004-platinum-tier
branch: 004-platinum-tier
user: safdarayub
command: /sp.specify
labels: ["platinum", "cloud-hybrid", "specification", "tier-upgrade"]
links:
  spec: specs/004-platinum-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/004-platinum-tier/spec.md
  - specs/004-platinum-tier/checklists/requirements.md
tests:
  - "Spec quality checklist: all items PASS"
---

## Prompt

Upgrade the existing Personal AI Employee project (safdarayubpk/PersonalAIEmployee) from Gold tier to full Platinum tier as defined in the Panaversity Hackathon 0 blueprint.

Current state:
- Local machine: laptop with full Gold-tier code, vault, and Claude Code session
- Cloud VM: live at public IP 141.145.146.17, Ubuntu 24.04.4 LTS, user ubuntu
- Repo cloned on VM: safdarayubpk/PersonalAIEmployee at ~/AI_Employee_Vault
- Git sync verified: commit/push from VM → pull locally works both directions
- Python venv on VM: ~/fte-env (Python 3.12.3 + pip 26.0.1)
- Installed on VM: python3-venv, nodejs, npm, git, curl, unzip, build-essential
- Constitution updated to v1.3.0 with Platinum hybrid principles (cloud draft-only, local execute, git file-based delegation, claim-by-move, FTE_ROLE gating, correlation IDs, secrets never synced)

Target audience: Hackathon judges, Panaversity faculty/students, and small business owners who want a reliable, 24/7 autonomous AI employee that continues working even when the owner's laptop is off, asleep, or disconnected for hours/days.

Core focus:
- Achieve true always-on behavior via the cloud VM at 141.145.146.17 (Ubuntu 24.04).
- Implement strict secure domain ownership split between Cloud (draft/read-only) and Local (approve/execute/high-security).
- Use git-based vault synchronization for file-based delegation only (markdown, plans, approvals, updates — no secrets).
- Preserve and enhance all existing Gold-tier safety (HITL approval gates, risk-based routing, never autonomous payments/emotional/legal actions).

Success criteria for passing Platinum:
1. The system runs 24/7 on cloud VM when local laptop is offline.
2. Cloud agent detects new events (e.g. incoming Gmail) → reasons → generates drafts → writes structured approval request files to shared vault folders.
3. When local machine comes back online → local agent detects pending approval files → user reviews/moves to /Approved/ → local executes real action via existing MCP servers (email send, social post, etc.).
4. End-to-end offline-tolerant demo works.
5. Vault sync uses git only, never syncs secrets.
6. Claim-by-move rule prevents duplicate processing.
7. Single-writer rule for Dashboard.md.
8. Odoo Community on cloud VM with draft-only access.
9. No regression from Gold-tier features.
10. Security boundaries absolute.

## Response snapshot

Generated comprehensive Platinum tier specification with:
- 8 user stories (4x P1, 3x P2, 1x P3) covering: always-on email triage, git-based vault sync, FTE_ROLE gating, claim-by-move concurrency, single-writer dashboard, secrets isolation, correlation ID tracking, and cloud daemon operation
- 30 functional requirements organized into 9 categories: git sync engine, role gating, claim-by-move, single-writer dashboard, secrets isolation, correlation IDs, vault folder structure, cloud daemon management, and approval flow
- 10 measurable success criteria (8hr offline, 5min draft visibility, zero secrets in git, zero duplicates, 95% uptime, etc.)
- 6 edge cases with resolutions
- 4 key entities defined
- 6 assumptions documented
- 7 explicit non-goals
- Quality checklist: all items PASS, zero NEEDS CLARIFICATION markers

## Outcome

- ✅ Impact: Feature spec ready for planning phase. Defines the full Platinum tier upgrade scope.
- 🧪 Tests: Spec quality checklist passed all items (content quality, requirement completeness, feature readiness)
- 📁 Files: 2 files created (spec.md, checklists/requirements.md)
- 🔁 Next prompts: /sp.clarify (optional) or /sp.plan (recommended next step)
- 🧠 Reflection: Spec is comprehensive but large (30 FRs). Plan phase should identify implementation order and dependencies carefully. Gmail read-only OAuth on cloud VM is an assumption that needs validation during planning.

## Evaluation notes (flywheel)

- Failure modes observed: None — user provided extremely detailed input, minimizing ambiguity
- Graders run and results (PASS/FAIL): Quality checklist PASS (all items checked)
- Prompt variant (if applicable): Standard /sp.specify with detailed user input
- Next experiment (smallest change to try): Validate Gmail OAuth read-only assumption in /sp.plan
