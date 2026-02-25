# Contract: Plan File Format

**Version**: 1.0
**Producer**: process-needs-action skill
**Consumer**: check-and-process-needs-action skill, human review

## Format

```markdown
---
title: "Plan: <original-needs-action-title>"
created: "YYYY-MM-DDTHH:MM:SS"
source_file: "Needs_Action/<original-filename>"
risk_level: low|high
status: planned|completed|pending_approval
---

## Action plan

<Describe what will be done based on the suggested action>

## Risk assessment

- Classification: <low-risk|high-risk>
- Reason: <why this classification was chosen>
- Company Handbook rule: <which rule applied>

## Expected outcome

<What the result should look like after execution>
```

## Filename Convention

`plan-{original-stem}-{YYYYMMDD-HHMMSS}.md`

## Status Transitions

```
planned → completed        (low-risk, action executed, file moved to Done/)
planned → pending_approval (high-risk, file moved to Pending_Approval/)
```
