# ADR-0016: Gmail OAuth Token Transfer for Headless Cloud

- **Status:** Accepted
- **Date:** 2026-03-11
- **Feature:** 004-platinum-tier
- **Context:** The cloud agent needs to read Gmail (the core Platinum use case — always-on email triage). Gmail API requires OAuth2 authentication. The OAuth flow requires a browser-based consent screen, which is impossible on a headless cloud VM. The cloud agent only needs read access (`gmail.readonly` scope) — it never sends emails. We must decide how to provide Gmail API access to the cloud VM without compromising the security model.

## Decision

**Manually copy a read-only scoped `token.json`** from the local machine to the cloud VM as a one-time setup step:

- **Scope limitation**: Cloud VM token uses `gmail.readonly` scope only (not `gmail.modify` or `gmail.send`). Even if the token leaks, it cannot be used to send emails.
- **Manual transfer**: `scp token.json ubuntu@<cloud-host>:~/AI_Employee_Vault/token.json` — performed once during initial setup.
- **Token refresh**: The `google-auth` library refreshes the token automatically using the embedded refresh token. Works headlessly as long as the refresh token is valid.
- **Failure handling**: When token refresh fails (Google revokes refresh token after password change, 6 months inactivity, or security event): cloud agent enters circuit breaker OPEN state for Gmail, creates `Needs_Action/manual/` file for human to re-authenticate on local machine and re-transfer token.
- **Token excluded from git**: `token.json` is in `.gitignore` and blocked by pre-commit hook (ADR-0012). Transfer is out-of-band via `scp`.

## Consequences

### Positive

- **Simple**: One `scp` command to enable cloud Gmail access. No additional infrastructure.
- **Scope-limited**: Read-only token limits blast radius. Cloud can triage but never act on emails.
- **Compatible with existing code**: `gmail_poll.py` already uses `token.json` for authentication. Cloud mode just forces `SCOPES_READONLY`.
- **Circuit breaker mitigation**: Known failure mode (token expiry) has a defined recovery path with clear user instructions.

### Negative

- **Token expiry is a known risk**: Google may revoke the refresh token at any time (password change, suspicious activity, extended inactivity). Requires manual re-authentication and re-transfer. Not fully automated.
- **Security trade-off**: A `token.json` file on the cloud VM is technically a credential, even if read-only scoped. An attacker with VM access could read Gmail. Mitigated by: VM is on private VCN, SSH key-only access, read-only scope limits damage.
- **Manual setup step**: Not infrastructure-as-code. Cannot be fully automated. Acceptable for single-user hackathon project.
- **Not production-grade**: Production systems would use a service account with domain-wide delegation or an intermediate credential manager.

## Alternatives Considered

**Alternative A: Google Service Account with domain-wide delegation**
- Pros: No refresh token expiry. Fully headless. Production-grade.
- Rejected: Requires Google Workspace admin account. Safdar uses a personal Gmail account (not Workspace). Service accounts cannot access personal Gmail without Workspace delegation.

**Alternative B: IMAP polling instead of Gmail API**
- Pros: Simpler authentication (app password or OAuth). Widely supported.
- Rejected: Gmail deprecated app passwords for most accounts. IMAP loses Gmail-specific features (labels, threads, search). Would require rewriting `gmail_poll.py` entirely.

**Alternative C: Local agent polls Gmail and pushes results to git**
- Pros: No token on cloud at all. Local handles all Gmail interaction.
- Rejected: Defeats the Platinum value proposition. If local must be online to poll Gmail, the cloud agent doesn't add 24/7 coverage. Cloud triage while owner sleeps is the core feature.

## References

- Feature Spec: [spec.md](../../specs/004-platinum-tier/spec.md) — US-1 (Always-On Email Triage), SC-001 (8hr offline operation), Assumptions (Gmail OAuth risk)
- Implementation Plan: [plan.md](../../specs/004-platinum-tier/plan.md) — Cloud VM First-Boot Setup, Risk Register
- Research: [research.md](../../specs/004-platinum-tier/research.md) — R4: Gmail OAuth on Headless Cloud VM
- Related ADRs: ADR-0012 (Defense-in-Depth Secrets Isolation — token.json excluded from git)
- Related Constitution: Principle I (Local-First — Platinum exception for read-only token), VII.1 (Cloud Agent capabilities)
