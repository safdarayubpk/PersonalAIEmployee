# Contract: Needs_Action File Format

**Version**: 1.0
**Producers**: file_drop_watcher.py, error recovery (Principle VI)
**Consumers**: process-needs-action skill, check-and-process-needs-action skill

## Format

```markdown
---
title: "<descriptive-kebab-case-title>"
created: "YYYY-MM-DDTHH:MM:SS"
tier: bronze
source: "<component-name>"
priority: routine|sensitive|critical
status: needs_action
---

## What happened

<Description of the event or trigger that created this file>

## Suggested action

<What the agent recommends doing with this event>

## Context

<Relevant file paths, error details, or data references>
```

## Field Constraints

| Field | Constraint |
|-------|-----------|
| title | Non-empty string, kebab-case, max 100 chars |
| created | Valid ISO 8601 datetime |
| tier | Must be `bronze` for this tier |
| source | Non-empty string identifying the creator component |
| priority | One of: `routine`, `sensitive`, `critical` |
| status | Always `needs_action` at creation |

## Filename Convention

`dropped-{original-stem}-{YYYYMMDD-HHMMSS}.md`

Example: A file `report.pdf` dropped at 2026-02-24 14:30:00 produces:
`dropped-report-20260224-143000.md`

## Watcher-Generated Example

```markdown
---
title: "dropped-report-pdf"
created: "2026-02-24T14:30:00"
tier: bronze
source: "file-drop-watcher"
priority: routine
status: needs_action
---

## What happened

New file detected in drop folder: `report.pdf` (245 KB)

## Suggested action

Review and organize the dropped file.

## Context

- Original file: /home/safdarayub/Desktop/DropForAI/report.pdf
- File type: .pdf
- File size: 245 KB
- Drop time: 2026-02-24T14:30:00
```

## Validation Rules

- Missing frontmatter → treat as high-risk (priority: critical)
- Missing `priority` field → default to high-risk
- Invalid `status` value → reject with error log
- File MUST have all three body sections (What happened, Suggested action, Context)
