# ADR-0015: Single Repo with Role-Gated Runtime

- **Status:** Accepted
- **Date:** 2026-03-11
- **Feature:** 004-platinum-tier
- **Context:** The Platinum tier introduces a cloud agent and a local agent. We must decide whether to maintain one codebase or two. The Gold-tier codebase (`safdarayubpk/PersonalAIEmployee`) has 16+ Python files, 4 MCP servers, 4 PM2-managed watchers, and 6 config files. Splitting into separate cloud and local repositories would require maintaining parallel code with shared logic. Keeping a single repo requires a mechanism to differentiate behavior at runtime.

## Decision

Maintain a **single repository** shared by both agents, with **runtime behavior differentiated by `FTE_ROLE` environment variable**:

- **Same code, different behavior**: Both cloud and local run identical Python files. `FTE_ROLE` gates which actions are permitted, which folders are writable, and which services start.
- **Single PM2 config pattern**: `ecosystem.config.js` (local) and `ecosystem.cloud.config.js` (cloud) select different service subsets from the same codebase.
- **Conditional vault setup**: `setup_vault.py` creates Platinum folders only when `FTE_ROLE` is set (backward compat with Gold).
- **No feature flags or conditional imports**: Role gating is a simple runtime check (`if is_cloud(): refuse`), not compile-time branching.

## Consequences

### Positive

- **Zero code duplication**: All bug fixes, improvements, and new features apply to both agents automatically.
- **Gold backward compatibility trivial**: `FTE_ROLE=local` is functionally equivalent to Gold tier (FR-030). No code paths are removed — only new guard clauses are added.
- **Single CI/CD pipeline**: One repo = one test suite = one deployment artifact. Reduces operational complexity.
- **Familiar pattern**: Same approach used by many cloud-native projects (12-factor app: config in environment).

### Negative

- **Cloud has dead code**: The cloud VM has code for `send_email()`, `post_social()`, etc. that it can never execute. Increases attack surface marginally (mitigated by role gate + no credentials).
- **Testing complexity**: Must test same code with two different `FTE_ROLE` values. Test matrix doubles.
- **Accidental feature leakage**: A developer adding a new Routine action might not realize it runs on cloud. Requires vigilance in code review.
- **Git sync of code changes**: Code updates on local must be pushed and pulled on cloud. Vault sync and code sync share the same git channel (acceptable for single-user project).

## Alternatives Considered

**Alternative A: Separate cloud and local repositories**
- Pros: Physical separation guarantees cloud never has sensitive code. Clean boundaries.
- Rejected: Doubles maintenance burden. Shared logic (vault_helpers, correlation, circuit_breaker) must be duplicated or extracted into a shared package. Any bug fix requires two PRs. Gold backward compatibility is much harder.

**Alternative B: Monorepo with separate packages (cloud/ and local/ directories)**
- Pros: Code separation within one repo. Shared libraries in `common/`.
- Rejected: Overengineering for a single-user project. Adds package management overhead. Existing flat `src/` structure works well. The problem is solved more simply by runtime gating.

**Alternative C: Docker images with different entrypoints**
- Pros: Different images from same code. Build-time separation of concerns.
- Rejected: Docker overhead on E2.1.Micro (1GB RAM) is prohibitive. Explicit non-goal (no K8s/Docker scaling). PM2 is simpler for this scale.

## References

- Feature Spec: [spec.md](../../specs/004-platinum-tier/spec.md) — FR-029, FR-030 (Gold backward compatibility)
- Implementation Plan: [plan.md](../../specs/004-platinum-tier/plan.md) — Structure Decision, Project Structure section
- Related ADRs: ADR-0010 (Runtime Role Gating — the mechanism that makes single-repo safe)
- Related Constitution: Principle IV (Modularity — tier builds incrementally, no breakage)
