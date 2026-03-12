# ADR-0018: PM2 v6 Shell Wrapper for Environment Variable Injection

- **Status:** Accepted
- **Date:** 2026-03-12
- **Feature:** 004-platinum-tier
- **Context:** PM2 v6.0.14 on the cloud VM has two bugs that prevent direct Python process management: (1) the `interpreter` field causes PM2's internal `ProcessContainerForkBun.js` to be parsed by Python instead of the actual script; (2) when using the `script`/`args` workaround, the `env` block is not reliably passed to child processes. All services failed with "FTE_ROLE environment variable is not set" despite correct ecosystem config.

## Decision

Create a shell wrapper `config/cloud-start.sh` that sets all required environment variables (`FTE_ROLE=cloud`, `VAULT_PATH`, `PROJECT_ROOT`, `GIT_SYNC_INTERVAL_SECONDS`, `DRY_RUN=true`), changes to the vault directory, and exec's Python with the provided script arguments. PM2 ecosystem config uses `cloud-start.sh` as `script` for all 4 services, with the actual `.py` file as `args`.

## Consequences

### Positive

- All 4 services receive correct env vars reliably
- Single point of configuration for cloud environment variables
- Works with any PM2 version (bypasses both interpreter and env block bugs)
- `exec` ensures PM2 can still signal the Python process directly

### Negative

- Extra indirection layer for debugging
- Cloud-specific hardcoded paths (not portable without editing)
- PM2's built-in env management bypassed entirely

## Alternatives Considered

1. **Downgrade PM2 to v5**: v5 is EOL, npm only installs v6. Rejected for maintenance risk.
2. **Use systemd directly**: Loses PM2's log rotation, cron_restart, and monitoring. Rejected for operational convenience.
3. **Source .env from Python scripts**: Too invasive — requires modifying every entry point. Rejected.
4. **PM2 JSON config format**: Tested, still doesn't pass env vars reliably in v6. Rejected.

## References

- Feature Spec: specs/004-platinum-tier/spec.md (FR-027, FR-028)
- Related ADRs: ADR-0008 (process management), ADR-0014 (cloud VM resource strategy)
- Files: config/cloud-start.sh, config/ecosystem.cloud.config.js
