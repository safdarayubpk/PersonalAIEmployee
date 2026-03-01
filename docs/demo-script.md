# Demo Script — Personal AI Employee (5-10 Minutes)

This script demonstrates the Gold tier Personal AI Employee end-to-end, showcasing multi-source input, HITL approval gates, MCP server integration, and automated reporting.

## Pre-Demo Setup (Run Before Demo)

```bash
# Terminal 1: Start all components
cd /home/safdarayub/Desktop/claude/fte
pm2 start config/ecosystem.config.js

# Verify all processes started
pm2 status

# Terminal 2: Set up demo environment
export VAULT_PATH="/home/safdarayub/Documents/AI_Employee_Vault"
export DRY_RUN=false  # Live mode for demo
export DEMO_MODE=true

# Verify vault exists
ls -la "$VAULT_PATH"

# Ensure Odoo Docker container is running (if demoing Odoo)
docker ps | grep odoo
```

## Demo 1: Email Draft via MCP (Routine Action) — 1 minute

**Narrative**: "The system can compose emails via the MCP email server. Let's draft a response to a customer."

```bash
# Terminal 2: Create a test email task
cat > "$VAULT_PATH/Needs_Action/test-draft-email.md" << 'EOF'
---
title: Draft customer response email
created: 2026-03-01T14:00:00
tier: gold
source: demo
priority: routine
status: needs_action
correlation_id: corr-20260301-140000-demo
---

Draft a professional response thanking the customer for their inquiry.
EOF

# Show the task was created
echo "Created test task in Needs_Action/"
ls -la "$VAULT_PATH/Needs_Action/test-draft-email.md"

# View the JSONL log before orchestrator runs
echo ""
echo "Checking email MCP logs (should be empty initially)..."
wc -l "$VAULT_PATH/Logs/mcp_email.jsonl" 2>/dev/null || echo "Log doesn't exist yet"

# Run orchestrator
cd /home/safdarayub/Documents/AI_Employee_Vault
echo ""
echo "Running orchestrator to process the draft email task..."
claude "check and process needs action"

# Show the result
echo ""
echo "Draft email created in Plans/:"
ls -la "$VAULT_PATH/Plans/" | grep email | head -3

# Show the MCP log entry
echo ""
echo "Email MCP log entry:"
tail -1 "$VAULT_PATH/Logs/mcp_email.jsonl" | python3 -m json.tool
```

**Expected output**:
- New file in `Plans/draft-email-*.md` with draft content
- Entry in `Logs/mcp_email.jsonl` with correlation_id, tool="draft", status="dry_run" (because this is routine)

---

## Demo 2: Social Media Post with HITL Gate (Sensitive Action) — 2 minutes

**Narrative**: "Social media posts are sensitive (require human approval). Let's see the approval gate in action."

```bash
# Create a social media posting task
cat > "$VAULT_PATH/Needs_Action/test-social-post.md" << 'EOF'
---
title: Post business update to social media
created: 2026-03-01T14:05:00
tier: gold
source: demo
priority: sensitive
status: needs_action
correlation_id: corr-20260301-140500-demo
type: action
action: social.post_facebook
---

Post: "Excited to announce new features shipping this week! Stay tuned."
Platform: facebook
EOF

# Run orchestrator
echo "Running orchestrator to process the social media task..."
claude "check and process needs action"

# Show the pending approval file
echo ""
echo "Sensitive action created Pending_Approval file:"
ls -la "$VAULT_PATH/Pending_Approval/" | grep social | head -1
cat "$VAULT_PATH/Pending_Approval/$(ls -1 "$VAULT_PATH/Pending_Approval/" | grep social | head -1)" | head -20

# Show the MCP log entry (with pending_approval status)
echo ""
echo "Social media MCP log entry (pending approval):"
tail -1 "$VAULT_PATH/Logs/mcp_social.jsonl" | python3 -m json.tool
```

**Expected output**:
- File in `Pending_Approval/` containing the full action payload
- MCP log entry with status="pending_approval", approval_file path
- NOT actually posted to Facebook (dry-run or blocked)

**Next step (optional, if time permits)**:
```bash
# Simulate developer approval
PENDING_FILE=$(ls -1 "$VAULT_PATH/Pending_Approval/" | grep social | head -1)
mv "$VAULT_PATH/Pending_Approval/$PENDING_FILE" "$VAULT_PATH/Approved/$PENDING_FILE"

echo "Moved to Approved/. With --live flag, this would post to Facebook."
echo "In production, orchestrator retries with --approval-ref pointing to this file."
```

