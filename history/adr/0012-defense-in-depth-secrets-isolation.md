# ADR-0012: Defense-in-Depth Secrets Isolation

- **Status:** Accepted
- **Date:** 2026-03-11
- **Feature:** 004-platinum-tier
- **Context:** The vault is now git-synced between a cloud VM and local machine. Any secret file (`.env`, OAuth tokens, session files, private keys) that enters git becomes accessible on the cloud VM, breaking the trust model. A single layer of protection (`.gitignore` alone) is insufficient — accidental `.gitignore` edits, force-adds, or misconfigured exclusions could leak secrets. The constitution mandates "absolute" security boundaries (SC-004: zero secrets in git history at any point).

## Decision

Implement **three independent layers** of secrets isolation:

- **Layer 1 — `.gitignore`**: Vault `.gitignore` includes patterns from constitution Section: Security (`.env`, `*.session`, `*.token`, `*.key`, `*.pem`, `credentials/`, `secrets/`, `__pycache__/`). Prevents accidental staging.
- **Layer 2 — Pre-commit hook**: A `hooks/pre-commit` script validates staged files against a **hardcoded** exclusion list (independent of `.gitignore`). Blocks commits containing secrets even if `.gitignore` is modified or `git add -f` is used. Prints clear error: `"BLOCKED: <file> matches secrets exclusion pattern"`.
- **Layer 3 — Cloud VM audit**: FR-016 requires that if a secrets-matching file is detected on the cloud VM, it is logged as a critical security event. Periodic audit via `git log --all --diff-filter=A --name-only | grep` verifies zero secrets in entire git history.

## Consequences

### Positive

- **No single point of failure**: `.gitignore` deletion doesn't bypass the pre-commit hook. Force-adding a file still triggers the hook. Even if both fail, the cloud audit detects the leak.
- **Testable**: SC-004 can be verified automatically by scanning git history. Pre-commit hook can be tested with `git add .env && git commit`.
- **Self-documenting**: The hook's blocked patterns are hardcoded and visible in the script — no hidden configuration.
- **Edge case covered**: Spec Edge Case 6 (`.gitignore` accidentally modified) is handled by the hook's independent validation.

### Negative

- **Pre-commit hooks can be bypassed**: `git commit --no-verify` skips the hook. Mitigated by constitution mandate to never use `--no-verify` and by Layer 3 audit.
- **Maintenance of two exclusion lists**: `.gitignore` and the pre-commit hook have overlapping patterns. Changes must be synchronized. Mitigated by the hook using a superset of `.gitignore` patterns.
- **No server-side enforcement**: GitHub doesn't run pre-commit hooks. A developer pushing from a machine without the hook installed could push secrets. Mitigated by the single-user nature of this project and Layer 3 audit.

## Alternatives Considered

**Alternative A: `.gitignore` only (single layer)**
- Pros: Simple, standard, well-understood.
- Rejected: Single point of failure. `git add -f .env` bypasses `.gitignore`. Accidental edits expose all secrets. Does not meet "absolute" security boundary requirement.

**Alternative B: Server-side GitHub pre-receive hook**
- Pros: Cannot be bypassed by client. Catches all pushes regardless of local configuration.
- Rejected: Requires GitHub Enterprise or GitHub Actions integration. Not available on free-tier private repos. Would be ideal for production but overkill for hackathon scope.

**Alternative C: Git-crypt or git-secret for encrypted secrets**
- Pros: Secrets can exist in git but encrypted. Cloud VM gets ciphertext only.
- Rejected: Adds GPG key management complexity. Secrets should not be in git at all (even encrypted) per constitution Principle I. Violates the "never sync secrets" philosophy.

## References

- Feature Spec: [spec.md](../../specs/004-platinum-tier/spec.md) — FR-014 to FR-016, US-6, SC-004, Edge Case 6
- Implementation Plan: [plan.md](../../specs/004-platinum-tier/plan.md) — Secrets Management section, Pre-Commit Hook design
- Related ADRs: ADR-0003 (Vault Data Safety and Logging Strategy)
- Related Constitution: Principle I (Local-First — secrets remain local-only), Section: Security (`.gitignore` patterns mandate)
