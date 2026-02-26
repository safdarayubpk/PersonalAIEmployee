# ADR-0007: Task Persistence and Retry Strategy

- **Status:** Accepted
- **Date:** 2026-02-26
- **Feature:** 002-silver-tier
- **Context:** Silver tier requires a retry mechanism ("Ralph Wiggum loop") for failed tasks. Actions may fail due to transient errors (network timeouts, API rate limits, temporary service outages). The system must retry with exponential backoff, respect a configurable maximum, and log all attempts. Bronze had no retry capability — failed tasks required manual re-processing.

## Decision

Use a **shell-command wrapper with exponential backoff** implemented as `ralph_retry.py`:

- **Wrapper pattern**: `ralph_retry.py --command "<shell_command>" --max-retries N --backoff-base B` wraps any shell command in a retry loop
- **Backoff**: Exponential with configurable base (default: 2). Delays: `base^attempt` seconds (2s, 4s, 8s, 16s...), capped at 300s per delay
- **Limits**: Default max retries: 15, hard cap: 20 (constitution specifies 10-20 range)
- **Exit codes**: 0 = eventual success, 1 = exhausted retries, 2 = non-retryable error (HITL block or abort signal)
- **Logging**: Every attempt logged to `{VAULT_PATH}/Logs/retry.jsonl` with timestamp, attempt number, delay, error details
- **Integration**: Orchestrator can wrap action executor calls in ralph_retry for transient failures

## Consequences

### Positive

- Universal — wraps any shell command, not limited to Python actions
- Transparent — all retry attempts logged as JSONL for audit and debugging
- Configurable — backoff base and max retries adjustable per invocation
- Safe — hard cap prevents infinite loops; exit code 2 provides clean abort path for HITL-blocked actions
- Simple — single-file implementation, no external dependencies

### Negative

- Shell overhead — spawning subprocess per retry attempt adds ~200ms per attempt
- No jitter — pure exponential backoff without randomization can cause thundering herd if multiple retries fire simultaneously (unlikely in single-user system)
- No task queue persistence — if ralph_retry process itself crashes, retry state is lost (partially mitigated by JSONL log showing last attempt)
- Coarse-grained — retries entire command, cannot retry specific sub-steps of a multi-step action

## Alternatives Considered

### Alternative A: Celery/RQ Task Queue with Built-in Retry

Use Celery or Python-RQ with Redis backend for persistent task queuing and automatic retries.

- **Pros**: Battle-tested retry logic, persistent task state, dead letter queues, built-in monitoring (Flower)
- **Cons**: Requires Redis (external dependency), significant setup complexity, overkill for single-user local system, violates local-first principle
- **Why rejected**: Constitution prohibits external cloud dependencies before Platinum. Redis adds operational burden for hackathon context.

### Alternative B: Inline Retry Decorator

Python decorator (`@retry(max=15, backoff=2)`) applied directly to action functions in `src/actions/*.py`.

- **Pros**: Zero subprocess overhead, tighter integration, per-function retry configuration
- **Cons**: Only works for Python functions (not shell commands), retry logic scattered across modules, harder to log uniformly, couples retry concern to action code
- **Why rejected**: Violates separation of concerns. Ralph retry should be a standalone, reusable utility that works with any command. Action stubs should remain simple.

### Alternative C: APScheduler-Based Retry

Schedule failed tasks as one-shot delayed jobs in the existing APScheduler daemon.

- **Pros**: Reuses existing scheduler infrastructure, persistent if scheduler uses job store, integrates naturally with scheduling system
- **Cons**: Tight coupling between retry and scheduling concerns, complex state management (retry count tracking across scheduled invocations), scheduler restart loses in-memory jobs
- **Why rejected**: Mixing retry and scheduling responsibilities creates fragile coupling. Better to keep them as independent tools that can be composed.

## References

- Feature Spec: `specs/002-silver-tier/spec.md` (FR-008: Ralph Wiggum retry loop)
- Implementation Plan: `specs/002-silver-tier/plan.md` (Phase 6: Ralph Retry)
- Data Model: `specs/002-silver-tier/data-model.md` (Entity 5: Retry Attempt Log Entry)
- CLI Contract: `specs/002-silver-tier/contracts/cli-interfaces.md` (Ralph Retry section)
- Related ADRs: ADR-0003 (Vault Data Safety — JSONL logging pattern reused)
- Research: `specs/002-silver-tier/research.md` (R-001: Action Execution Pattern — exit code conventions)
