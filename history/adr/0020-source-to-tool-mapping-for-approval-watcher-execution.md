# ADR-0020: Source-to-Tool Mapping for Approval Watcher Execution

- **Status:** Accepted
- **Date:** 2026-03-12
- **Feature:** 004-platinum-tier
- **Context:** The Platinum lifecycle has a gap between cloud drafting and local execution. When the cloud orchestrator routes a file to Pending_Approval/, the approval_watcher on the local side needs to know which tool to call when the user approves. During the T047 live demo, the approval_watcher returned `no_tool` because the gmail-watcher file lacked a `tool:` field in frontmatter. This broke the automated execution pipeline, requiring manual file enrichment.

## Decision

Implement a two-map pattern in the orchestrator:

1. **SOURCE_ACTION_MAP** (existing): Maps source → draft action (e.g., `gmail-watcher` → `email.draft_email`). Used for dry-run drafting on cloud.

2. **SOURCE_TOOL_MAP** (new): Maps source → execution tool (e.g., `gmail-watcher` → `email.send`). The orchestrator adds `tool:` to frontmatter via `complete_file(**tool_kwargs)` when routing to Pending_Approval/.

3. The approval_watcher reads `tool:` from frontmatter and calls the corresponding action module with parameters from the `## Parameters` JSON block.

This separates "what to draft" (cloud, read-only) from "what to execute" (local, after approval).

## Consequences

### Positive

- Fully automated approval → execution pipeline without manual file editing
- Clean separation of draft action (cloud) vs execution action (local)
- Frontmatter-based — works naturally with git sync, no API needed
- Extensible: adding new source types requires only a map entry

### Negative

- Two maps to maintain in sync (SOURCE_ACTION_MAP and SOURCE_TOOL_MAP)
- Parameters block must be valid JSON in the markdown file — fragile parsing
- Only sources with map entries get automated execution; unmapped sources fall through to `no_tool`

## Alternatives Considered

1. **Single map for both draft and execute**: Would couple cloud drafting with local execution, violating role separation. Rejected.
2. **Tool name derived from source name by convention**: e.g., `gmail-watcher` → `gmail.send`. Too implicit, breaks when conventions change. Rejected.
3. **User specifies tool in approval step**: Adds friction to the approval workflow. Rejected for UX.
4. **Hardcoded in approval_watcher**: Would require approval_watcher changes for each new source. Rejected for modularity.

## References

- Feature Spec: specs/004-platinum-tier/spec.md (FR-006, FR-007, SC-003)
- Constitution: Principle II (HITL Safety), Principle VII.1 (Role gating)
- Related ADRs: ADR-0005 (action execution pattern), ADR-0010 (role gating)
- Files: .claude/skills/central-orchestrator/scripts/orchestrator.py (SOURCE_TOOL_MAP), src/approval_watcher.py
- Live Demo: T047 — identified gap when `no_tool` returned for approved gmail email
