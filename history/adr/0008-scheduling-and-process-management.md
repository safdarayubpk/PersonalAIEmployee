# ADR-0008: Scheduling and Process Management

- **Status:** Accepted
- **Date:** 2026-02-26
- **Feature:** 002-silver-tier
- **Context:** Silver tier needs recurring task scheduling (e.g., daily CEO briefing prep) and reliable process management for multiple long-running watchers and daemons. Bronze used PM2 for the single file-drop watcher. Silver adds Gmail watcher, WhatsApp watcher, scheduler daemon, and orchestrator — all must be daemonizable, restartable, and conflict-free.

## Decision

Use **APScheduler (in-memory) for job scheduling** combined with **PM2 for process management**:

- **Scheduler**: `scheduler_daemon.py` uses APScheduler's `BlockingScheduler` with in-memory job store. Jobs are defined in `config/schedules.json` and loaded on startup.
- **Job management**: CLI interface for `--add`, `--list` operations. Jobs fire by creating `Needs_Action/` files (same pattern as watchers).
- **PID lock**: Each daemon writes a PID lock file to prevent duplicate instances. Stale detection via `os.kill(pid, 0)` with automatic cleanup.
- **Process management**: PM2 `ecosystem.config.js` manages all Silver processes (file-drop watcher, Gmail watcher, WhatsApp watcher, scheduler daemon). Provides restart-on-crash, log aggregation, and status monitoring.
- **Timezone support**: All schedules use IANA timezone strings (default: `Asia/Karachi`), stored in job config.

## Consequences

### Positive

- Simple deployment — PM2 handles all process lifecycle with a single `pm2 start ecosystem.config.js`
- No external dependencies — APScheduler is pure Python, in-memory; PM2 is already installed from Bronze
- Familiar tooling — PM2 `status`, `logs`, `restart` commands for operations
- Composable — scheduler creates Needs_Action files, reusing the same orchestrator pipeline as watchers
- PID locks prevent resource conflicts (e.g., two Gmail pollers creating duplicate files)

### Negative

- In-memory job store — APScheduler jobs are lost on process restart (mitigated by `config/schedules.json` reload on startup)
- No distributed scheduling — single-machine only (acceptable for Silver, Platinum may need distributed)
- PM2 is Node.js-based — adds Node runtime dependency to a Python project (already present from Bronze)
- No job result tracking — scheduler only creates Needs_Action files; outcome tracking is delegated to orchestrator logs

## Alternatives Considered

### Alternative A: System Cron + Systemd Services

Use system crontab for scheduling and systemd unit files for process management.

- **Pros**: OS-native, zero dependencies, battle-tested, survives reboots
- **Cons**: Requires root/sudo for systemd, crontab syntax less readable, harder to manage across dev/prod, no cross-platform support, less portable for hackathon participants
- **Why rejected**: Constitution specifies APScheduler for scheduling. PM2 is already established from Bronze. Hackathon participants need portable, user-space tooling.

### Alternative B: Celery Beat + Supervisor

Use Celery Beat for periodic task scheduling and Supervisor for process management.

- **Pros**: Persistent task results, distributed-ready, mature ecosystem, built-in monitoring
- **Cons**: Requires Redis/RabbitMQ broker (external dependency), significant setup complexity, overkill for local single-user system
- **Why rejected**: Constitution prohibits external cloud dependencies before Platinum. Operational complexity disproportionate to Silver tier needs.

### Alternative C: APScheduler with SQLite Job Store + PM2

Same as chosen approach but with SQLite-backed job store instead of in-memory.

- **Pros**: Jobs persist across restarts without re-reading JSON, supports job state tracking
- **Cons**: SQLite file adds complexity, potential lock contention, config/schedules.json becomes redundant (two sources of truth), harder to inspect jobs (SQL vs JSON)
- **Why rejected**: `config/schedules.json` is the intended source of truth for human-readable job definitions. Reloading from JSON on startup is simpler and avoids dual-state issues. SQLite job store is a reasonable upgrade path for Gold/Platinum if needed.

## References

- Feature Spec: `specs/002-silver-tier/spec.md` (FR-007: Scheduling, FR-015: Daemonization)
- Implementation Plan: `specs/002-silver-tier/plan.md` (Phase 4: Scheduler, Phase 7: PM2 Integration)
- Data Model: `specs/002-silver-tier/data-model.md` (Entity 4: Scheduled Task)
- CLI Contract: `specs/002-silver-tier/contracts/cli-interfaces.md` (Scheduler Daemon section)
- Related ADRs: ADR-0001 (Event-Driven File Detection — PID lock pattern reused), ADR-0004 (Bronze Scope — deferred scheduling to Silver)
- Research: `specs/002-silver-tier/research.md` (R-005: Scheduler Implementation)
