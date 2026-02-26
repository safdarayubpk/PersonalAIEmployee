---
name: central-orchestrator
description: Central routing hub for Silver tier. Receives Needs_Action files from all watchers (filesystem, Gmail, WhatsApp, scheduler), queues tasks to avoid overload, triages via process-needs-action, decides MCP call or HITL routing, and updates Dashboard/Logs. Use when the user asks to "run orchestrator", "process all sources", "run the agent loop", "orchestrate tasks", "central processing", or when a watcher or scheduler triggers a processing cycle. Also triggers on phrases like "process everything", "run full pipeline", "handle all pending", or "silver tier processing". This is the top-level entry point that supersedes Bronze check-and-process-needs-action for multi-source workflows.
---

# Central Orchestrator

Silver tier routing hub. Ingests Needs_Action files from all sources, queues them by priority, triages each through the processing pipeline, and routes to MCP execution or HITL approval.

**Vault root**: `/home/safdarayub/Documents/AI_Employee_Vault`
(override via `VAULT_PATH` env var)

## Dependencies

- **Bronze skills** (reused): `vault-interact`, `process-needs-action`, `check-and-process-needs-action`
- **Silver skills**: `action-executor`, `ralph-retry` (optional, for fault tolerance)
- **Risk assessor subagent**: `.claude/agents/risk-assessor.md` (optional, for parallel risk checks)

## Architecture

```
                    ┌──────────────┐
                    │  Filesystem  │
                    │   Watcher    │──┐
                    └──────────────┘  │
                    ┌──────────────┐  │    ┌─────────────┐    ┌──────────────┐
                    │    Gmail     │──┼───▶│   INTAKE     │───▶│    QUEUE     │
                    │   Watcher    │  │    │ Needs_Action │    │  (priority)  │
                    └──────────────┘  │    └─────────────┘    └──────┬───────┘
                    ┌──────────────┐  │                              │
                    │  WhatsApp    │──┤                         ┌────▼────┐
                    │   Watcher    │  │                         │ TRIAGE  │
                    └──────────────┘  │                         │ (risk)  │
                    ┌──────────────┐  │                         └────┬────┘
                    │  Scheduler   │──┘                              │
                    └──────────────┘                      ┌─────────┼─────────┐
                                                          │         │         │
                                                     ┌────▼───┐ ┌──▼───┐ ┌──▼──────┐
                                                     │  MCP   │ │ HITL │ │  Done   │
                                                     │ Caller │ │ Gate │ │ (local) │
                                                     └────┬───┘ └──┬───┘ └────┬────┘
                                                          │        │          │
                                                     ┌────▼────────▼──────────▼────┐
                                                     │     Dashboard + Logs        │
                                                     └────────────────────────────┘
```

## Workflow

```
1. SCAN    → List all .md files in Needs_Action/
2. FILTER  → Exclude .moved files, deduplicate by source+title
3. QUEUE   → Sort by priority (high → medium → low), cap at batch_size
4. TRIAGE  → For each file: classify source, assess risk, create plan
5. ROUTE   → Execute locally / call MCP / route to Pending_Approval
6. LOG     → Update Dashboard.md + Logs/orchestrator.jsonl
```

## Usage

### Run a processing cycle

```bash
# Process all pending Needs_Action files (default: batch of 10)
python .claude/skills/central-orchestrator/scripts/orchestrator.py

# Custom batch size
python .claude/skills/central-orchestrator/scripts/orchestrator.py --batch-size 5

# Filter by source
python .claude/skills/central-orchestrator/scripts/orchestrator.py --source gmail

# Custom vault
python .claude/skills/central-orchestrator/scripts/orchestrator.py --vault-path /custom/vault

# With ralph-retry wrapper for fault tolerance
python .claude/skills/ralph-retry/scripts/ralph_retry.py \
  --command "python .claude/skills/central-orchestrator/scripts/orchestrator.py" \
  --description "Central orchestrator run" --max-retries 3
```

### As a Claude Code invocation

```
cd /home/safdarayub/Documents/AI_Employee_Vault
claude "run central orchestrator"
claude "process all pending tasks from gmail"
claude "orchestrate everything"
```

## Step 1: Scan Needs_Action

1. List all `.md` files in `Needs_Action/` (exclude `.moved` files)
2. Read frontmatter from each file to extract: `source`, `priority`, `status`, `type`
3. Skip files with `status: processing` (already being handled)
4. Build intake list with metadata

## Step 2: Classify and Queue

Sort files into a priority queue:

| Priority | Sources | Processing Order |
|----------|---------|------------------|
| **high** | VIP emails, urgent WhatsApp, scheduled high-priority | First |
| **medium** | Standard emails, direct WhatsApp, meeting requests | Second |
| **low** | Filesystem drops, newsletters, routine scheduled | Third |

Within same priority, sort by `created` timestamp (oldest first — FIFO).

Cap at `batch_size` (default 10) per run. Log remainder as deferred.

## Step 3: Triage Each File

For each queued file, determine the routing path:

1. **Read** the full Needs_Action file content
2. **Identify source** from frontmatter `source` field:
   - `file-drop-watcher` → filesystem origin
   - `gmail-watcher` → email origin
   - `whatsapp-watcher` → message origin
   - `daily-scheduler` → scheduled task origin
3. **Assess risk** using keyword scan (inline) or risk-assessor subagent
4. **Create action plan** in `Plans/`
5. **Determine route**:

```
Risk Assessment
       │
       ├── Low risk + routine action
       │     └── EXECUTE locally (move to Done/)
       │
       ├── Low risk + requires external action
       │     └── CALL MCP (via mcp-caller, dry-run default)
       │
       ├── Medium risk
       │     └── CALL MCP with approval check
       │           ├── Has approval → Execute
       │           └── No approval → Route to Pending_Approval/
       │
       └── High risk
             └── ROUTE to Pending_Approval/ (always HITL)
```

## Step 4: Execute Route

### Local execution (Done/)
- Use `process-needs-action` skill logic: create result file, move original to Done/
- Reuses Bronze tier processing — no duplication

### MCP execution
- Call `mcp-caller` with appropriate server and method
- Dry-run by default; live only if approval exists
- On failure: queue for ralph-retry or log error

### HITL routing (Pending_Approval/)
- Create detailed pending action file with instructions
- Move original Needs_Action file to `Pending_Approval/`
- Log the routing decision

## Step 5: Update Dashboard and Logs

Append processing summary to Dashboard.md:

```markdown
### Orchestrator Run — 2026-02-25T12:00:00

| Metric | Count |
|--------|-------|
| Files scanned | 12 |
| Processed (Done) | 7 |
| MCP calls (dry-run) | 2 |
| Pending approval | 2 |
| Deferred to next run | 1 |
| Errors | 0 |

| Source | Count |
|--------|-------|
| filesystem | 4 |
| gmail | 3 |
| whatsapp | 3 |
| scheduler | 2 |
```

Log each action to `Logs/orchestrator.jsonl`:

```json
{
  "timestamp": "2026-02-25T12:00:01",
  "component": "central-orchestrator",
  "action": "route_task",
  "status": "success",
  "file": "email-boss-20260225-073000.md",
  "source": "gmail-watcher",
  "priority": "high",
  "risk_level": "medium",
  "route": "mcp",
  "mcp_server": "email",
  "mcp_method": "draft_email",
  "dry_run": true,
  "detail": "Routed to MCP email.draft_email (dry-run)"
}
```

## Output Format

```json
{
  "status": "processed",
  "run_id": "orch-20260225-120000",
  "scanned": 12,
  "processed": 7,
  "mcp_calls": 2,
  "pending_approval": 2,
  "deferred": 1,
  "errors": 0,
  "by_source": {
    "filesystem": 4,
    "gmail": 3,
    "whatsapp": 3,
    "scheduler": 2
  },
  "next_action": "none"
}
```

Possible `status` values: `processed` (all done), `routed` (some sent to HITL/MCP), `queued` (deferred items remain).

Possible `next_action` values: `mcp` (MCP calls pending live execution), `hitl` (items awaiting approval), `none` (all complete).

## Safety Rules

1. **Batch size cap** — max 10 files per run (configurable, hard cap 50) to avoid overload
2. **No parallel writes** — process files sequentially to prevent race conditions
3. **Deduplication** — skip files with same `title` + `source` already processed in this run
4. **Mark in-progress** — set `status: processing` in frontmatter while handling (reset on error)
5. **Bronze compatibility** — reuses `process-needs-action` and `vault-interact` unchanged
6. **MCP dry-run default** — all MCP calls are dry-run unless explicit approval exists
7. **All vault writes scoped to vault root** — path validation on every file operation
8. **No-deletion policy** — files are moved (`.moved` rename), never deleted
9. **Error isolation** — one file's error does not stop processing of remaining files
10. **Log everything** — every scan, route decision, and outcome to `Logs/orchestrator.jsonl`

## Resources

### scripts/

- `orchestrator.py` — Main orchestration script with queue, triage, routing, and dashboard updates

### references/

- `routing_rules.md` — Detailed routing decision matrix by source type and risk level