---

## Demo 3: Odoo Financial Query (Routine Read) — 1.5 minutes

**Narrative**: "The system can query live accounting data from Odoo. Let's get a financial summary."

```bash
# Check if Odoo is running
echo "Checking Odoo availability..."
curl -s "http://localhost:8069/jsonrpc" -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"service":"common","method":"version"},"id":1}' \
  | python3 -m json.tool

# Create a task to query Odoo
cat > "$VAULT_PATH/Needs_Action/test-odoo-query.md" << 'EOF'
---
title: Fetch financial summary for CEO briefing
created: 2026-03-01T14:10:00
tier: gold
source: demo
priority: routine
status: needs_action
correlation_id: corr-20260301-141000-demo
type: action
action: odoo.financial_summary
---

Get revenue, expenses, receivables, and payables for the current month.
EOF

# Run orchestrator
echo ""
echo "Running orchestrator to process Odoo query..."
claude "check and process needs action"

# Show the result
echo ""
echo "Financial summary report created:"
ls -la "$VAULT_PATH/Plans/" | grep financial | head -1

# Show the Odoo MCP log
echo ""
echo "Odoo MCP log entry:"
tail -1 "$VAULT_PATH/Logs/mcp_odoo.jsonl" | python3 -m json.tool

# If Odoo is down, show graceful degradation
if [ $? -ne 0 ]; then
  echo ""
  echo "Note: Odoo is not available. System gracefully degraded:"
  echo "- Odoo service marked as 'degraded' in Logs/health.json"
  echo "- Dependent tasks queued for retry"
  echo "- CEO briefing would show 'Financial data unavailable'"
fi
```

**Expected output**:
- If Odoo is running: Financial summary file with real data (revenue, expenses, etc.)
- MCP log entry with status="success" or status="dry_run"
- If Odoo is not running: Circuit breaker activates, error logged, graceful degradation

---

## Demo 4: Generate CEO Briefing On-Demand — 2 minutes

**Narrative**: "Every Monday morning, the system generates an executive briefing aggregating all data from the past week."

```bash
# Verify the scheduler has a CEO briefing task configured
echo "CEO Briefing scheduled tasks:"
grep -A 5 "briefing\|ceo" "$VAULT_PATH/../../../config/schedules.json" || echo "Check config/schedules.json"

# Generate briefing on-demand
echo ""
echo "Triggering CEO briefing generation..."
cd /home/safdarayub/Desktop/claude/fte
claude "generate ceo briefing"

# Show the generated briefing
echo ""
echo "CEO Briefing generated:"
ls -la "$VAULT_PATH/Briefings/" | tail -1
echo ""
echo "Briefing preview (first 50 lines):"
head -50 "$VAULT_PATH/Briefings/$(ls -1 "$VAULT_PATH/Briefings/" | tail -1)"

# Show correlation IDs in the briefing
echo ""
echo "Correlation IDs referenced in briefing:"
grep "corr-" "$VAULT_PATH/Briefings/$(ls -1 "$VAULT_PATH/Briefings/" | tail -1)" | head -3
```

**Expected output**:
- `Briefings/YYYY-MM-DD_Monday_Briefing.md` created with sections:
  - Executive Summary
  - Revenue & Expenses (from Odoo)
  - Completed Tasks (count by source)
  - Social Media Activity (posts this week)
  - Bottlenecks (items pending >24h)
  - Proactive Suggestions

---

## Demo 5: Check Health Dashboard and Circuit Breaker Status — 1 minute

**Narrative**: "The system monitors the health of all external services and automatically handles outages gracefully."

```bash
# Show the current Dashboard
echo "Dashboard status:"
head -30 "$VAULT_PATH/Dashboard.md"

# Show health.json with circuit breaker states
echo ""
echo "Service health status (circuit breaker states):"
cat "$VAULT_PATH/Logs/health.json" | python3 -m json.tool

# Show a service in degraded state (if applicable)
if grep -q '"state": "degraded"' "$VAULT_PATH/Logs/health.json"; then
  echo ""
  echo "Service degradation detected:"
  grep -B 5 '"state": "degraded"' "$VAULT_PATH/Logs/health.json" | head -20
fi

# Show recent log entries with correlation IDs
echo ""
echo "Recent orchestrator decisions with correlation IDs:"
tail -3 "$VAULT_PATH/Logs/orchestrator.jsonl" | python3 -m json.tool
```

