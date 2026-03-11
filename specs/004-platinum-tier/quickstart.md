# Quickstart: Platinum Tier — Cloud-Local Hybrid Operation

**Feature**: 004-platinum-tier | **Date**: 2026-03-11

## Prerequisites

### Local Machine (already in place)
- Gold-tier FTE fully operational
- Python 3.13+ venv at `/home/safdarayub/Desktop/claude/fte/.venv`
- Obsidian vault at `/home/safdarayub/Documents/AI_Employee_Vault`
- GitHub repo `safdarayubpk/PersonalAIEmployee` (private)
- Gmail API credentials (`credentials.json`, `token.json`)

### Cloud VM (already in place)
- Oracle Cloud VM at `141.145.146.17` (E2.1.Micro, Ubuntu 24.04)
- SSH access: `ssh ubuntu@141.145.146.17`
- Python venv at `~/fte-env`
- Repo cloned at `~/AI_Employee_Vault`
- Git SSH key configured for GitHub push/pull

## Setup Steps

### Step 1: Install Pre-Commit Hook (local)

```bash
cp hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### Step 2: Create Platinum Vault Folders (both machines)

```bash
# Local
FTE_ROLE=local python src/setup_vault.py

# Cloud (via SSH)
ssh ubuntu@141.145.146.17
source ~/fte-env/bin/activate
cd ~/AI_Employee_Vault
FTE_ROLE=cloud python src/setup_vault.py
```

### Step 3: Configure Environment Variables

**Local `.env`** (add to existing):
```bash
FTE_ROLE=local
GIT_SYNC_INTERVAL_SECONDS=60
```

**Cloud `.env`** (create):
```bash
FTE_ROLE=cloud
VAULT_PATH=/home/ubuntu/AI_Employee_Vault
PROJECT_ROOT=/home/ubuntu/AI_Employee_Vault
GIT_SYNC_INTERVAL_SECONDS=60
DRY_RUN=true
```

### Step 4: Transfer Gmail Read-Only Token (one-time)

```bash
# From local machine:
scp token.json ubuntu@141.145.146.17:~/AI_Employee_Vault/token.json
```

Note: This is a read-only scoped token. The cloud agent can only read Gmail, never send.

### Step 5: Install Cloud VM Dependencies

```bash
ssh ubuntu@141.145.146.17
source ~/fte-env/bin/activate
pip install google-api-python-client google-auth-oauthlib apscheduler watchdog pyyaml
sudo npm install -g pm2
```

### Step 6: Start Cloud Services

```bash
ssh ubuntu@141.145.146.17
cd ~/AI_Employee_Vault
pm2 start config/ecosystem.cloud.config.js
pm2 startup systemd -u ubuntu --hp /home/ubuntu
pm2 save
pm2 list  # Verify all services running
```

### Step 7: Start Local Git Sync

```bash
# On local machine
python src/git_sync.py  # Runs as daemon
```

Or add to local PM2:
```bash
pm2 start config/ecosystem.config.js  # Updated with FTE_ROLE=local
```

## Verification

### Quick Health Check

```bash
# Cloud: check services
ssh ubuntu@141.145.146.17 "pm2 list"

# Local: check sync
ls ~/Documents/AI_Employee_Vault/Logs/sync.jsonl

# Both: check vault structure
ls ~/Documents/AI_Employee_Vault/Needs_Action/gmail/
ls ~/Documents/AI_Employee_Vault/In_Progress/cloud/
ls ~/Documents/AI_Employee_Vault/Pending_Approval/gmail/
```

### Demo Test (5 minutes)

1. Close laptop / stop local agent
2. Send a test email to monitored Gmail
3. Wait 2-3 minutes
4. Open laptop / start local agent
5. Check `Pending_Approval/gmail/` for draft
6. Move draft to `Approved/`
7. Verify email sent, file in `Done/`

## First-Boot Setup Script (Cloud VM)

For automated setup on a fresh cloud VM, run the following after cloning the repo:

```bash
#!/bin/bash
# cloud-setup.sh — First-boot Platinum setup for cloud VM
set -euo pipefail

echo "=== Platinum Cloud VM Setup ==="

# 1. Create Python venv and install deps
python3 -m venv ~/fte-env
source ~/fte-env/bin/activate
cd ~/AI_Employee_Vault
pip install google-api-python-client google-auth-oauthlib apscheduler watchdog pyyaml

# 2. Install PM2
sudo npm install -g pm2

# 3. Create .env
cat > .env << 'ENVEOF'
FTE_ROLE=cloud
VAULT_PATH=/home/ubuntu/AI_Employee_Vault
PROJECT_ROOT=/home/ubuntu/AI_Employee_Vault
GIT_SYNC_INTERVAL_SECONDS=60
DRY_RUN=true
ENVEOF

# 4. Create Platinum vault folders
FTE_ROLE=cloud python3 src/setup_vault.py

# 5. Install pre-commit hook
cp hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# 6. Start PM2 services
pm2 start config/ecosystem.cloud.config.js
pm2 startup systemd -u ubuntu --hp /home/ubuntu
pm2 save

echo "=== Setup complete. Transfer token.json from local machine. ==="
echo "Run: scp token.json ubuntu@141.145.146.17:~/AI_Employee_Vault/token.json"
```

Save as `scripts/cloud-setup.sh` and run with `bash scripts/cloud-setup.sh`.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Cloud services not starting | Missing `FTE_ROLE` env | Check `.env` has `FTE_ROLE=cloud` |
| Gmail watcher failing | Token expired | Re-auth on local, copy new `token.json` to VM |
| Git sync conflicts | Simultaneous edits | Check `Logs/sync-conflicts.jsonl`, resolve manually |
| No files syncing | SSH key issue on VM | Verify `ssh -T git@github.com` works on VM |
| OOM on E2.1.Micro | Too many services | Reduce poll intervals, check `pm2 monit` |
