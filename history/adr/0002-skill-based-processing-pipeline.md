# ADR-0002: Skill-Based Processing Pipeline

- **Status:** Accepted
- **Date:** 2026-02-24
- **Feature:** 001-bronze-tier

- **Context:** The Bronze tier needs a processing pipeline that reads `Needs_Action` files, classifies them by risk, creates plans, routes them to `Done/` or `Pending_Approval/`, and updates `Dashboard.md`. The project has three pre-existing Claude Code Agent Skills (`vault-interact`, `process-needs-action`, `check-and-process-needs-action`). The key architectural question is: where does processing logic live — in Python scripts, in Claude Code skills, or in some combination? This decision defines the boundary between automation infrastructure (Python) and reasoning/triage logic (Claude), and shapes how the system extends in Silver/Gold tiers.

## Decision

- **Infrastructure (Python scripts)**: `setup_vault.py` (vault initialization) and `file_drop_watcher.py` (filesystem monitoring + Needs_Action file creation) — deterministic, stateless operations
- **Processing logic (Claude Code skills)**: All triage, classification, plan creation, file routing, and dashboard updates handled by the three-skill composition chain:
  - `vault-interact` → low-level file I/O (read, write, append, list, move, create)
  - `process-needs-action` → per-file triage (risk classification, plan creation, routing)
  - `check-and-process-needs-action` → batch orchestrator (up to 5 files per run, error isolation, dashboard summary)
- **Shared utilities (Python module)**: `vault_helpers.py` provides path validation, JSONL logging, and frontmatter generation — used by both Python scripts
- **Invocation model**: Manual trigger via Claude Code (user says "check and process needs action"); no automated orchestration in Bronze

## Consequences

### Positive

- Claude Code's reasoning capabilities handle the nuanced parts (risk classification, Company Handbook rule interpretation) while Python handles the deterministic parts (file watching, PID management)
- Skills are prompt-based — easy to modify behavior without code changes, just update SKILL.md
- Three-skill composition creates clear separation of concerns: I/O, triage, orchestration
- Skills are reusable across tiers — Silver/Gold add new triggers but reuse the same processing chain
- Existing skills were already built and tested — no new processing code needed for Bronze

### Negative

- Processing depends on Claude Code being available and manually invoked — no autonomous processing loop in Bronze
- Skill-based logic is non-deterministic — Claude interprets Company Handbook rules, which may produce slightly different classifications across runs
- Debugging skill behavior requires understanding prompt engineering, not just code debugging
- Three-skill chain adds invocation overhead vs a single Python script that does everything
- Skills cannot be unit-tested in the traditional sense — only end-to-end manual testing

## Alternatives Considered

**Alternative A: All-Python processing pipeline**
- Pros: Deterministic behavior, traditional unit testing, single runtime, no Claude API dependency for processing
- Cons: Cannot leverage Claude's reasoning for nuanced risk classification; rule matching becomes rigid keyword-based; loses the "AI employee" value proposition; significant new Python code to write
- Rejected: The hackathon thesis is that Claude *is* the employee — processing logic should use its reasoning capabilities, not replicate them in Python

**Alternative B: Single monolithic skill**
- Pros: Simpler invocation (one skill does everything), no inter-skill dependencies
- Cons: Violates separation of concerns; vault I/O, triage logic, and orchestration all tangled together; harder to reuse I/O operations in other contexts; harder to maintain
- Rejected: Three focused skills are more modular and align with constitution Principle IV (Modularity)

**Alternative C: Python scripts call Claude API directly**
- Pros: Automated processing (no manual trigger), deterministic orchestration with AI reasoning, full programmatic control
- Cons: Requires API key management, adds network dependency (violates local-first spirit for Bronze), more complex error handling, duplicates what Claude Code skills already provide
- Rejected: Over-engineered for Bronze; Silver tier may introduce this pattern when scheduling is added

## References

- Feature Spec: `specs/001-bronze-tier/spec.md` (FR-006 through FR-016)
- Implementation Plan: `specs/001-bronze-tier/plan.md` (D2, Component Mapping)
- Skills: `.claude/skills/vault-interact/SKILL.md`, `.claude/skills/process-needs-action/SKILL.md`, `.claude/skills/check-and-process-needs-action/SKILL.md`
- Related ADRs: ADR-0004 (Bronze tier scope — why manual trigger only)
- Constitution: Principle II (HITL Safety — risk classification), Principle IV (Modularity)
