# Contract: Dashboard.md Format

**Version**: 1.0
**Producers**: setup_vault.py (initial), check-and-process-needs-action skill (updates)
**Consumer**: Developer (via Obsidian), human review

## Initial Format (created by setup_vault.py)

```markdown
---
title: "AI Employee Dashboard"
created: "YYYY-MM-DDTHH:MM:SS"
tier: bronze
status: active
---

# AI Employee Dashboard

## Status Overview

- **Vault**: Active
- **Tier**: Bronze
- **Created**: YYYY-MM-DDTHH:MM:SS
- **Last processed**: Never

## Processing History

<!-- Processing summaries are appended below by check-and-process-needs-action -->
```

## Appended Processing Summary Format

Each processing run appends a section:

```markdown
### Processing Run — YYYY-MM-DDTHH:MM:SS

| Metric | Count |
|--------|-------|
| Files processed | N |
| Auto-executed (Done) | N |
| Pending approval | N |
| Errors | N |
| Deferred to next run | N |
```

If no files found:

```markdown
- [YYYY-MM-DDTHH:MM:SS] No pending actions.
```

## Update Rules

- NEVER overwrite existing content — always append
- Each processing run adds one summary block
- "Last processed" in Status Overview is NOT updated (append-only design for simplicity)
