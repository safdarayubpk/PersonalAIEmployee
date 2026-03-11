# ADR-0010: Runtime Role Gating via FTE_ROLE

- **Status:** Accepted
- **Date:** 2026-03-11
- **Feature:** 004-platinum-tier
- **Context:** The cloud agent must be structurally incapable of executing irreversible actions (sending emails, making payments, posting to social media). Meanwhile, the local agent must retain full Gold-tier execution capabilities. We need a mechanism to enforce this security boundary that cannot be accidentally bypassed by a routing bug, misconfigured orchestrator, or direct function call.

## Decision

Use a single **environment variable `FTE_ROLE`** (`cloud` or `local`) as the runtime role discriminator, enforced at multiple levels:

- **Centralized gate module**: New `src/role_gate.py` with `get_fte_role()`, `enforce_role_gate(action, risk_level)`, `validate_startup()`
- **Enforcement level**: Action executor (not just orchestrator), per FR-008 — every component that can trigger external effects calls `enforce_role_gate()` before execution
- **Fail-closed**: Missing or invalid `FTE_ROLE` causes a fatal startup error (process refuses to start)
- **Immutable**: Role cannot be changed at runtime — set once at process start
- **Cloud behavior**: When `FTE_ROLE=cloud`, all Sensitive/Critical actions are blocked; system creates draft in `Pending_Approval/` instead
- **Local behavior**: When `FTE_ROLE=local`, system operates identically to Gold tier with full HITL-gated execution

## Consequences

### Positive

- **Defense in depth**: Role is checked at action executor level — even if orchestrator routes incorrectly, the executor refuses.
- **Simple to verify**: `grep -r "enforce_role_gate" src/` reveals all enforcement points. Missing calls are visible in code review.
- **Backward compatible**: `FTE_ROLE=local` produces identical behavior to Gold tier (FR-030). Pre-Platinum code works when `FTE_ROLE` is unset (via graceful handling in setup_vault.py).
- **Testable**: Unit tests can set `FTE_ROLE=cloud` and verify all sensitive actions are blocked.
- **Fail-safe**: Missing env var = system won't start = no accidental execution.

### Negative

- **Every action executor must be modified**: All MCP servers, action handlers, and watchers need `enforce_role_gate()` calls added. If one is missed, it's a security gap.
- **No granular permissions**: Role is binary (cloud/local). Cannot express "cloud can do X but not Y" beyond the risk-level classification. If a new Routine action has side effects, it would pass the gate.
- **Env var dependency**: Process restart required to change role. No hot-switching for debugging.

## Alternatives Considered

**Alternative A: Orchestrator-only gate (check role only in the central orchestrator)**
- Pros: Single enforcement point, simpler implementation.
- Rejected: Violates FR-008 ("MUST be enforced at the action executor level, not just the orchestrator"). A routing bug or direct function call would bypass the gate.

**Alternative B: Python decorator-based (@require_role("local"))**
- Pros: Clean, declarative, Pythonic. Self-documenting which functions are gated.
- Rejected: Harder to test in isolation, stack traces less clear on failure, and decorators can be bypassed by calling the underlying function directly. Explicit function call is more transparent and grep-able.

**Alternative C: Separate codebases for cloud and local**
- Pros: Physical separation guarantees cloud never has sensitive code paths.
- Rejected: Doubles maintenance burden, breaks the single-repo pattern (ADR-0015), and makes Gold-tier backward compatibility much harder. The role gate achieves the same security without code duplication.

## References

- Feature Spec: [spec.md](../../specs/004-platinum-tier/spec.md) — FR-005 to FR-008, US-3, SC-006
- Implementation Plan: [plan.md](../../specs/004-platinum-tier/plan.md) — `src/role_gate.py` design section
- Research: [research.md](../../specs/004-platinum-tier/research.md) — R2: FTE_ROLE Enforcement Architecture
- Related ADRs: ADR-0005 (Action Execution Pattern — now extended with role gate before `importlib` dispatch)
- Related Constitution: Principle VII.1 (Agent Roles), VII.8 (Safety Preservation), II (HITL Safety — Platinum clarification)
