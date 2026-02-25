# Quickstart: Bronze Tier

**Feature**: 001-bronze-tier
**Prerequisites**: Python 3.13+, pip, Obsidian v1.11.x+, Claude Code 2.1.x

## 1. Install Dependencies

```bash
pip install watchdog pyyaml
```

## 2. Set Environment Variables

```bash
# Add to ~/.bashrc or .env
export VAULT_PATH="/home/safdarayub/Documents/AI_Employee_Vault"
export DROP_FOLDER="$HOME/Desktop/DropForAI"
```

## 3. Initialize the Vault

```bash
python src/setup_vault.py
```

**Expected output**: 7 folders and 2 files created. Open vault in Obsidian to verify.

**Verify**:
```bash
ls /home/safdarayub/Documents/AI_Employee_Vault/
# Should show: Approved/  Company_Handbook.md  Dashboard.md  Done/
#              Inbox/  Logs/  Needs_Action/  Pending_Approval/  Plans/
```

## 4. Start the Watcher

```bash
python src/file_drop_watcher.py
```

**Expected**: "Watching ~/Desktop/DropForAI for new files..." printed to stdout. PID lock written to `Logs/watcher.pid`.

## 5. Test the Drop → Needs_Action Flow

In a second terminal:
```bash
echo "Test content" > ~/Desktop/DropForAI/test-file.txt
```

**Expected**: Within 5 seconds, a new file appears:
```bash
ls /home/safdarayub/Documents/AI_Employee_Vault/Needs_Action/
# Should show: dropped-test-file-YYYYMMDD-HHMMSS.md
```

## 6. Process Needs_Action Files via Claude Code

Open Claude Code and say:
```
check and process needs action
```

**Expected**: Claude reads the Needs_Action file, classifies it as routine (low-risk), creates a plan in `Plans/`, moves the result to `Done/`, and appends a summary to `Dashboard.md`.

## 7. Verify End-to-End

```bash
# Check Plans/
ls /home/safdarayub/Documents/AI_Employee_Vault/Plans/

# Check Done/
ls /home/safdarayub/Documents/AI_Employee_Vault/Done/

# Check Dashboard (open in Obsidian or cat)
cat /home/safdarayub/Documents/AI_Employee_Vault/Dashboard.md

# Check logs
cat /home/safdarayub/Documents/AI_Employee_Vault/Logs/vault_operations.jsonl
cat /home/safdarayub/Documents/AI_Employee_Vault/Logs/actions.jsonl
```

## 8. Stop the Watcher

Press `Ctrl+C` in the watcher terminal. The PID lock file is removed automatically.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Watcher already running" | Check `Logs/watcher.pid`. If process is dead, delete the PID file. |
| No Needs_Action file created | Check drop folder exists. Check `Logs/errors.jsonl` for errors. |
| Claude can't read vault files | Verify `VAULT_PATH` is set. Run `setup_vault.py` first. |
| "Path violation" error | You're trying to operate outside the vault root. Use relative paths. |