**Expected output**:
- Dashboard showing last orchestrator run stats
- `Logs/health.json` with all services listed (healthy, degraded, or down)
- Recent JSONL entries with correlation_id for traceability

---

## Demo 6: Trace End-to-End via Correlation ID (Optional, if time permits) — 1 minute

**Narrative**: "Using correlation IDs, we can trace any task through the entire system."

```bash
# Pick a correlation ID from the logs
CORR_ID=$(grep -h '"correlation_id"' "$VAULT_PATH/Logs"/*.jsonl | head -1 | grep -o 'corr-[^"]*' | head -1)

echo "Tracing correlation ID: $CORR_ID"
echo ""
echo "All log entries with this ID:"
grep "$CORR_ID" "$VAULT_PATH/Logs"/*.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    entry = json.loads(line.strip())
    timestamp = entry.get('timestamp', 'N/A')
    component = entry.get('component', 'N/A')
    action = entry.get('action', entry.get('tool', 'N/A'))
    status = entry.get('status', 'N/A')
    print(f'{timestamp} | {component:20} | {action:20} | {status}')
"

echo ""
echo "Complete lifecycle of this task visible in a single grep."
```

**Expected output**:
- Timeline showing: watcher creation → orchestrator scan → risk assessment → routing → action execution
- Each step with timestamp and component name
- Proves full traceability for audit and debugging

---

## Troubleshooting During Demo

| Issue | Cause | Solution |
|-------|-------|----------|
| "No MCP servers registered" | PM2 didn't start them | Run `pm2 start config/ecosystem.config.js` |
| "Vault path not found" | Wrong vault location | Set `VAULT_PATH` env var |
| "Odoo connection refused" | Docker container not running | `docker-compose up -d` in odoo config dir |
| "Gmail auth failed" | OAuth token expired | Re-authenticate via Gmail watcher setup script |
| "Logs are empty" | DRY_RUN=true | Set `DRY_RUN=false` before running orchestrator |
| "Files not processed" | Orchestrator didn't run | Manually run `claude "check and process needs action"` |

---

## Post-Demo Cleanup

```bash
# Stop all processes
pm2 stop config/ecosystem.config.js

# Clean up test files (optional)
rm -f "$VAULT_PATH/Needs_Action/test-*.md"
rm -f "$VAULT_PATH/Pending_Approval/"*
rm -f "$VAULT_PATH/Plans/test-*"
rm -f "$VAULT_PATH/Plans/email-draft-*"
rm -f "$VAULT_PATH/Plans/financial-*"

# Optionally, restart for next demo
pm2 start config/ecosystem.config.js
```

---

## Key Talking Points During Demo

### On HITL (Human-In-The-Loop)
"Notice that routine tasks (like email drafts, financial queries) execute immediately. But sensitive actions like social media posts require human approval. The system creates a file in Pending_Approval/, and only after a human moves it to Approved/ does the system execute for real. This is how we balance autonomy with safety."

### On Reliability
"Even if Odoo or a social media API goes down, the system doesn't crash. It marks that service as degraded, queues the task for retry, and continues processing everything else. The circuit breaker pattern prevents cascading failures."

### On Observability
"Every single action has a correlation ID that links it through all components. A single grep shows the entire lifecycle of a task from detection to completion. This makes debugging trivial and auditing safe."

### On Autonomy
"The CEO briefing runs every Sunday evening automatically. Without any human intervention, it queries live financial data, reviews this week's tasks, checks social media activity, and generates a report. That's real autonomy."

---

## Time Breakdown

| Demo | Time | Complexity |
|------|------|-----------|
| Setup (before demo) | 2-3 min | PM2 start, verify vault |
| Demo 1: Email draft | 1 min | Routine action, shows MCP |
| Demo 2: Social post | 2 min | HITL gate, approval flow |
| Demo 3: Odoo query | 1.5 min | External service integration |
| Demo 4: CEO briefing | 2 min | Scheduled report, multi-source aggregation |
| Demo 5: Health dashboard | 1 min | Circuit breaker, service health |
| Demo 6: Correlation ID trace | 1 min | End-to-end audit trail |
| **Total** | **~10 minutes** | Comprehensive Gold tier demo |

---

## References

- Architecture: [docs/architecture.md](architecture.md)
- Lessons Learned: [docs/lessons-learned.md](lessons-learned.md)
- Manual Test Plan: [tests/manual/gold-tier-test-plan.md](../tests/manual/gold-tier-test-plan.md)
- Source Code: [src/](../src/)
- Configuration: [config/](../config/)
