# ADR-0014: Cloud VM Resource Strategy and Service Subset

- **Status:** Accepted
- **Date:** 2026-03-11
- **Feature:** 004-platinum-tier
- **Context:** The cloud agent runs on an Oracle Cloud Free Tier VM.Standard.E2.1.Micro (1 OCPU, 1GB RAM, 2 vCPUs). This is severely resource-constrained. The Gold-tier local setup runs 4 PM2-managed services (file-drop-watcher, gmail-watcher, whatsapp-watcher, scheduler-daemon). Not all can or should run on the cloud VM — WhatsApp requires local `.session` files, and memory limits may prevent running all services simultaneously. An A1.Flex (4 OCPU, 24GB) is being attempted but has been consistently unavailable (OutOfHostCapacity).

## Decision

Run a **curated subset of 3 services** on the E2.1.Micro cloud VM via PM2, with a designed upgrade path:

- **Cloud services (E2.1.Micro)**: `cloud-git-sync`, `cloud-gmail-watcher`, `cloud-scheduler` (~170MB estimated total: PM2 30MB + 3 Python processes ~45MB each)
- **Excluded from cloud**: `whatsapp-watcher` (requires `.session` files — security exclusion, not resource), `file-drop-watcher` (no drop folder on cloud)
- **Process manager**: PM2 (not systemd), matching Gold-tier pattern (ADR-0008). PM2 `startup` for auto-start on boot.
- **Restart policy**: Max 5 restarts per 60s window. Exhaustion creates `Needs_Action/manual/` alert.
- **Uptime target**: 90% on E2.1.Micro (SC-007), upgrading to 99%+ when A1.Flex becomes available
- **A1.Flex upgrade path**: When available, all services run comfortably. Config change only — same `ecosystem.cloud.config.js`, no code changes.

## Consequences

### Positive

- **Runs within free tier**: No cost for 24/7 operation. Matches Principle V (Cost-Efficiency).
- **Graceful degradation**: If memory is tight, PM2 restart limits prevent crash loops. Health monitor detects and alerts.
- **Natural upgrade path**: Moving to A1.Flex requires only a VM migration, not code changes. PM2 config is identical.
- **Security benefit**: WhatsApp exclusion is a feature, not a limitation — cloud never has `.session` files.

### Negative

- **90% uptime target is low**: 10% downtime = ~2.4 hours/day. Acceptable for hackathon demo but not production.
- **OOM risk**: 1GB RAM is tight. Google API client library alone loads ~50MB of discovery cache. Monitoring via `pm2 monit` is essential.
- **No orchestrator on cloud**: Cloud agent triages and drafts but cannot run the full orchestrator pipeline. Limits cloud-side intelligence to what watchers and scheduler provide directly.

## Alternatives Considered

**Alternative A: Run all 4+ services on E2.1.Micro**
- Pros: Full feature parity with local.
- Rejected: High OOM risk on 1GB RAM. Python processes with Google API libraries are memory-hungry. PM2 itself needs ~30MB. Would likely trigger frequent OOM kills, reducing effective uptime below 90%.

**Alternative B: Use systemd instead of PM2**
- Pros: Lower memory overhead (~5MB vs ~30MB for PM2). Native on Ubuntu.
- Rejected: Loses PM2's built-in restart limits, log management, process monitoring (`pm2 monit`), and ecosystem config. Already using PM2 in Gold tier (ADR-0008) — changing adds inconsistency.

**Alternative C: Kubernetes/Docker on the VM**
- Pros: Container isolation, resource limits per service.
- Rejected: Explicit non-goal in spec. K8s/Docker overhead would consume most of the 1GB RAM. Free tier VM is too small for container orchestration.

## References

- Feature Spec: [spec.md](../../specs/004-platinum-tier/spec.md) — FR-023 to FR-025, US-8, SC-007
- Implementation Plan: [plan.md](../../specs/004-platinum-tier/plan.md) — PM2 Configuration section, `ecosystem.cloud.config.js`
- Research: [research.md](../../specs/004-platinum-tier/research.md) — R6: PM2 on E2.1.Micro Memory Constraints
- Related ADRs: ADR-0008 (Scheduling and Process Management — PM2 established in Gold tier)
- Related Constitution: Principle V (Cost-Efficiency), VII.8 (Safety Preservation — PM2 restart limits)
