# Vault Conventions

## Vault Path

Resolve from `VAULT_PATH` env var, default: `/home/safdarayub/Documents/AI_Employee_Vault`

All file operations MUST use absolute paths. Abort if a relative path is detected.

## File Naming

- `kebab-case.md` — no spaces, no uppercase in filenames
- Every .md file MUST have YAML frontmatter with: `title`, `created`, `tier`, `status`

## Folder Structure

```
AI_Employee_Vault/
├── Needs_Action/      # Files awaiting processing
├── Done/              # Completed files
├── Pending_Approval/  # High-risk items awaiting human approval
├── Approved/          # Human-approved items ready for execution
├── Plans/             # Action plans generated during processing
├── Logs/              # JSON Lines log files
├── Dashboard.md       # Status overview
└── Company_Handbook.md # Processing rules and policies
```

## Needs_Action File Format

```yaml
---
title: "<descriptive title>"
created: "YYYY-MM-DDTHH:MM:SS"
tier: bronze|silver|gold|platinum
source: "<watcher or component name>"
priority: routine|sensitive|critical
status: needs_action
---

## What happened
<description of the event or trigger>

## Suggested action
<what the agent recommends doing>

## Context
<relevant file paths, error details, or data references>
```

## Risk Classification

| Level | Examples | Action |
|-------|----------|--------|
| Routine | File organization, notes, reports | Auto-execute, log |
| Sensitive | Email, social media, financial records | HITL gate via Pending_Approval/ |
| Critical | Payments, deletions, legal, credentials | HITL gate + confirmation log |

## Log Format

JSON Lines in `Logs/`, required fields:
- `timestamp` (ISO 8601)
- `component` (string)
- `action` (string)
- `status` (success|failure|skipped)
- `detail` (string)
