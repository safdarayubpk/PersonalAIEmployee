# ADR-0005: Action Execution Pattern

- **Status:** Accepted
- **Date:** 2026-02-26
- **Feature:** 002-silver-tier
- **Context:** Silver tier needs an action execution layer that dispatches 6 actions across 4 domains (email, social, calendar, documents). The action executor must support dry-run by default, HITL approval gates for sensitive actions, and be extensible for Gold tier. Bronze had no action execution — all processing was read-only vault operations.

## Decision

Use **direct Python function calls via `importlib` dynamic import** with a JSON action registry:

- **Registry**: `config/actions.json` maps `action_id` → `module` + `function` (e.g., `email.send_email` → `actions.email.send_email`)
- **Executor**: `execute_action.py` loads the registry, resolves the module via `importlib.import_module()`, and calls the function with a standardized signature `fn(params: dict, dry_run: bool) -> dict`
- **Stubs**: All 6 action functions are initially stubs returning simulated results. Real implementations (Gmail API for email) are wired in incrementally.
- **HITL gate**: Actions with `hitl_required: true` in the registry create a `Pending_Approval/` file and exit with code 2 when `--live` is passed without `--approval-ref`.
- **Exit codes**: 0 = success, 1 = failure, 2 = HITL blocked

## Consequences

### Positive

- Zero network overhead — function calls are direct, no HTTP serialization
- Simple debugging — standard Python stack traces, no service boundaries
- Registry-driven extensibility — add new actions by adding a JSON entry and a Python module
- Stub-first development — all actions testable immediately without external services
- Constitution-compliant — dry-run default prevents accidental execution

### Negative

- No process isolation — a misbehaving action module can crash the executor
- Single-language lock-in — all actions must be Python (acceptable for Silver/Gold scope)
- No built-in rate limiting or circuit breaking (must be added per-action if needed)
- Gold tier may need to introduce HTTP layer for external integrations, requiring partial rewrite of dispatch logic

## Alternatives Considered

### Alternative A: MCP/FastAPI HTTP Servers

Each action domain runs as a separate FastAPI server with MCP protocol endpoints. The executor makes HTTP calls.

- **Pros**: Process isolation, language-agnostic, matches MCP ecosystem
- **Cons**: Significant overhead for 6 actions, complex deployment (6 servers), overkill for local-first single-user system
- **Why rejected**: Constitution principle of cost-efficiency and local-first simplicity. Deferred to Gold tier if external integration needs arise.

### Alternative B: Subprocess Execution

Each action is a standalone Python script invoked via `subprocess.run()`. Communication via stdin/stdout JSON.

- **Pros**: Process isolation, simple to reason about, crash-contained
- **Cons**: Startup overhead per invocation (~200ms Python boot), complex error propagation, harder to share state (e.g., Gmail API credentials)
- **Why rejected**: Latency overhead unacceptable when orchestrator processes 10+ tasks per batch.

### Alternative C: Plugin Architecture (Entry Points)

Use Python `importlib.metadata` entry points for action discovery, similar to pytest plugins.

- **Pros**: Standard Python packaging pattern, auto-discovery
- **Cons**: Requires package installation (`pip install -e .`), more complex than a JSON file for 6 actions, harder to inspect/edit for hackathon participants
- **Why rejected**: Over-engineered for current scale. JSON registry is simpler and more transparent.

## References

- Feature Spec: `specs/002-silver-tier/spec.md` (FR-003, FR-004, FR-005)
- Implementation Plan: `specs/002-silver-tier/plan.md` (Phase 3: Action Executor)
- Data Model: `specs/002-silver-tier/data-model.md` (Entity 2: Action Registry Entry)
- Contracts: `specs/002-silver-tier/contracts/action-registry-schema.json`
- Related ADRs: ADR-0002 (Skill-Based Processing Pipeline — Bronze read-only actions), ADR-0004 (Bronze Scope and Deferral — deferred MCP to Silver)
- Research: `specs/002-silver-tier/research.md` (R-001: Action Execution Pattern)
